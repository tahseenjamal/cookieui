"""Helper utilities for building tazui applications.

This module provides reusable patterns for common UI tasks, reducing boilerplate
when building multi-window applications with consistent layouts and behaviors.
"""

from typing import Any, Optional, Callable, List
from .core.event import Key, KeyType
from .widgets.base import Widget
from .widgets.button import Button
from .widgets.window import Window
from .widgets.label import Label
from .widgets.dialog import Dialog


# Drop-shadow extent in rows/columns. Every shadowed surface (Window, Dialog, Button,
# Listbox) casts a 1-row/1-column shadow via Screen.cast_shadow, so a window at (x, y)
# of size (w, h) visually occupies through row y+h and column x+w. The stacking helpers
# below reserve this automatically so windows never sit on each other's shadow.
SHADOW = 1

# Sentinel for "find it automatically" parameters (run_task's progress/spinner):
# distinct from None, which means "explicitly none".
AUTO = object()


class Page:
    """What page() returns: the view, window, and layout behind **one name**.

    The page delegates to its parts, so you talk to it directly — layout factories
    (`page.input/.label/.listbox/.buttons/.gap/...`), window helpers
    (`page.fill_with/.add/.interior_rect/...`) — and `build_view` can return the
    page itself (push_view unwraps it):

        def build_view(self):
            page = self.page(0.5, title='Sign In')
            usr = page.input(label='Username')
            page.buttons([('Sign In', go), ('Quit', self.quit)])
            return page

    `page.footer([...])` is footer_buttons on the page's window. The parts stay
    reachable as `page.view` / `page.win` / `page.lay` (key bindings and status bars
    take `page.view`), and `view, win, lay = page` unpacking still works.
    """

    def __init__(self, view, win: Window, lay: 'VerticalLayout'):
        self.view = view
        self.win  = win
        self.lay  = lay

    def __iter__(self):                       # `view, win, lay = page` still works
        return iter((self.view, self.win, self.lay))

    def __getattr__(self, name: str) -> Any:
        # Fallback delegation for the long tail (focus helpers, interior math, …):
        # layout first (row factories), then window, then view. The common surface is
        # declared as real methods below so editors can autocomplete + type-check it.
        for part in (self.lay, self.win, self.view):
            if hasattr(part, name):
                return getattr(part, name)
        raise AttributeError(f'Page has no attribute {name!r} '
                             '(not found on its lay, win, or view either)')

    # ── Explicit delegation: the common surface, typed for autocomplete ──
    # (Keep in sync when VerticalLayout gains a factory — editors only see these.)

    def label(self, text: str, bold: bool = False, dim: bool = False):
        return self.lay.label(text, bold=bold, dim=dim)

    def input(self, label: str = '', placeholder: str = '', password: bool = False,
              on_enter=None, on_change=None):
        return self.lay.input(label=label, placeholder=placeholder, password=password,
                              on_enter=on_enter, on_change=on_change)

    def checkbox(self, label: str, checked: bool = False, on_change=None):
        return self.lay.checkbox(label, checked=checked, on_change=on_change)

    def checkboxes(self, specs, on_change=None) -> tuple:
        return self.lay.checkboxes(specs, on_change=on_change)

    def radio_group(self, options: List, selected: int = 0, on_change=None):
        return self.lay.radio_group(options, selected=selected, on_change=on_change)

    def listbox(self, height: Optional[int] = None, shadow: bool = False,
                rows: Optional[int] = None):
        return self.lay.listbox(height=height, shadow=shadow, rows=rows)

    def textview(self, height: Optional[int] = None, text: str = '', title: str = '',
                 wrap: bool = True, shadow: bool = False, rows: Optional[int] = None):
        return self.lay.textview(height=height, text=text, title=title,
                                 wrap=wrap, shadow=shadow, rows=rows)

    def table(self, columns, height: Optional[int] = None, title: str = '',
              on_select=None, shadow: bool = False, rows: Optional[int] = None):
        return self.lay.table(columns, height=height, title=title,
                              on_select=on_select, shadow=shadow, rows=rows)

    def spinner(self, label: str = '', frames: Optional[str] = None,
                fps: float = 12, style: str = 'dots'):
        return self.lay.spinner(label=label, frames=frames, fps=fps, style=style)

    def progressbar(self, value: float = 0.0, show_percent: bool = True):
        return self.lay.progressbar(value=value, show_percent=show_percent)

    def buttons(self, specs, spacing: int = 3, align: str = 'center') -> tuple:
        return self.lay.buttons(specs, spacing=spacing, align=align)

    def gap(self, lines: int = 1) -> None:
        self.lay.gap(lines)

    def fill_with(self, widget_cls, *args, footer: bool = True, **kwargs):
        return self.win.fill_with(widget_cls, *args, footer=footer, **kwargs)

    def add(self, *widgets) -> Window:
        return self.win.add(*widgets)

    def footer(self, specs, spacing: int = 3, align: str = 'center') -> tuple:
        """footer_buttons on this page's window — `page.footer([('OK', fn), ...])`."""
        return footer_buttons(self.win, specs, spacing=spacing, align=align)


def resolve_size(value, total: int) -> int:
    """Resolve a size spec against a total: a float <= 1.0 is a **fraction** of `total`
    (`0.5` → half the terminal); anything else is taken as absolute cells. This is what
    lets `page()`/`columns()` take proportions instead of eyeballed cell counts."""
    if isinstance(value, float) and value <= 1.0:
        return max(1, round(total * value))
    return int(value)


class TerminalSizeProvider:
    """Access terminal dimensions from an App instance.

    Provides a consistent interface for querying terminal width and height.
    """

    def __init__(self, app):
        """Initialize with a tazui App instance."""
        self.app = app

    def width(self) -> int:
        """Current terminal width in columns."""
        return self.app._terminal.width

    def height(self) -> int:
        """Current terminal height in rows."""
        return self.app._terminal.height


def calculate_centered_window(
    term_w: int,
    term_h: int,
    desired_w: int,
    desired_h: int
) -> tuple:
    """Calculate position and constrained size for a centered window.

    Returns: (x, y, constrained_w, constrained_h)
    - Window is constrained to fit within terminal bounds
    - Horizontally centered on screen
    - Vertically positioned with slight offset from center

    Args:
        term_w: Terminal width
        term_h: Terminal height
        desired_w: Target window width
        desired_h: Target window height

    Returns:
        Tuple of (x, y, width, height) for window positioning
    """
    # Constrain width: use desired width or (term_w - 2), whichever is smaller
    win_w = min(desired_w, term_w - 2)

    # Constrain height: use desired height or (term_h - 4), whichever is smaller
    # (account for some padding from top/bottom)
    win_h = min(desired_h, term_h - 4)

    # Center horizontally
    wx = (term_w - win_w) // 2

    # Position vertically with slight offset from center
    wy = max(1, (term_h - win_h - 4) // 2)

    return (wx, wy, win_w, win_h)


def create_status_bar(
    view,
    term_w: int,
    term_h: int,
    status_text: str = 'Status Bar',
    align: str = 'center'
) -> Window:
    """Create a status bar window at the bottom of the screen.

    The text is **centered** in the bar by default (matching button rows and
    dialog buttons); pass align='left' or 'right' to anchor it.

    Args:
        view: The View to add the status bar to
        term_w: Terminal width
        term_h: Terminal height
        status_text: Text to display in the status bar
        align: 'left' | 'center' | 'right'

    Returns:
        The created status bar Window
    """
    if align not in ('left', 'center', 'right'):
        raise ValueError(f"align={align!r} — use 'left', 'center', or 'right'")
    # A real frame with the text INSIDE it needs 3 rows: top border, text row,
    # bottom border. shadow=False: flush with the bottom row — no shadow, and no
    # draw-time edge shift (which would move the frame off its label).
    status_win = Window(0, term_h - 3, term_w, 3, title='', shadow=False)
    view.add(status_win)                       # auto-links
    ix, iy = status_win.interior()
    avail = term_w - 4                          # interior minus 1 cell padding each side
    if align == 'center':
        lx = ix + 1 + max(0, (avail - len(status_text)) // 2)
    elif align == 'right':
        lx = ix + 1 + max(0, avail - len(status_text))
    else:
        lx = ix + 1
    status_win.add(Label(lx, iy, status_text, max_width=term_w - 4))
    view._has_status = True                     # suppress TuiApp's auto status bar
    return status_win


def layout_buttons(
    buttons: List[Button],
    start_x: int,
    start_y: int,
    spacing: int = 3,
    width: Optional[int] = None,
    align: str = 'left'
) -> None:
    """Arrange buttons horizontally with consistent spacing.

    Modifies button positions in-place based on their widths. With a `width`,
    the whole row can be justified inside it: `align='center'` (the Newt look)
    or `'right'`; `'left'` (default) anchors at `start_x` as before.

    Args:
        buttons: List of Button widgets to position
        start_x: X-coordinate the row is justified within
        start_y: Y-coordinate for all buttons
        spacing: Space between buttons (default 3 columns)
        width:   Available row width (required for center/right)
        align:   'left' | 'center' | 'right'
    """
    if align not in ('left', 'center', 'right'):
        raise ValueError(f"align={align!r} — use 'left', 'center', or 'right'")
    x = start_x
    if align != 'left' and width is not None and buttons:
        total = sum(b.width for b in buttons) + spacing * (len(buttons) - 1)
        free  = max(0, width - total)
        x     = start_x + (free // 2 if align == 'center' else free)
    for btn in buttons:
        btn.x = x
        btn.y = start_y
        x += btn.width + spacing


def chain_key_handler(
    widget: Widget,
    custom_handler: Callable[[Key], bool]
) -> None:
    """Chain a custom key handler before a widget's existing handler.

    Calls custom_handler first. If it returns True (key handled), stops.
    Otherwise delegates to the widget's original handle_key method.

    Args:
        widget: The Widget to wrap
        custom_handler: Function taking a Key, returning bool
    """
    original_handler = widget.handle_key

    def chained_handler(key: Key) -> bool:
        if custom_handler(key):
            return True
        return original_handler(key)

    widget.handle_key = chained_handler


def bind_enter_action(
    widget: Widget,
    action: Callable[[], None]
) -> None:
    """Bind an action to trigger when a widget receives Enter key.

    Args:
        widget: The Widget to bind to
        action: Callback function (no args)
    """
    def enter_handler(key: Key) -> bool:
        if key.type == KeyType.ENTER:
            action()
            return True
        return False

    chain_key_handler(widget, enter_handler)


def bind_key(target, key_type: KeyType, action: Callable[[], None], char: Optional[str] = None) -> None:
    """Run `action()` when `target` (a widget or a view) receives `key_type`.

    Handles the chaining internally — replaces the recurring
    `_h = target.handle_key; def wrap(k): ...; target.handle_key = wrap` boilerplate.
    For character keys, pass `char=` to match a specific key:

        bind_key(view, KeyType.ESCAPE, go_to_parent)
        bind_key(view, KeyType.CHAR, refresh, char='r')
    """
    original = target.handle_key

    def handler(key: Key) -> bool:
        if key.type == key_type and (char is None or key.char == char):
            action()
            return True
        return original(key)

    target.handle_key = handler


def stack_below(y: int, height: int, gap: int = 1, shadow: int = SHADOW) -> int:
    """Y for the next window/widget stacked below one of `height` rows starting at `y`.

    Shadow-aware: it reserves the drop-shadow row plus `gap` blank rows, so stacked
    windows never sit on each other's shadow. The default gap=1 leaves exactly one
    clear row below the shadow — what you almost always want.

    Eliminates hand-rolled `y + height + SHADOW + VGAP` chains.

    Usage:
        out_y    = stack_below(top, browser_h)     # one blank row after the shadow
        status_y = stack_below(out_y, out_h)
        btn_y    = stack_below(status_y, status_h)
    """
    return y + height + shadow + gap


def stack_beside(x: int, width: int, gap: int = 2, shadow: int = SHADOW) -> int:
    """X for the next window placed to the right of one `width` columns wide at `x`.

    Shadow-aware horizontal counterpart of stack_below(). Reserves the 1-column drop
    shadow plus `gap` clear columns. The default gap=2 (shadow + 2 columns = 3 total)
    matches columns()'s comfortable default spacing.

    Usage:
        right_x = stack_beside(left_x, left_w)     # shadow + 2 clear columns
    """
    return x + width + shadow + gap


def calculate_footer_position(interior_y: int, interior_height: int, button_height: int = 3) -> int:
    """Calculate Y position for footer buttons inside a window.

    Eliminates hardcoded offsets like iy + ih - 5. Positions buttons at the bottom
    with proper padding above them.

    Args:
        interior_y: Starting Y of interior (from window.interior()[1])
        interior_height: Height available (from window.interior_size()[1])
        button_height: Height of buttons (default 3 for standard Buttons)

    Returns:
        Y position for footer buttons

    Usage:
        ix, iy = win.interior()
        iw, ih = win.interior_size()
        btn_y = calculate_footer_position(iy, ih)
        btn = Button(ix, btn_y, 'OK')
    """
    return interior_y + interior_height - button_height - 1


def footer_buttons(win, specs, spacing: int = 3, button_height: int = 3,
                   align: str = 'center') -> tuple:
    """Create a row of buttons along a window's footer and add them to it.

    Collapses the recurring ritual — calculate_footer_position + Button(...) × n +
    layout_buttons + win.add — into one call. Positions are interior-aware (no magic
    offsets). Every spec is a `(label, on_click)` tuple (define the callbacks first):

        footer_buttons(win, [('Add', do_add), ('Quit', app.quit)])

    The row is **centered** in the window by default (the Newt look — dialogs
    center too); pass align='left' or 'right' to anchor it.

    Returns the buttons as a tuple, in order, for any later tweaks.
    """
    if getattr(win, '_auto_height', False):
        raise ValueError(
            "footer_buttons needs a fixed-height window, but this window is content-fit "
            "(no height was given). In a content-fit window, buttons flow with the "
            "content — use lay.buttons([...]) instead."
        )
    ix, iy = win.interior()
    iw, ih = win.interior_size()
    btn_y  = calculate_footer_position(iy, ih, button_height)
    buttons = [Button(ix, btn_y, label, on_click=cb) for label, cb in specs]
    layout_buttons(buttons, ix, btn_y, spacing=spacing, width=iw, align=align)
    win.add(*buttons)
    return tuple(buttons)


def buttons_below(view, win, specs, spacing: int = 3, gap: int = 1,
                  align: str = 'center') -> tuple:
    """A floating button row below a window — the sibling of footer_buttons().

    Shadow-aware (uses stack_below, so the row clears the window's drop shadow).
    Each spec is a `(label, on_click)` tuple; the buttons are added to the view
    and returned as a tuple:

        buttons_below(view, left_win, [('Save', do_save), ('Back', do_back)])

    Replaces the x/y math + Button(...)×n + layout_buttons + view.add ritual.
    Centered under the window by default; align='left'/'right' to anchor.

    Works under content-fit windows too: the row is re-anchored once the window's
    height is finalized (when the view is pushed).
    """
    bx = win.x + 2
    by = stack_below(win.y, win.height, gap=gap)
    buttons = [Button(bx, by, label, on_click=cb) for label, cb in specs]
    layout_buttons(buttons, bx, by, spacing=spacing, width=win.width - 4, align=align)
    view.add(*buttons)
    if getattr(win, '_auto_height', False):
        # Height isn't known yet — remember the row so finalize can re-anchor it.
        win._below_rows = getattr(win, '_below_rows', [])
        win._below_rows.append((buttons, gap))
    return tuple(buttons)


def bind_quit(view, on_quit: Callable[[], None], keys=('q',), escape: bool = True) -> None:
    """Bind quit keys on a view — TextInput-aware.

    Calls on_quit() for Escape (when escape=True) and for any single char in `keys`
    (default 'q'). A char key is ignored while a TextInput is focused, so the user can
    type it normally. Falls through to the existing handler.

        bind_quit(view, self.quit)        # Esc or q quits
        bind_quit(view, do_back)          # any callback (e.g. pop to previous view)

    Marks the view as quit-bound, so TuiApp's AUTO_QUIT skips it — a view that binds
    its own Esc/q behavior (e.g. "go back") keeps it even with AUTO_QUIT = True.
    """
    from .widgets.textinput import TextInput
    view._quit_bound = True
    original = view.handle_key

    def handler(key) -> bool:
        if escape and key.type == KeyType.ESCAPE:
            on_quit(); return True
        if key.type == KeyType.CHAR and key.char in keys:
            typing = any(isinstance(w, TextInput) and w.focused for w in view._focusable)
            if not typing:
                on_quit(); return True
        return original(key)

    view.handle_key = handler


class WindowColumn:
    """Stacks bordered windows vertically in a view, auto-advancing past each drop shadow.

    Mirrors VerticalLayout, but operates on whole Windows and handles the view wiring:
    each .window() call creates the Window, adds it to the view, calls set_view(), and
    advances the cursor by height + shadow + gap (via stack_below) so the next window
    clears the shadow. Removes the manual Y math, the local SHADOW/VGAP constants, and
    the repetitive view.add(...) / set_view(...) boilerplate.

    (For side-by-side windows use TuiApp.columns(); its spacing already matches
    stack_beside().)

    Example:
        col = WindowColumn(view, x=2, y=1, width=34, gap=1)
        out_win    = col.window(3, title='Output File')   # created, added, linked
        status_win = col.window(3, title='Status')
        btn_y      = col.y       # first free row below the column, e.g. a floating button

    Differing widths within one column (pass per-window width):
        col = WindowColumn(view, x=right_x, y=1, gap=1)
        size_win   = col.window(len(SIZES) + 2,  title='Page Size', width=29)
        margin_win = col.window(len(MARGINS) + 2, title='Margins',  width=25)
    """

    def __init__(self, view, x: int, y: int, width: Optional[int] = None,
                 gap: int = 1, shadow: int = SHADOW):
        """Initialize a vertical window stack.

        Args:
            view: View the windows are added to.
            x: Left edge X for every window in the column.
            y: Starting Y of the first window.
            width: Default window width. May be omitted if every .window() call passes width=.
            gap: Blank rows between a window's shadow and the next window (default 1).
            shadow: Drop-shadow extent (default SHADOW=1).
        """
        self.view   = view
        self.x      = x
        self._y     = y
        self.width  = width
        self.gap    = gap
        self.shadow = shadow

    @property
    def y(self) -> int:
        """Current cursor Y — the first free row below the last window's shadow + gap."""
        return self._y

    def window(self, height: int, title: str = '', width: Optional[int] = None,
               icon: str = '') -> Window:
        """Create a Window at the cursor, add+link it to the view, and advance the cursor.

        Returns the Window so you can position children via win.interior()/interior_size().
        """
        w = width if width is not None else self.width
        if w is None:
            raise ValueError(
                "WindowColumn.window() needs a width: set a default width on the "
                "WindowColumn or pass width=... to this call."
            )
        win = Window(self.x, self._y, w, height, title=title, icon=icon)
        self.view.add(win)       # auto-links the view (set_view)
        self._y = stack_below(self._y, height, gap=self.gap, shadow=self.shadow)
        return win

    def gap_rows(self, rows: int = 1) -> None:
        """Insert extra blank rows before the next window (beyond the per-window gap)."""
        self._y += rows


class VerticalLayout:
    """Helper for positioning widgets vertically within a container.

    Automatically manages Y positions, eliminating manual offset calculations.
    Has sensible defaults for spacing (1 line between widgets — compact).

    Example (using defaults):
        # No need to specify spacing — defaults to 1 line between widgets
        layout = VerticalLayout(x=10, y=5, width=40)
        checkbox1 = layout.checkbox('Option 1', checked=True)
        checkbox2 = layout.checkbox('Option 2')

    Example (custom spacing):
        layout = VerticalLayout(x=10, y=5, width=40, spacing=3)  # More spacious
        input1 = layout.input(label='Name')
    """

    DEFAULT_SPACING = 1  # Default space between widgets (compact)

    def __init__(self, x: int, y: int, width: int, spacing: Optional[int] = None,
                 target=None):
        """Initialize vertical layout.

        Args:
            x: Left edge X coordinate
            y: Starting Y coordinate
            width: Width for all widgets
            spacing: Vertical space between widgets. If None, uses DEFAULT_SPACING (1 line)
            target: Optional Window/View — when set, every widget built here is added to
                    it automatically, so you never write a separate `win.add(...)`.
        """
        self.x = x
        self.y = y
        self.width = width
        self.spacing = spacing if spacing is not None else self.DEFAULT_SPACING
        self._current_y = y
        self.target = target

    def _add(self, widget):
        """Register the widget with the target container (if any) and return it."""
        if self.target is not None:
            self.target.add(widget)
        return widget

    def _next_y(self, height: int = 1) -> int:
        """Get next Y position and advance."""
        result = self._current_y
        self._current_y += height + self.spacing
        return result

    def checkbox(self, label: str, checked: bool = False, on_change=None):
        """Add a checkbox widget."""
        from .widgets.checkbox import Checkbox
        return self._add(Checkbox(self.x, self._next_y(), self.width, label, checked, on_change))

    def input(self, label: str = '', placeholder: str = '', password: bool = False,
              on_enter=None, on_change=None):
        """Add a text input widget (2 lines: label + input). `on_enter` fires on Enter;
        `on_change(value)` fires after every user edit (live filtering)."""
        from .widgets.textinput import TextInput
        return self._add(TextInput(self.x, self._next_y(2), self.width, label=label,
                                   password=password, placeholder=placeholder,
                                   on_enter=on_enter, on_change=on_change))

    def label(self, text: str, bold: bool = False, dim: bool = False):
        """Add a label widget — clipped to the layout width at draw time, so neither the
        initial text nor later `.text` updates can overflow the window border."""
        from .widgets.label import Label
        widget = Label(self.x, self._next_y(), text, max_width=self.width)
        if bold:
            widget.bold = bold
        if dim:
            widget.dim = dim
        return self._add(widget)

    def radio_group(self, options: List[str], selected: int = 0, on_change=None):
        """Add a radio group. Options are labels or (label, value) pairs;
        `on_change(index)` fires when the selection moves."""
        from .widgets.radiogroup import RadioGroup
        return self._add(RadioGroup(self.x, self._next_y(len(options)), self.width,
                                    options, selected, on_change=on_change))

    def fill_height(self, footer: bool = True) -> int:
        """Rows from the current cursor down to the footer-button row (or the window
        bottom with footer=False). Requires target to be a fixed-height Window. Replaces
        hand-counted `win.remaining_height(8)`-style arguments — the layout knows what's
        been placed."""
        from .widgets.window import Window
        if not isinstance(self.target, Window):
            raise ValueError('fill_height() needs the layout to target a Window '
                             '(use win.layout() or self.page()).')
        return self.target.fill_height(self._current_y, footer=footer)

    def _box_height(self, height, rows, what: str, chrome: int = 2):
        """Resolve a scroll-box height: `rows=N` means N visible content rows (semantic
        — never eyeballed cells; `chrome` is the widget's own non-content rows, e.g.
        borders, header); no height at all means fill down to the footer."""
        if rows is not None:
            if height is not None:
                raise ValueError(f'{what}: pass height= or rows=, not both.')
            return rows + chrome
        if height is None:
            return self.fill_height()           # raises a clear error in content-fit windows
        return height

    def listbox(self, height: Optional[int] = None, shadow: bool = False,
                rows: Optional[int] = None):
        """Add a listbox. With no size it fills the space left above the footer buttons;
        `rows=5` means "show 5 rows" (works in content-fit windows too)."""
        from .widgets.listbox import Listbox
        height = self._box_height(height, rows, 'listbox')
        return self._add(Listbox(self.x, self._next_y(height), self.width, height, shadow=shadow))

    def table(self, columns, height: Optional[int] = None, title: str = '',
              on_select=None, shadow: bool = False, rows: Optional[int] = None):
        """Add a Table. Columns are specs ('Name' | ('Name', weight) | ('Name', 1, '>')).
        Sizing works like listbox(): no size fills to the footer; `rows=8` shows 8 data
        rows (the header/border chrome is accounted for). Assign `.rows` afterwards."""
        from .widgets.table import Table
        height = self._box_height(height, rows, 'table', chrome=Table.CHROME)
        return self._add(Table(self.x, self._next_y(height), self.width, height,
                               columns=columns, title=title,
                               on_select=on_select, shadow=shadow))

    def textview(self, height: Optional[int] = None, text: str = '', title: str = '',
                 wrap: bool = True, shadow: bool = False, rows: Optional[int] = None):
        """Add a scrollable read-only text view. Sizing works like listbox(): no size
        fills to the footer, `rows=N` shows N text rows."""
        from .widgets.textview import TextView
        height = self._box_height(height, rows, 'textview')
        return self._add(TextView(self.x, self._next_y(height), self.width, height,
                                  text=text, title=title, wrap=wrap, shadow=shadow))

    def spinner(self, label: str = '', frames: str = None, fps: float = 12,
                style: str = 'dots'):
        """Add an activity spinner. `style=` picks a named look ('dots', 'line', 'arc',
        'circle', 'square', 'arrow', 'pulse'); `frames=` overrides with a custom cycle."""
        from .widgets.spinner import Spinner
        return self._add(Spinner(self.x, self._next_y(), label, frames, fps, style=style))

    def progressbar(self, value: float = 0.0, show_percent: bool = True):
        """Add a progress bar spanning the layout width."""
        from .widgets.progressbar import ProgressBar
        return self._add(ProgressBar(self.x, self._next_y(), self.width, value, show_percent))

    def gap(self, lines: int = 1):
        """Add empty space (gap between sections)."""
        self._current_y += lines

    def buttons(self, specs, spacing: int = 3, align: str = 'center') -> tuple:
        """Create, position, and (if a target is set) add a row of buttons at current Y.

        Each spec is a label string or a `(label, on_click)` tuple — pass the callbacks
        inline instead of assigning `.on_click` afterwards:

            lay.buttons([('Sign In', do_login), ('Quit', self.quit)])
            ok, cancel = lay.buttons(['OK', 'Cancel'])     # plain labels still fine

        The row is **centered** in the layout width by default (the Newt look,
        matching dialogs and footer_buttons); align='left'/'right' to anchor it.
        Always returns a tuple so unpacking reads naturally.
        """
        from .widgets.button import Button
        y = self._current_y
        buttons = []
        for spec in specs:
            label, cb = spec if isinstance(spec, tuple) else (spec, None)
            buttons.append(Button(self.x, y, label, on_click=cb))
        layout_buttons(buttons, self.x, y, spacing=spacing,
                       width=self.width, align=align)
        self._current_y += 3 + self.spacing  # Button height (3) + spacing
        for b in buttons:
            self._add(b)
        return tuple(buttons)

    def checkboxes(self, specs, on_change=None) -> tuple:
        """Add a batch of checkboxes — one call instead of one line each.

        Each spec is a label string or a `(label, checked)` tuple:

            prefs = lay.checkboxes(['Notifications', ('Dark mode', True), 'Compact'])
        """
        out = []
        for spec in specs:
            label, checked = spec if isinstance(spec, tuple) else (spec, False)
            out.append(self.checkbox(label, checked=checked, on_change=on_change))
        return tuple(out)


class TuiApp:
    """Base class for TUI applications with built-in helper methods.

    Provides terminal size tracking, view management, dialog helpers, and
    common layout utilities. Subclass and override build_view() to create your app.

    Example:
        class MyApp(TuiApp):
            def build_view(self):
                view = View()
                # ... build your UI ...
                return view

            def __init__(self):
                super().__init__()
                self.push_view(self.build_view())

        if __name__ == '__main__':
            MyApp().run()
    """

    # Esc / q quit the app automatically on every view. Set False in a subclass to
    # manage quit keys yourself (e.g. when Esc means "go up a level").
    AUTO_QUIT = True

    # A status bar with these hints is added to any view that doesn't build its own.
    # Set AUTO_STATUS = False to suppress, or override STATUS_HINT for different text.
    AUTO_STATUS = True
    STATUS_HINT = 'Tab cycle focus   Esc / q quit'

    # Rebuild views automatically when the terminal is resized. Works for any view
    # pushed as a *builder* (`self.push_view(self.build_view)` — note: no parentheses);
    # the builder is re-run with the new terminal size, so centered_window() and friends
    # re-center for free. Views pushed as plain View objects are left untouched.
    # Set False if your views hold state in widgets that a rebuild would lose.
    AUTO_RESIZE = True

    # Push `self.build_view` automatically (as a builder) when the subclass defines it,
    # so the standard app needs no __init__ at all. Set False to push views yourself.
    AUTO_VIEW = True

    def __init__(self, theme=None):
        """Initialize TuiApp with optional theme.

        If the subclass defines `build_view`, it is pushed automatically (`AUTO_VIEW`),
        so most apps don't override __init__ at all. Initialize app state in `setup()`
        — or, when the constructor takes arguments, set it *before* super().__init__():

            class TodoApp(TuiApp):
                def setup(self):
                    self.todos = load_todos()       # runs before build_view
                def build_view(self): ...

            class GitLog(TuiApp):
                def __init__(self, repo=None):
                    self.repo = repo or Path.cwd()  # state first — build_view needs it
                    super().__init__()              # auto-pushes build_view
        """
        from .app import App
        from .core.event import Key, KeyType
        self._app = App(theme)
        self._app.on_resize = self._rebuild_views
        self.ts = TerminalSizeProvider(self._app)
        self.KeyType = KeyType  # For convenience
        self.setup()
        if self.AUTO_VIEW and hasattr(type(self), 'build_view') and not self._app._views:
            self.push_view(self.build_view)

    def setup(self):
        """Override to initialize app state — runs before the first view is built."""

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped App."""
        if name == '_app':
            # __init__ hasn't run (or didn't finish) — without this guard the
            # delegation recurses forever and the real cause is buried.
            raise AttributeError(
                "this TuiApp has no _app yet — an __init__ override must call "
                "super().__init__() (after setting any state build_view needs)")
        return getattr(self._app, name)

    def _auto_wire(self, view):
        if view is None:
            return
        self._finalize_auto_windows(view)
        if self.AUTO_QUIT and not getattr(view, '_quit_bound', False):
            bind_quit(view, self.quit)
            view._quit_bound = True
        if self.AUTO_STATUS and self.STATUS_HINT and not getattr(view, '_has_status', False):
            self.status_bar(view, self.STATUS_HINT)

    @staticmethod
    def _finalize_auto_windows(view):
        """Fit every content-fit window to what was placed in it, then re-anchor any
        buttons_below rows that were waiting on the final height."""
        for w in view._all:
            if isinstance(w, Window) and getattr(w, '_auto_height', False):
                w.fit_content_height()
                for buttons, gap in getattr(w, '_below_rows', []):
                    by = stack_below(w.y, w.height, gap=gap)
                    for b in buttons:
                        b.y = by

    @staticmethod
    def _resolve_view(view):
        """Accept a View, a Page (unwrapped to its view), or a zero-arg builder
        returning either. A builder is remembered on the view, so AUTO_RESIZE can
        re-run it when the terminal resizes."""
        builder = None
        if callable(view):
            builder = view
            view = builder()
        if isinstance(view, Page):
            view = view.view
        if builder is not None:
            view._builder = builder
        return view

    def _rebuild_views(self, w, h):
        """On terminal resize, re-run the builder of every view that has one (AUTO_RESIZE)."""
        if not self.AUTO_RESIZE:
            return
        views = self._app._views
        for i, old in enumerate(views):
            builder = getattr(old, '_builder', None)
            if builder is None:
                continue
            view = builder()
            if isinstance(view, Page):
                view = view.view
            view._builder = builder
            views[i] = view
            self._auto_wire(view)
            view.focus_first()

    def columns(self, view, spec=2, titles: Optional[List[str]] = None,
                height=None, width=0.9, gap: int = 2, y: Optional[int] = None) -> tuple:
        """Split the terminal into side-by-side windows — no coordinates, no cell counts.

        `spec` is a column count (equal widths) or a list of weights; widths are derived
        from the terminal, shadow-aware, and the block is centered:

            left, right = self.columns(view, 2, titles=['Preferences', 'Protocol'])
            main, side  = self.columns(view, [2, 1])     # 2:1 split

        `height` defaults to **content-fit**: each window wraps whatever you put in it
        (finalized when the view is pushed). Pass a fraction (`0.7`), cells, or a list
        for fixed heights. `width` is the whole block (fraction of the terminal or cells).
        The windows are added + linked to the view and returned as a tuple.
        """
        W, H = self.ts.width(), self.ts.height()
        weights = [1] * spec if isinstance(spec, int) else list(spec)
        n = len(weights)
        total  = min(resolve_size(width, W), W - 2)
        usable = total - (n - 1) * (SHADOW + gap)
        widths = [max(4, usable * w // sum(weights)) for w in weights]
        widths[-1] += usable - sum(widths)              # give rounding remainder to the last

        heights = height if isinstance(height, (list, tuple)) else [height] * n
        fixed   = [None if h is None else resolve_size(h, H) for h in heights]
        est     = max([h for h in fixed if h is not None], default=H // 2)
        wy      = y if y is not None else max(1, (H - est - 4) // 2)

        wins, x = [], (W - total) // 2
        for i in range(n):
            h = fixed[i]
            win = Window(x, wy, widths[i], h if h is not None else H - wy - 2,
                         title=(titles[i] if titles and i < len(titles) else ''))
            if h is None:
                win._auto_height = True                 # finalized on push_view
            view.add(win)
            wins.append(win)
            x = stack_beside(x, widths[i], gap=gap)
        return tuple(wins)

    # ── View Management ──────────────────────────────────────────────────

    def push_view(self, view):
        """Push a view (auto-wires Esc/q quit + a default status bar unless disabled).

        Pass the *builder* rather than a built view to get automatic resize handling:

            self.push_view(self.build_view)     # rebuilt on terminal resize
            self.push_view(self.build_view())   # also fine — but fixed at this size
        """
        view = self._resolve_view(view)
        result = self._app.push_view(view)
        self._auto_wire(view)
        return result

    def pop_view(self):
        """Pop the current view from the stack."""
        return self._app.pop_view()

    def replace_view(self, view):
        """Replace the current view (auto-wires quit + default status bar unless disabled).

        Like push_view, accepts a zero-arg builder for automatic resize handling —
        capture any arguments first: `self.replace_view(lambda: self.build_page(name))`.
        """
        view = self._resolve_view(view)
        result = self._app.replace_view(view)
        self._auto_wire(view)
        return result

    # ── Dialog Management ────────────────────────────────────────────────

    def show_dialog(self, dialog):
        """Show a modal dialog."""
        return self._app.show_dialog(dialog)

    def close_dialog(self):
        """Close the current dialog."""
        return self._app.close_dialog()

    def show_message(self, title: str, message: str, buttons: Optional[List[str]] = None,
                    on_close: Optional[Callable] = None, max_width=0.6):
        """Show a message dialog. The dialog closes itself on any button — `on_close`
        is optional and just says what to *do* after (it receives the button label).

            self.show_message('File Info', msg)                 # plain OK, auto-closes
            self.show_message('Saved', msg, on_close=after)     # run after() on close

        Returns the Dialog instance.
        """
        W, H = self.ts.width(), self.ts.height()
        dialog = Dialog(W, H, title=title, message=message,
                        buttons=buttons or ['OK'], on_close=on_close, max_width=max_width)
        self.show_dialog(dialog)
        return dialog

    def confirm(self, title: str, message: str, on_yes: Callable[[], None],
                yes: str = 'Yes', no: str = 'No', on_no: Optional[Callable[[], None]] = None):
        """Show a yes/no confirmation. Auto-closes, then calls `on_yes()` if the user
        chose `yes` (or `on_no()` for `no`). Escape selects `no`.

            self.confirm('Quit?', 'Are you sure?', self.quit)
        """
        def _on_close(label: str):
            if label == yes:
                on_yes()
            elif on_no:
                on_no()
        return self.show_message(title, message, buttons=[yes, no], on_close=_on_close)

    # ── Background work ──────────────────────────────────────────────────

    def _sole_widget(self, cls):
        """The current view's only widget of `cls`, or None (zero or several)."""
        view = self._app.current_view
        if view is None:
            return None
        found = []
        for w in view._all:
            if isinstance(w, cls):
                found.append(w)
            found.extend(k for k in getattr(w, '_kids', []) if isinstance(k, cls))
        return found[0] if len(found) == 1 else None

    def run_task(self, fn, *args, progress=AUTO, spinner=AUTO, status=None,
                 running: Optional[str] = None,
                 done: Optional[str] = None, error: Optional[str] = None,
                 on_done: Optional[Callable] = None,
                 on_error: Optional[Callable] = None, **kwargs) -> bool:
        """Run `fn(*args, **kwargs)` on a background worker — the whole worker-thread
        ceremony (guard, progress/spinner wiring, error handling, status text, thread
        spawn) in one call. The fully-wired form is one line:

            self.run_task(long_task, status=self.status, running='Working…')
            self.run_task(download, status=self.done, done='Complete ✓')
            self.run_task(copy_file, src, dst, status=self.status,
                          running=f'Copying {src.name} …',
                          on_done=lambda n: f'✓ {n:,} bytes',
                          on_error=lambda e: f'✗ {e}')

        Parameters follow the library-wide naming rule (same as confirm's yes=/on_yes=):
        **a bare noun is a value, an on_-noun is a callable.** `running`/`done`/`error`
        are status texts; `on_done(result)`/`on_error(exc)` are callbacks for behavior
        or dynamic text.

        Progress and spinner are **found automatically**: if the current view contains
        exactly one ProgressBar it is reset to 0, fn receives an `on_progress` callback
        (the cookieui engine convention), and the bar fills to 1.0 on success; if the
        view contains exactly one Spinner it is shown while the task runs and hidden
        after. Pass `progress=`/`spinner=` to target a specific widget, or None to
        disable.

        Textual outcomes flow to the `status` widget — and **with no status=, the
        progress bar itself is the status area**: running/done/error texts render
        centered on the bar face, installer-style (the bar is a self-contained
        widget; no separate label needed):
          • running='…' is shown the moment the task actually starts
          • done='Saved ✓' is shown on success. Need dynamic text or behavior? Use
            on_done=fn(result) — its returned string is shown when done= is absent
            (return None if you updated the UI yourself). Both together work: on_done
            runs for behavior, done= supplies the text. With neither, str(result) is
            shown — an engine that returns its message needs nothing
          • error='✗ failed' / on_error=fn(exc) mirror it; with neither, status shows
            'Error: …', or an Error dialog when there is no status — failures are
            never silently lost

        Also: single-flight guard (returns False and does nothing while a previous
        task is still running), daemon worker thread, busy flag reset in finally.
        `fn` should be a pure domain function — PATTERNS.md "The domain/UI boundary
        rule".
        """
        import threading
        from .widgets.progressbar import ProgressBar
        from .widgets.spinner import Spinner

        if isinstance(on_done, str) or isinstance(on_error, str):
            raise TypeError("on_done/on_error are callbacks — for static text use "
                            "done='…' / error='…' (bare noun = value, on_noun = callable)")
        if getattr(self, '_task_busy', False):
            return False
        self._task_busy = True

        if progress is AUTO:
            progress = self._sole_widget(ProgressBar)
        if spinner is AUTO:
            spinner = self._sole_widget(Spinner)

        if spinner is not None:
            spinner.visible = True
        if progress is not None:
            progress.value = 0.0
            progress.text  = ''                          # clear any previous overlay
            kwargs['on_progress'] = lambda f: setattr(progress, 'value', f)
            if status is None:
                status = progress                        # the bar IS the status area:
                                                         # texts render centered on it
        if status is not None and running is not None:
            status.text = running

        def _show(text):
            if status is not None and isinstance(text, str):
                status.text = text

        def _outcome(value, handler, arg, fallback):
            """The noun param (value) owns the display; the on_-param (handler) runs
            for behavior and supplies the text only when no value was given."""
            text = handler(arg) if handler else None
            if value is not None:
                return value
            return text if handler else fallback

        def _work():
            try:
                result = fn(*args, **kwargs)
                if progress is not None:
                    progress.value = 1.0
                _show(_outcome(done, on_done, result, str(result)))
            except Exception as e:
                if status is None and on_error is None:
                    self.show_message('Error', error if error is not None else str(e))
                else:
                    _show(_outcome(error, on_error, e, f'Error: {e}'))
            finally:
                if spinner is not None:
                    spinner.visible = False
                self._task_busy = False

        threading.Thread(target=_work, daemon=True).start()
        return True

    def prompt(self, title: str, message: str = '', on_submit: Optional[Callable[[str], None]] = None,
               default: str = '', placeholder: str = '', password: bool = False,
               ok: str = 'OK', cancel: str = 'Cancel',
               on_cancel: Optional[Callable[[], None]] = None, max_width=0.6):
        """Ask for a line of text in a modal dialog — `on_submit(text)` runs when the
        user presses Enter (or the OK button); Escape/Cancel runs `on_cancel` if given.
        Auto-closes like all dialogs.

            self.prompt('New task', 'What needs doing?', on_submit=add_task)
        """
        from .widgets.dialog import InputDialog
        dlg = InputDialog(self.ts.width(), self.ts.height(), title, message,
                          default=default, placeholder=placeholder, password=password,
                          buttons=[ok, cancel], max_width=max_width)

        def _on_close(label: str):
            if label == ok and on_submit:
                on_submit(dlg.value)
            elif label != ok and on_cancel:
                on_cancel()

        dlg._on_close = _on_close
        self.show_dialog(dlg)
        return dlg

    def choose(self, title: str, items, on_pick: Optional[Callable] = None,
               message: str = '', ok: str = 'OK', cancel: str = 'Cancel',
               on_cancel: Optional[Callable[[], None]] = None,
               list_height: Optional[int] = None, max_width=0.6):
        """Pick one entry from a list in a modal dialog — `on_pick(value)` runs when the
        user presses Enter on a row (or the OK button). Items follow the Listbox
        convention: plain labels, or `(label, value)` pairs so `on_pick` receives the
        paired domain object. Escape/Cancel runs `on_cancel` if given.

            self.choose('Branch', branches, on_pick=checkout)
            self.choose('Theme', [('Newt blue', DEFAULT), ('Mocha', MOCHA)], on_pick=apply)
        """
        from .widgets.dialog import ChoiceDialog
        dlg = ChoiceDialog(self.ts.width(), self.ts.height(), title, items,
                           message=message, list_height=list_height,
                           buttons=[ok, cancel], max_width=max_width)

        def _on_close(label: str):
            if label == ok and on_pick:
                on_pick(dlg.value)
            elif label != ok and on_cancel:
                on_cancel()

        dlg._on_close = _on_close
        self.show_dialog(dlg)
        return dlg

    # ── Layout Helpers ───────────────────────────────────────────────────

    def page(self, width=0.6, height=None, title: str = '', icon: str = '',
             pad_x: int = 1, pad_y: int = 0, spacing: int = 1) -> 'Page':
        """One-call scaffold for the standard view: a fresh View, a centered Window
        (auto-clamped to the terminal, auto-linked), and the window's layout — the
        opening ceremony of every build_view collapsed to a single line:

            def build_view(self):
                view, win, lay = self.page(0.5, title='Sign In')
                usr = lay.input('Username')
                ...
                return view

        Sizes are intent, not eyeballed cells: floats <= 1.0 are **fractions of the
        terminal** (`0.5` = half), ints are exact cells.

        **Omit `height` for content-fit windows** (forms, menus, button panels — the
        window wraps whatever the layout places, finalized when the view is pushed);
        **pass `height` when the window contains a listbox/textview or other fill
        widget** (`page(0.7, 0.8)`) — "fill the window" needs a fixed window to fill.
        In a content-fit window, size scroll boxes with `rows=5` and put buttons in
        the flow (`lay.buttons`); getting this wrong raises a ValueError that says so.

        `pad_x`/`pad_y`/`spacing` pass through to win.layout(). The return is a
        NamedTuple: unpack it (use `_` for parts this view doesn't need — different
        views need different subsets), or keep it whole and use `.view`/`.win`/`.lay`
        attributes if you'd rather not write placeholders.
        """
        from .app import View
        view = View()
        W, H = self.ts.width(), self.ts.height()
        if height is None:
            ww = min(resolve_size(width, W), W - 2)
            wx = (W - ww) // 2
            wy = max(1, (H - H // 2 - 4) // 2)          # anchor as if half-terminal tall
            win = Window(wx, wy, ww, H - wy - 2, title=title, icon=icon)
            win._auto_height = True                      # finalized on push_view
        else:
            wx, wy, ww, wh = self.centered_window(resolve_size(width, W),
                                                  resolve_size(height, H))
            win = Window(wx, wy, ww, wh, title=title, icon=icon)
        view.add(win)
        return Page(view, win, win.layout(pad_x=pad_x, pad_y=pad_y, spacing=spacing))

    def centered_window(self, desired_w: int, desired_h: int) -> tuple:
        """Get position and size for a centered window.

        Returns: (x, y, width, height)
        """
        W, H = self.ts.width(), self.ts.height()
        return calculate_centered_window(W, H, desired_w, desired_h)

    def status_bar(self, view, text: str, align: str = 'center') -> Window:
        """Create a status bar at the bottom (text centered; align='left'/'right')."""
        W, H = self.ts.width(), self.ts.height()
        return create_status_bar(view, W, H, text, align=align)

    # ── Application Control ──────────────────────────────────────────────

    def run(self):
        """Start the application."""
        return self._app.run()

    def quit(self):
        """Quit the application."""
        self._app.quit()

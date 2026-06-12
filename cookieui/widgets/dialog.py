from typing import Optional, Callable, List

from .base import Widget
from .button import Button
from ..core.event import Key, KeyType
from ..core.screen import Screen
from ..theme import Theme


class Dialog(Widget):
    """Modal dialog — drawn over the current scene with a darkened overlay.

    Buttons are managed internally; the dialog handles its own Tab cycle.
    The caller receives a result via the on_close callback:
        on_close(button_label: str)
    """
    focusable = True

    @staticmethod
    def _cap(screen_w: int, max_width) -> int:
        """Resolve the dialog's width cap: a fraction of the screen (sizing-model
        semantics) and never wider than the screen minus a margin."""
        from ..helpers import resolve_size
        return min(resolve_size(max_width, screen_w), screen_w - 4)

    @classmethod
    def _wrap(cls, message: str, screen_w: int, max_width) -> str:
        """Word-wrap message lines to the width cap so dialogs never balloon past
        `max_width` of the screen. Blank/space-only lines (used as row reserves by
        InputDialog/ChoiceDialog) are truncated, not wrapped — their row count is
        load-bearing."""
        from .textview import TextView
        wrap_w = max(10, cls._cap(screen_w, max_width) - 6)   # borders + padding
        out = []
        for line in message.split('\n'):
            if not line.strip():
                out.append(line[:wrap_w])
            elif len(line) <= wrap_w:
                out.append(line)
            else:
                out.extend(TextView._wrap_line(line, wrap_w))
        return '\n'.join(out)

    def __init__(self, screen_w: int, screen_h: int,
                 title: str, message: str,
                 buttons: Optional[List[str]] = None,
                 on_close: Optional[Callable[[str], None]] = None,
                 icon: str = '', max_width=0.6):
        buttons   = buttons or ['OK']
        message   = self._wrap(message, screen_w, max_width)
        self.title    = title
        self.message  = message
        self._icon    = icon
        self._on_close = on_close

        # Auto-size: wide enough for the longest line + padding, capped at max_width
        msg_lines = message.split('\n')
        # Button width: max(12, len(label) + 6) per button, plus spacing between them, plus shadow on right
        btn_width = sum(max(12, len(b) + 6) for b in buttons) + (len(buttons) - 1) * 2 + 1
        inner_w   = max(len(title) + 4,
                        max(len(l) for l in msg_lines) + 4,
                        btn_width)
        inner_w   = max(inner_w, 36)
        inner_w   = min(inner_w, self._cap(screen_w, max_width) - 2)
        height    = 2 + len(msg_lines) + 1 + 3 + 1 + 1  # border(2) + msg + gap + btns(3) + shadow(1) + gap

        x = (screen_w - inner_w - 2) // 2
        y = (screen_h - height)      // 2
        super().__init__(x, y, inner_w + 2, height)

        # Build button widgets — positioned with space for button height (3) + shadow (1)
        self._btns: List[Button] = []
        # Use the same width calculation as for dialog sizing to ensure buttons fit
        total_btn_w = sum(max(12, len(b) + 6) for b in buttons) + (len(buttons) - 1) * 2 + 1
        bx = self.x + 1 + (inner_w - total_btn_w) // 2

        btn_y = self.y + height - 5
        for label in buttons:
            btn = Button(bx, btn_y, label, on_click=lambda l=label: self._close(l))
            self._btns.append(btn)
            bx += btn.width + 2

        self._focus_idx = 0
        if self._btns:
            self._btns[0].focused = True

    def _close(self, label: str):
        if self._on_close:
            self._on_close(label)

    def draw(self, screen: Screen, theme: Theme):
        t = theme

        # The chrome draws the surface (raised fill + elevated border + title)
        bg = t.chrome.dialog_frame(screen, theme, self.x, self.y,
                                   self.width, self.height,
                                   title=self.title, icon=self._icon)

        # Message lines (centered)
        msg_lines = self.message.split('\n')
        for i, line in enumerate(msg_lines):
            mx = self.x + max(1, (self.width - len(line)) // 2)
            screen.write(mx, self.y + 2 + i, line, fg=t.text, bg=bg)

        # Buttons
        for btn in self._btns:
            btn.draw(screen, theme)

        # Drop shadow — drawn last so it tints whatever is behind the dialog
        # Only draw if shadow won't exceed screen bounds
        if (self.x + self.width < screen.width and
            self.y + self.height < screen.height):
            t.chrome.shadow(screen, theme, self.x, self.y, self.width, self.height)

    def handle_key(self, key: Key) -> bool:
        if not self._btns:
            return False

        btn = self._btns[self._focus_idx]
        if btn.handle_key(key):
            return True

        # Tab / Shift-Tab cycle dialog buttons
        if key.type == KeyType.TAB:
            btn.focused = False
            self._focus_idx = (self._focus_idx + 1) % len(self._btns)
            self._btns[self._focus_idx].focused = True
            return True
        if key.type == KeyType.SHIFT_TAB:
            btn.focused = False
            self._focus_idx = (self._focus_idx - 1) % len(self._btns)
            self._btns[self._focus_idx].focused = True
            return True
        if key.type == KeyType.ESCAPE:
            self._close(self._btns[-1].label)   # last button = Cancel/No
            return True

        return False


class InputDialog(Dialog):
    """Dialog with a single text-entry field — backs `TuiApp.prompt()`.

    The field is focused first; Enter submits (closes with the first button's label),
    Tab cycles field → buttons → field, Escape cancels (last button). Read the entered
    text from `.value` (typically inside the on_close callback).
    """

    def __init__(self, screen_w: int, screen_h: int, title: str, message: str = '',
                 default: str = '', placeholder: str = '', password: bool = False,
                 buttons: Optional[List[str]] = None,
                 on_close: Optional[Callable[[str], None]] = None, icon: str = '',
                 max_width=0.6):
        from .textinput import TextInput

        # Wrap FIRST so the row count below is final (Dialog's own wrap is then a no-op),
        # then reserve rows in the message block: the message, a gap row, the entry row.
        message   = self._wrap(message, screen_w, max_width) if message else ''
        msg_lines = message.split('\n') if message else []
        synthetic = '\n'.join(msg_lines + ['', ''])
        super().__init__(screen_w, screen_h, title, synthetic,
                         buttons or ['OK', 'Cancel'], on_close, icon, max_width=max_width)

        entry_y = self.y + 2 + len(msg_lines) + 1
        self._input = TextInput(self.x + 3, entry_y, self.width - 6,
                                placeholder=placeholder, password=password)
        self._input.set_value(default)

        # Focus order: entry field first, then the buttons.
        self._btns[0].focused = False
        self._input.focused = True
        self._order = [self._input] + self._btns
        self._oidx  = 0

    @property
    def value(self) -> str:
        """The entered text."""
        return self._input.value

    def draw(self, screen: Screen, theme: Theme):
        super().draw(screen, theme)
        self._input.draw(screen, theme)

    def handle_key(self, key: Key) -> bool:
        kt = key.type
        if kt == KeyType.ESCAPE:
            self._close(self._btns[-1].label)
            return True
        cur = self._order[self._oidx]
        if cur is self._input and kt == KeyType.ENTER:
            self._close(self._btns[0].label)    # Enter in the field = first button (OK)
            return True
        if kt == KeyType.TAB:
            self._cycle_focus(+1); return True
        if kt == KeyType.SHIFT_TAB:
            self._cycle_focus(-1); return True
        return cur.handle_key(key)

    def _cycle_focus(self, direction: int):
        self._order[self._oidx].focused = False
        self._oidx = (self._oidx + direction) % len(self._order)
        self._order[self._oidx].focused = True


class ChoiceDialog(Dialog):
    """Dialog with a scrollable list of choices — backs `TuiApp.choose()`.

    Items follow the Listbox convention: plain labels or `(label, value)` pairs.
    The list is focused first; Enter picks the highlighted row (closes with the first
    button's label), Tab cycles list → buttons → list, Escape cancels (last button).
    Read the picked value from `.value` (typically inside the on_close callback).
    """

    def __init__(self, screen_w: int, screen_h: int, title: str, items,
                 message: str = '', list_height: Optional[int] = None,
                 buttons: Optional[List[str]] = None,
                 on_close: Optional[Callable[[str], None]] = None, icon: str = '',
                 max_width=0.6):
        from .listbox import Listbox

        items  = list(items)
        list_h = list_height or min(12, max(4, len(items) + 2))

        # Wrap FIRST so the row count below is final, then reserve rows for the list
        # (gap row + list rows) and widen the dialog to fit the longest label — the
        # width-hint line is spaces, so it renders invisibly (and truncates, never
        # wraps, when it exceeds the cap).
        message    = self._wrap(message, screen_w, max_width) if message else ''
        labels = [entry[0] if isinstance(entry, tuple) else str(entry) for entry in items]
        width_hint = ' ' * (max((len(l) for l in labels), default=0) + 6)
        msg_lines  = message.split('\n') if message else []
        synthetic  = '\n'.join(msg_lines + [width_hint] + [''] * list_h)
        super().__init__(screen_w, screen_h, title, synthetic,
                         buttons or ['OK', 'Cancel'], on_close, icon, max_width=max_width)

        list_y = self.y + 2 + len(msg_lines) + 1
        self._list = Listbox(self.x + 2, list_y, self.width - 4, list_h,
                             items=items, shadow=False,
                             on_select=lambda i, lbl: self._close(self._btns[0].label))

        # Focus order: list first, then the buttons.
        self._btns[0].focused = False
        self._list.focused = True
        self._order = [self._list] + self._btns
        self._oidx  = 0

    @property
    def value(self):
        """The picked row's value (`selected_value` of the embedded Listbox)."""
        return self._list.selected_value

    def draw(self, screen: Screen, theme: Theme):
        super().draw(screen, theme)
        self._list.draw(screen, theme)

    def handle_key(self, key: Key) -> bool:
        kt = key.type
        if kt == KeyType.ESCAPE:
            self._close(self._btns[-1].label)
            return True
        if kt == KeyType.TAB:
            self._cycle_focus(+1); return True
        if kt == KeyType.SHIFT_TAB:
            self._cycle_focus(-1); return True
        return self._order[self._oidx].handle_key(key)

    def _cycle_focus(self, direction: int):
        self._order[self._oidx].focused = False
        self._oidx = (self._oidx + direction) % len(self._order)
        self._order[self._oidx].focused = True

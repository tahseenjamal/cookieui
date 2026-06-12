from .base import Widget
from ..core.event import KeyType


class Window(Widget):
    """Bordered container. Not itself a Tab stop; its children are.

    Usage:
      win = Window(x, y, w, h, title='...')
      view.add(win)
      win.set_view(view)          # Tell window about the parent view
      win.add(child1, child2)     # Children auto-register with view

    Behavior:
    • window.add() registers children to both window (drawing) and view (Tab cycling)
    • Tab cycles through all focusable widgets in the view (flat global list)
    • Arrow keys navigate between children *within* this window only
    """
    focusable = False   # Window is a container, not a Tab stop

    def __init__(self, x: int, y: int, width: int, height: int,
                 title: str = '', icon: str = '', shadow: bool = True):
        super().__init__(x, y, width, height)
        self.title  = title
        self.icon   = icon
        self.shadow = shadow   # shadow=False also stops the draw-time edge shift
                               # reserving a shadow row/col (e.g. a bottom status bar)
        self._kids:          list = []
        self._focusable_kids: list = []
        self._kid_idx: int   = 0
        self._parent_view    = None   # Set by set_view()

    # ── View registration ────────────────────────────────────────────

    def set_view(self, view):
        """Registers this window with a View so children can be added to Tab cycle."""
        self._parent_view = view
        return self

    def interior(self) -> tuple:
        """Return (x, y) for interior positioning (accounting for border).

        Window borders take 1 column left and 1 row top, so interior starts at (+1, +1).
        But common practice is (+2, +2) for padding. For consistency across the layout
        helpers, use +1, +1 to stay as close to the border as possible.

        Usage:
            win = Window(10, 5, 40, 15, title='My Window')
            ix, iy = win.interior()
            win.add(Button(ix, iy, 'OK'))  # No manual +2 needed!
        """
        return (self.x + 1, self.y + 1)

    def interior_size(self) -> tuple:
        """Return (width, height) for interior content (accounting for borders).

        Subtracts 2 from width and height to account for left+right and top+bottom borders.

        Usage:
            iw, ih = win.interior_size()
            layout = VerticalLayout(*win.interior(), iw)
        """
        return (self.width - 2, self.height - 2)

    def interior_rect(self) -> tuple:
        """Return (x, y, width, height) of the content area in one call — the common
        pairing of interior() + interior_size()."""
        x, y = self.interior()
        w, h = self.interior_size()
        return (x, y, w, h)

    def layout(self, pad_x: int = 1, pad_y: int = 0, spacing: int = 1):
        """Return a VerticalLayout anchored inside this window's content area, targeting
        this window — so widgets it builds are added automatically (no `win.add`):

            lay = win.layout()
            lay.input('Name')           # created, positioned, AND added to the window
            lay.checkbox('Enable')

        `pad_x`/`pad_y` are padding *inside* the border (default: 1 column each side,
        flush to the top — the common Newt look). Use `.x`/`.y`/`.width` on the returned
        layout as an anchor when a row needs custom placement (then `win.add` it yourself).
        """
        from ..helpers import VerticalLayout
        return VerticalLayout(self.x + 1 + pad_x, self.y + 1 + pad_y,
                              self.width - 2 - 2 * pad_x, spacing=spacing, target=self)

    def fill_height(self, y: int, footer: bool = True) -> int:
        """Height for a widget starting at absolute row `y` that fills the rest of the
        interior — stopping one clear row above the footer_buttons row (footer=True),
        or running to the window bottom (footer=False).

        Replaces hand-counted `remaining_height(8)`-style math: the footer geometry is
        derived from the same calculation footer_buttons uses, so the numbers can't drift.

            ix, iy, iw, ih = win.interior_rect()
            tv = TextView(ix, iy, iw, win.fill_height(iy), text)
            footer_buttons(win, [('Back', back), ('Quit', app.quit)])
        """
        if getattr(self, '_auto_height', False):
            raise ValueError(
                "this window is content-fit (page()/columns() got no height), so there is "
                "no fixed space to fill. Either give the window a height — e.g. "
                "page(0.7, 0.8) — or size this widget semantically with rows=5."
            )
        from ..helpers import calculate_footer_position
        _, iy = self.interior()
        _, ih = self.interior_size()
        if footer:
            return calculate_footer_position(iy, ih) - y - 1
        return iy + ih - y

    def fill_with(self, widget_cls, *args, footer: bool = True, **kwargs):
        """Create a widget that fills this window's interior, and add it — one call.

        The window already knows its interior bounds and how much space is free above
        the footer buttons, so the caller shouldn't have to ask for them, destructure
        them, and hand them right back:

            tv      = win.fill_with(TextView, output, wrap=False)
            browser = win.fill_with(FileBrowser, start_dir, on_select=open_file)

        `widget_cls` must take `(x, y, width, height, ...)` as its first arguments —
        the convention every cookieui widget follows; `*args`/`**kwargs` are the
        widget's *content* arguments. `shadow=False` is applied automatically when the
        widget supports it (a widget filling a window is already inside one);
        pass `shadow=True` to override. `footer=False` fills to the window bottom
        instead of stopping above the footer-button row.
        """
        import inspect
        ix, iy, iw, _ = self.interior_rect()
        h = self.fill_height(iy, footer=footer)     # clear error on content-fit windows
        params = inspect.signature(widget_cls.__init__).parameters
        accepts_shadow = 'shadow' in params or any(
            p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
        if accepts_shadow:
            kwargs.setdefault('shadow', False)
        widget = widget_cls(ix, iy, iw, h, *args, **kwargs)
        self.add(widget)
        return widget

    def fit_content_height(self) -> int:
        """Shrink/grow the window so its bottom border sits just below its lowest child
        (counting a child's drop shadow). Backs content-fit windows — `page()`/`columns()`
        with no height call this automatically when the view is pushed."""
        bottom = self.y + 1                      # at least one interior row
        for k in self._kids:
            kb = k.y + k.height - 1 + (1 if getattr(k, 'shadow', False) else 0)
            bottom = max(bottom, kb)
        self.height = bottom - self.y + 2        # + bottom border
        return self.height

    def fit_content_width(self) -> int:
        """Widen the window so its right border clears its widest child (counting the
        child's drop shadow) — never narrows. The width companion of fit_content_height:
        in a content-fit window, a row wider than the requested width (a long row of
        buttons, say) stretches the window instead of bleeding through its border."""
        right = self.x + self.width - 2          # rightmost interior column
        for k in self._kids:
            kr = k.x + k.width - 1 + (1 if getattr(k, 'shadow', False) else 0)
            right = max(right, kr)
        self.width = max(self.width, right - self.x + 2)   # + right border column
        return self.width

    # ── Child management ─────────────────────────────────────────────

    def add(self, *widgets) -> 'Window':
        """Add children to this window. If view is set, also register with view Tab list."""
        for w in widgets:
            self._kids.append(w)
            is_focusable = getattr(w, 'focusable', True)
            if is_focusable:
                self._focusable_kids.append(w)
                # Register with parent view's Tab cycle if view was set
                if self._parent_view:
                    self._parent_view._focusable.append(w)
        return self

    def focus_child(self, widget) -> bool:
        """Jump focus directly to a specific child widget."""
        for i, w in enumerate(self._focusable_kids):
            if w is widget:
                if self._focusable_kids:
                    self._focusable_kids[self._kid_idx % len(self._focusable_kids)].focused = False
                self._kid_idx = i
                w.focused = True
                return True
        return False

    @property
    def focused_child(self):
        if not self._focusable_kids:
            return None
        return self._focusable_kids[self._kid_idx % len(self._focusable_kids)]

    # ── Drawing ───────────────────────────────────────────────────────

    def draw(self, screen, theme):
        # Adjust position/size to keep window (and its shadow, when it has one)
        # within screen bounds. A shadowless window (e.g. the status bar flush with
        # the bottom row) reserves nothing — shifting it would detach it from its
        # children, which draw at their own absolute coordinates.
        reserve = 1 if self.shadow else 0
        draw_x = self.x
        draw_y = self.y
        draw_w = self.width
        draw_h = self.height

        # If window + shadow would exceed right edge, shift left
        if draw_x + draw_w + reserve > screen.width:
            draw_x = max(0, screen.width - draw_w - reserve)

        # If window + shadow would exceed bottom edge, shift up
        if draw_y + draw_h + reserve > screen.height:
            draw_y = max(0, screen.height - draw_h - reserve)

        # The chrome draws the surface (fill + border + title)
        theme.chrome.window_frame(screen, theme, draw_x, draw_y, draw_w, draw_h,
                                  title=self.title, icon=self.icon)

        # Draw children (drawn on top of window fill, inheriting surface bg)
        for child in self._kids:
            if child.visible:
                child.draw(screen, theme)

        # Drop shadow — drawn after content so it tints what's behind
        if self.shadow:
            theme.chrome.shadow(screen, theme, draw_x, draw_y, draw_w, draw_h)

    # ── Key handling ──────────────────────────────────────────────────

    def handle_key(self, key) -> bool:
        """Handle keys for the focused child. Arrow keys cycle between children."""
        if not self._focusable_kids:
            return False

        # Sync with focus changes made outside this window (the View's Tab cycle):
        # without this, _kid_idx goes stale after a Tab and the arrow keys would
        # unfocus/move from the *old* position while the Tab-focused child stays
        # highlighted — two cursors at once.
        for i, kid in enumerate(self._focusable_kids):
            if kid.focused:
                self._kid_idx = i
                break

        fc = self.focused_child

        # Delegate to the focused child first
        if fc and fc.handle_key(key):
            return True

        # Arrow keys cycle between children within this window.
        # This only fires when the focused child did not consume the key.
        n = len(self._focusable_kids)
        if n < 2:
            return False

        if key.type in (KeyType.DOWN, KeyType.RIGHT):
            self._focusable_kids[self._kid_idx % n].focused = False
            self._kid_idx = (self._kid_idx + 1) % n
            self._focusable_kids[self._kid_idx].focused = True
            return True

        if key.type in (KeyType.UP, KeyType.LEFT):
            self._focusable_kids[self._kid_idx % n].focused = False
            self._kid_idx = (self._kid_idx - 1) % n
            self._focusable_kids[self._kid_idx].focused = True
            return True

        return False

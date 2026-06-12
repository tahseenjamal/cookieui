from typing import Optional, List

from .core.terminal import Terminal
from .core.screen   import Screen
from .core.event    import Key, KeyType
from .theme         import Theme, DEFAULT
from .widgets.base  import Widget
from .widgets.dialog import Dialog
from .widgets.window import Window


class View:
    """A view owns a flat list of widgets and manages Tab-based focus."""

    def __init__(self):
        self._all:      List[Widget] = []
        self._focusable: List[Widget] = []
        self._idx = 0

    def add(self, *widgets: Widget) -> 'View':
        for w in widgets:
            self._all.append(w)
            if isinstance(w, Window):
                w.set_view(self)        # auto-link — no manual win.set_view(view) needed
            if getattr(w, 'focusable', True):
                self._focusable.append(w)
        return self

    def focus_first(self):
        for w in self._focusable:
            w.focused = False
        if self._focusable:
            self._idx = 0
            self._focusable[0].focused = True

    def focus_widget(self, widget: Widget):
        """Focus a specific widget if it's in the Tab list."""
        if widget in self._focusable:
            self._cycle_to(self._focusable.index(widget))

    @property
    def focused_widget(self) -> Optional[Widget]:
        if not self._focusable:
            return None
        return self._focusable[self._idx % len(self._focusable)]

    def draw(self, screen, theme):
        for w in self._all:
            if w.visible:
                w.draw(screen, theme)

    def handle_key(self, key: Key) -> bool:
        fw = self.focused_widget

        # Sync focus: if a window changed internal focus (via arrow keys),
        # update our tracking to point to the actually focused widget.
        # This ensures SPACE/ENTER go to the visually highlighted widget, not a stale one.
        actual_focused = None
        for w in self._focusable:
            if w.focused:
                actual_focused = w
                break

        if actual_focused and actual_focused != fw:
            self._idx = self._focusable.index(actual_focused)
            fw = actual_focused

        if fw and fw.handle_key(key):
            return True

        if not self._focusable:
            return False

        # If the focused widget is inside a window, let the window
        # handle arrow keys for navigation between its children.
        from .widgets.window import Window as Win
        for w in self._all:
            if isinstance(w, Win) and fw in w._focusable_kids:
                if w.handle_key(key):
                    return True
                break

        # Tab / Shift-Tab cycle through the global flat list of all focusable widgets.
        if key.type == KeyType.TAB:
            return self._cycle(+1)
        if key.type == KeyType.SHIFT_TAB:
            return self._cycle(-1)

        # Form flow: Enter in a TextInput with no on_enter moves focus to the next
        # widget (same order as Tab) — so chaining fields needs no key wiring at all.
        if key.type == KeyType.ENTER:
            from .widgets.textinput import TextInput
            if isinstance(fw, TextInput) and fw.on_enter is None:
                return self._cycle(+1)

        return False

    def _cycle(self, direction: int) -> bool:
        self._cycle_to((self._idx + direction) % max(1, len(self._focusable)))
        return True

    def _cycle_to(self, idx: int):
        fw = self.focused_widget
        if fw:
            fw.focused = False
        self._idx = idx
        nfw = self.focused_widget
        if nfw:
            nfw.focused = True


class App:
    """Top-level application: owns the terminal, screen, and view stack."""

    def __init__(self, theme: Theme = None):
        self.theme      = theme or DEFAULT
        self._terminal  = Terminal()
        self._screen    = Screen(self._terminal.width, self._terminal.height)
        self._views:    List[View]     = []
        self._dialog:   Optional[Dialog] = None
        self._running   = False
        self._pending_size = None   # set from the SIGWINCH handler, applied between frames
        self.on_resize: Optional[callable] = None   # fn(w, h) — called after the screen resizes

    # ── View stack ────────────────────────────────────────────────────────

    def push_view(self, view: View):
        self._views.append(view)
        view.focus_first()

    def pop_view(self):
        if len(self._views) > 1:
            self._views.pop()

    def replace_view(self, view: View):
        if self._views:
            self._views[-1] = view
        else:
            self._views.append(view)
        view.focus_first()

    @property
    def current_view(self) -> Optional[View]:
        return self._views[-1] if self._views else None

    # ── Dialog overlay ────────────────────────────────────────────────────

    def show_dialog(self, dialog: Dialog):
        # Any button (or Escape) closes the dialog automatically, then runs the
        # caller's on_close — so callbacks never have to call close_dialog themselves.
        user_cb = dialog._on_close

        def _auto_close(label: str):
            self.close_dialog()
            if user_cb:
                user_cb(label)

        dialog._on_close = _auto_close
        self._dialog = dialog

    def close_dialog(self):
        self._dialog = None

    # ── Run loop ──────────────────────────────────────────────────────────

    def run(self):
        self._terminal.setup(on_resize=self._on_resize)
        self._running = True
        try:
            while self._running:
                self._apply_resize()
                self._draw()
                key = self._terminal.read_key(timeout=0.05)
                if key is not None:
                    self._dispatch(key)
        except KeyboardInterrupt:
            pass
        finally:
            self._terminal.teardown()

    def quit(self):
        self._running = False

    # ── Internals ─────────────────────────────────────────────────────────

    def _on_resize(self, w: int, h: int):
        # Runs in signal-handler context — record only; the run loop applies it
        # between frames so the screen is never reallocated mid-render.
        self._pending_size = (w, h)

    def _apply_resize(self):
        if self._pending_size is None:
            return
        w, h = self._pending_size
        self._pending_size = None
        self._screen.resize(w, h)
        if self.on_resize:
            self.on_resize(w, h)

    def _draw(self):
        self._screen.clear(bg=self.theme.bg)
        if self.current_view:
            self.current_view.draw(self._screen, self.theme)
        if self._dialog:
            self._dialog.draw(self._screen, self.theme)
        self._screen.render()

    def _dispatch(self, key: Key):
        if self._dialog:
            self._dialog.handle_key(key)
        elif self.current_view:
            self.current_view.handle_key(key)

from typing import Callable, List, Optional

from .base import Widget
from ..core.event import Key, KeyType


class RadioGroup(Widget):
    """Newt-style vertical radio button group.

    A single focusable widget that owns a column of mutually-exclusive
    options. Up/Down move the selection; Home/End jump to the ends.

    Each option renders as:
        (*) label   — selected
        ( ) label   — not selected

    The group paints its own ``theme.surface`` background, so it always
    reads as a panel sitting on a window — never transparent to the root
    background. The active row is highlighted with the theme's
    list-selection colours when focused, consistent with Listbox.
    """
    focusable = True

    def __init__(self, x: int, y: int, width: int,
                 options: Optional[List[str]] = None,
                 selected: int = 0,
                 on_change: Optional[Callable[[int], None]] = None):
        opts = list(options or [])
        super().__init__(x, y, width, max(1, len(opts)))
        self._on_change = on_change
        self._sel       = selected
        self._labels    = []
        self._values    = []
        self.options    = opts    # property setter splits (label, value) + sets height

    # ── State ───────────────────────────────────────────────────────────────

    @property
    def on_change(self):
        return self._on_change

    @on_change.setter
    def on_change(self, fn):
        """Assignable after construction, like Button.on_click."""
        self._on_change = fn

    @property
    def options(self) -> List[str]:
        return self._labels

    @options.setter
    def options(self, value) -> None:
        """Set the choices. Each entry is a label string, or a (label, value) pair —
        the label is shown, the value is recoverable via `selected_value`."""
        labels, values = [], []
        for entry in value:
            label, val = entry if isinstance(entry, tuple) else (entry, entry)
            labels.append(label)
            values.append(val)
        self._labels = labels
        self._values = values
        self.height  = max(1, len(labels))
        self._sel    = max(0, min(self._sel, len(labels) - 1)) if labels else 0

    @property
    def selected_index(self) -> int:
        return self._sel

    @property
    def selected(self) -> Optional[str]:
        return self._labels[self._sel] if self._labels else None

    @property
    def selected_value(self):
        """The value paired with the selected option (the value from a (label, value)
        entry, or the label itself for plain-string options). None when empty."""
        return self._values[self._sel] if self._values else None

    def set_selected(self, idx: int) -> None:
        if self._labels:
            self._select(max(0, min(len(self._labels) - 1, idx)))

    # ── Drawing ─────────────────────────────────────────────────────────────

    def draw(self, screen, theme) -> None:
        t  = theme
        bg = t.surface
        screen.fill(self.x, self.y, self.width, self.height, bg=bg)

        for i, opt in enumerate(self.options):
            row    = self.y + i
            is_sel = (i == self._sel)
            mark   = f'{t.rg_l}{t.rg_mark if is_sel else " "}{t.rg_r}'
            text   = f'{mark} {opt}'[:self.width].ljust(self.width)

            if is_sel and self.focused:
                screen.write(self.x, row, text,
                             fg=t.list_sel_fg, bg=t.list_sel_bg)
            elif is_sel:
                screen.write(self.x, row, text, fg=t.accent, bg=bg, bold=True)
            else:
                screen.write(self.x, row, text, fg=t.text, bg=bg)

    # ── Keys ────────────────────────────────────────────────────────────────

    def handle_key(self, key: Key) -> bool:
        n = len(self.options)
        if n == 0:
            return False

        kt = key.type
        if kt == KeyType.UP:
            self._select((self._sel - 1) % n); return True
        if kt == KeyType.DOWN:
            self._select((self._sel + 1) % n); return True
        if kt == KeyType.HOME:
            self._select(0);     return True
        if kt == KeyType.END:
            self._select(n - 1); return True
        return False

    def _select(self, idx: int) -> None:
        if idx != self._sel:
            self._sel = idx
            if self._on_change:
                self._on_change(idx)

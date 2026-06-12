from typing import List, Optional, Callable

from .base import Widget
from ..core.event import Key, KeyType


class Listbox(Widget):
    """Newt-style scrollable listbox with ▲░█▼ scrollbar."""
    focusable = True

    def __init__(self, x: int, y: int, width: int, height: int,
                 items: Optional[List[str]] = None,
                 title: str = '',
                 on_select: Optional[Callable[[int, str], None]] = None,
                 shadow: bool = True):
        super().__init__(x, y, width, height)
        self.title      = title
        self._on_select = on_select
        self.shadow     = shadow
        self._sel       = 0
        self._scroll    = 0
        self._values    = []
        self.items      = list(items or [])   # property setter clamps _sel/_scroll

    @property
    def items(self) -> List[str]:
        return self._items

    @items.setter
    def items(self, value) -> None:
        """Replace the rows. Each entry is a label string, or a (label, value) pair —
        the label is shown, the value is recoverable via `selected_value` (so callers
        don't need a parallel list to map a row back to a domain object). Re-clamps
        selection/scroll, so swapping in a shorter list never leaves the selection
        pointing out of range."""
        labels, values = [], []
        for entry in value:
            label, val = entry if isinstance(entry, tuple) else (entry, entry)
            labels.append(label)
            values.append(val)
        self._items  = labels
        self._values = values
        self._clamp()

    @property
    def selected(self) -> Optional[str]:
        return self._items[self._sel] if self._items else None

    @property
    def selected_value(self):
        """The value paired with the selected row (the value from a (label, value)
        entry, or the label itself for plain-string rows). None when empty."""
        return self._values[self._sel] if self._values else None

    @property
    def selected_index(self) -> int:
        return self._sel

    @selected_index.setter
    def selected_index(self, idx: int) -> None:
        """Move the selection programmatically; clamps to range and scrolls it into
        view. e.g. `lb.selected_index = 0` jumps to the top after replacing items."""
        self._sel = idx
        self._clamp()

    def _clamp(self) -> None:
        """Keep _sel in range and _scroll consistent (selection visible, in bounds)."""
        n  = len(self._items)
        ih = self._inner_h()
        self._sel = 0 if n == 0 else max(0, min(self._sel, n - 1))
        if self._sel < self._scroll:
            self._scroll = self._sel
        elif self._sel >= self._scroll + ih:
            self._scroll = self._sel - ih + 1
        self._scroll = max(0, min(self._scroll, max(0, n - ih)))

    def _inner_h(self) -> int:
        return self.height - 2

    def _inner_w(self) -> int:
        # Reserve 1 col for scrollbar when list overflows
        sb = 1 if len(self.items) > self._inner_h() else 0
        return self.width - 2 - sb

    def draw(self, screen, theme):
        t   = theme
        ih  = self._inner_h()
        iw  = self._inner_w()
        has_sb = len(self.items) > ih

        bg = t.chrome.frame(screen, theme, self.x, self.y, self.width, self.height,
                            focused=self.focused, title=self.title)

        # Items
        for i in range(ih):
            idx  = self._scroll + i
            ry   = self.y + 1 + i

            if idx >= len(self.items):
                screen.fill(self.x + 1, ry, iw, 1, bg=bg)
                continue

            item   = str(self.items[idx])
            is_sel = (idx == self._sel)

            if is_sel and self.focused:
                row_bg, row_fg = t.list_sel_bg, t.list_sel_fg
            elif is_sel:
                row_bg, row_fg = bg, t.accent
            else:
                row_bg, row_fg = bg, t.text

            line = item[:iw].ljust(iw)
            screen.write(self.x + 1, ry, line, fg=row_fg, bg=row_bg)

        # Scrollbar — Newt style: ▲ ░░█░░ ▼
        if has_sb:
            t.chrome.scrollbar(screen, theme, self.x + self.width - 2, self.y + 1,
                               ih, len(self.items), self._scroll, bg=bg)

        # Drop shadow — consistent with Window / Button
        if self.shadow:
            t.chrome.shadow(screen, theme, self.x, self.y, self.width, self.height)

    def handle_key(self, key: Key) -> bool:
        ih = self._inner_h()
        n  = len(self.items)
        if n == 0:
            return False

        kt = key.type
        if kt == KeyType.UP:           self._move(-1);  return True
        if kt == KeyType.DOWN:         self._move( 1);  return True
        if kt == KeyType.PAGE_UP:      self._move(-ih); return True
        if kt == KeyType.PAGE_DOWN:    self._move( ih); return True
        if kt == KeyType.HOME:
            self.selected_index = 0;     return True
        if kt == KeyType.END:
            self.selected_index = n - 1; return True
        if kt == KeyType.ENTER and self._on_select:
            self._on_select(self._sel, self._items[self._sel]); return True
        return False

    def _move(self, delta: int):
        self._sel += delta
        self._clamp()

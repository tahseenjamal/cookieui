from typing import Optional, Callable

from .base import Widget
from ..core.event import Key, KeyType


class Checkbox(Widget):
    """Newt-style checkbox: [ ] label

    Renders on a window *surface* (not the root background) so it sits
    cleanly inside a bordered container:
      • label + brackets use ``theme.text`` on ``theme.surface``
      • when checked, the ``*`` mark is drawn in ``theme.accent``
      • when focused, the mark cell is highlighted with the list-selection
        colours, mirroring Listbox / RadioGroup for a consistent feel
    """
    focusable = True

    def __init__(self, x: int, y: int, width: int, label: str,
                 checked: bool = False,
                 on_change: Optional[Callable[[bool], None]] = None):
        super().__init__(x, y, width, 1)
        self.label      = label
        self.checked    = checked
        self._on_change = on_change

    def draw(self, screen, theme):
        t    = theme
        bg   = t.surface
        mark = t.cb_mark if self.checked else ' '

        # Full row on the surface, inheriting window background via write_over
        row_text = f'{t.cb_l}{mark}{t.cb_r} {self.label}'[:self.width].ljust(self.width)
        screen.write_over(self.x, self.y, row_text,
                          fg=t.text, bold=self.focused)

        # Mark cell — highlighted when focused, accent when checked
        if self.focused:
            screen.put(self.x + 1, self.y, mark,
                       fg=t.list_sel_fg, bg=t.list_sel_bg)
        elif self.checked:
            # Get the current background (window surface)
            existing_bg = screen._cells[self.y][self.x + 1].bg if 0 <= self.x + 1 < screen.width else bg
            screen.put(self.x + 1, self.y, mark, fg=t.accent, bg=existing_bg, bold=True)

    def handle_key(self, key: Key) -> bool:
        if key.type == KeyType.ENTER or (key.type == KeyType.CHAR and key.char == ' '):
            self.checked = not self.checked
            if self._on_change:
                self._on_change(self.checked)
            return True
        return False

from typing import List

from .base import Widget
from ..core.event import Key, KeyType


class TextView(Widget):
    """Scrollable read-only multi-line text — bordered, with the Newt ▲░█▼ scrollbar.

    The workhorse for logs, file contents, help screens, and long command output.
    Set `.text` (a plain string, newlines included) and the widget wraps, clips, and
    scrolls it; setting it again from anywhere updates the next frame — same
    mutate-and-redraw model as every other widget.

        tv = TextView(x, y, w, h, text=open(p).read(), title=p.name)
        tv.text += f'\\n{line}'      # append (e.g. a log line)
        tv.scroll_to_end()           # follow output

    Keys (when focused): Up/Down scroll a line, PgUp/PgDn a page, Home/End jump.

    Args:
        text:   initial content. Tabs are expanded to 4 spaces.
        title:  centred on the top border, like Window/Listbox.
        wrap:   word-wrap long lines (default True); False clips them at the border.
        shadow: cast the standard drop shadow (default True).
    """
    focusable = True

    def __init__(self, x: int, y: int, width: int, height: int,
                 text: str = '', title: str = '',
                 wrap: bool = True, shadow: bool = True):
        super().__init__(x, y, width, height)
        self.title   = title
        self.wrap    = wrap
        self.shadow  = shadow
        self._scroll = 0
        self._raw    = ''
        self._lines: List[str] = ['']
        self.text    = text

    # ── Content ──────────────────────────────────────────────────────────

    @property
    def text(self) -> str:
        return self._raw

    @text.setter
    def text(self, value: str) -> None:
        """Replace the content; re-wraps and clamps the scroll position."""
        self._raw = str(value)
        self._reflow()

    def _inner_h(self) -> int:
        return self.height - 2

    def _reflow(self) -> None:
        raw_lines = self._raw.expandtabs(4).split('\n')
        # Wrap at the full interior first; if that overflows vertically, a scrollbar
        # column is needed, so re-wrap one column narrower.
        for sb in (0, 1):
            w = max(1, self.width - 2 - sb)
            lines: List[str] = []
            for line in raw_lines:
                lines.extend(self._wrap_line(line, w) if self.wrap else [line])
            if len(lines) <= self._inner_h() or sb == 1:
                break
        self._lines = lines or ['']
        self._clamp()

    @staticmethod
    def _wrap_line(line: str, width: int) -> List[str]:
        if len(line) <= width:
            return [line]
        out = []
        while len(line) > width:
            cut = line.rfind(' ', 1, width + 1)
            if cut <= 0:
                cut = width                      # no space — hard break
                out.append(line[:cut])
                line = line[cut:]
            else:
                out.append(line[:cut])
                line = line[cut + 1:]            # swallow the break space
        out.append(line)
        return out

    # ── Scrolling ────────────────────────────────────────────────────────

    def _clamp(self) -> None:
        self._scroll = max(0, min(self._scroll, len(self._lines) - self._inner_h()))

    def scroll_to_top(self) -> None:
        self._scroll = 0

    def scroll_to_end(self) -> None:
        """Jump to the last page — call after appending to follow output (logs)."""
        self._scroll = max(0, len(self._lines) - self._inner_h())

    # ── Widget interface ─────────────────────────────────────────────────

    def draw(self, screen, theme):
        t   = theme
        ih  = self._inner_h()
        has_sb = len(self._lines) > ih
        iw  = self.width - 2 - (1 if has_sb else 0)

        bg = t.chrome.frame(screen, theme, self.x, self.y, self.width, self.height,
                            focused=self.focused, title=self.title)

        # Text rows
        for i in range(ih):
            idx = self._scroll + i
            line = self._lines[idx] if idx < len(self._lines) else ''
            screen.write(self.x + 1, self.y + 1 + i, line[:iw].ljust(iw), fg=t.text, bg=bg)

        # Scrollbar — Newt style: ▲ ░░█░░ ▼ (same formula as Listbox)
        if has_sb:
            t.chrome.scrollbar(screen, theme, self.x + self.width - 2, self.y + 1,
                               ih, len(self._lines), self._scroll, bg=bg)

        if self.shadow:
            t.chrome.shadow(screen, theme, self.x, self.y, self.width, self.height)

    def handle_key(self, key: Key) -> bool:
        ih = self._inner_h()
        kt = key.type
        if kt == KeyType.UP:        self._scroll -= 1;  self._clamp(); return True
        if kt == KeyType.DOWN:      self._scroll += 1;  self._clamp(); return True
        if kt == KeyType.PAGE_UP:   self._scroll -= ih; self._clamp(); return True
        if kt == KeyType.PAGE_DOWN: self._scroll += ih; self._clamp(); return True
        if kt == KeyType.HOME:      self.scroll_to_top();  return True
        if kt == KeyType.END:       self.scroll_to_end();  return True
        return False

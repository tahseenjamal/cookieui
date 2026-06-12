import sys
from typing import Optional, Tuple

Color = Tuple[int, int, int]

_R = '\x1b[0m'


def _fg(r: int, g: int, b: int) -> str:
    return f'\x1b[38;2;{r};{g};{b}m'


def _bg(r: int, g: int, b: int) -> str:
    return f'\x1b[48;2;{r};{g};{b}m'


class _Cell:
    __slots__ = ('char', 'fg', 'bg', 'bold', 'italic', 'dim')

    def __init__(self):
        self.char: str               = ' '
        self.fg:   Optional[Color]   = None
        self.bg:   Optional[Color]   = None
        self.bold:   bool            = False
        self.italic: bool            = False
        self.dim:    bool            = False

    def attrs(self):
        return (self.char, self.fg, self.bg, self.bold, self.italic, self.dim)

    def copy_from(self, other: '_Cell'):
        self.char   = other.char
        self.fg     = other.fg
        self.bg     = other.bg
        self.bold   = other.bold
        self.italic = other.italic
        self.dim    = other.dim


class Screen:
    def __init__(self, width: int, height: int):
        self.width  = width
        self.height = height
        self._cells = self._alloc()
        self._prev  = None      # the last *rendered* frame; None forces a full repaint

    def _alloc(self):
        return [[_Cell() for _ in range(self.width)] for _ in range(self.height)]

    def resize(self, width: int, height: int):
        self.width  = width
        self.height = height
        self._cells = self._alloc()
        self._prev  = None      # dimensions changed — diffing against the old frame
                                # would be meaningless; repaint everything once

    # ── Primitives ────────────────────────────────────────────────────────

    def put(self, x: int, y: int, char: str,
            fg: Color = None, bg: Color = None,
            bold: bool = False, italic: bool = False, dim: bool = False):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        c = self._cells[y][x]
        c.char   = char[0] if char else ' '
        c.fg     = fg
        c.bg     = bg
        c.bold   = bold
        c.italic = italic
        c.dim    = dim

    def write(self, x: int, y: int, text: str,
              fg: Color = None, bg: Color = None,
              bold: bool = False, italic: bool = False, dim: bool = False):
        for i, ch in enumerate(text):
            self.put(x + i, y, ch, fg=fg, bg=bg, bold=bold, italic=italic, dim=dim)

    def fill(self, x: int, y: int, w: int, h: int,
             bg: Color = None, char: str = ' ', fg: Color = None):
        for row in range(max(0, y), min(y + h, self.height)):
            for col in range(max(0, x), min(x + w, self.width)):
                self.put(col, row, char, fg=fg, bg=bg)

    def clear(self, bg: Color = None):
        self.fill(0, 0, self.width, self.height, bg=bg)

    def bg_at(self, x: int, y: int):
        """The background color currently at a cell (None if unset/out of bounds).
        Lets widgets blend overlays against whatever they're drawn on."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._cells[y][x].bg
        return None

    def write_over(self, x: int, y: int, text: str,
                   fg: Color = None,
                   bold: bool = False, italic: bool = False, dim: bool = False):
        """Write text while inheriting each cell's existing background color.

        Use this for labels drawn inside windows so the window surface color
        shows through instead of being overwritten with the outer bg.
        """
        for i, ch in enumerate(text):
            xi = x + i
            if 0 <= xi < self.width and 0 <= y < self.height:
                existing_bg = self._cells[y][xi].bg
                self.put(xi, y, ch, fg=fg, bg=existing_bg,
                         bold=bold, italic=italic, dim=dim)

    def cast_shadow(self, win_x: int, win_y: int, win_w: int, win_h: int,
                    color: Color = (1, 57, 75),
                    max_x: int = None, max_y: int = None):
        """Apply a Newt-style drop shadow to a widget/window.

        Matches newtOpenWindow exactly:
          • 1-column shadow on the right  (col win_x+win_w, rows win_y+1 .. win_y+win_h-1)
          • 1-row    shadow on the bottom (row win_y+win_h,  cols win_x+1 .. win_x+win_w)

        Optional max_x, max_y clip the shadow to stay within bounds (used for widgets
        inside windows so their shadows don't escape the window border).
        """
        if max_x is None:
            max_x = self.width
        if max_y is None:
            max_y = self.height

        sr, sg, sb = color

        def _tint(c):
            # Darken background significantly: blend 70% toward the shadow color
            if c.bg:
                r, g, b = c.bg
                c.bg = (int(r * 0.3 + sr * 0.7), int(g * 0.3 + sg * 0.7), int(b * 0.3 + sb * 0.7))
            else:
                c.bg = color

            # Darken foreground very significantly - text in shadow should be very dark
            if c.fg:
                r, g, b = c.fg
                # Convert to greyscale and darken much more
                grey = int(0.299 * r + 0.587 * g + 0.114 * b)
                # Make text much darker by reducing brightness to 15%
                darkened = int(grey * 0.15)
                c.fg = (max(0, darkened), max(0, darkened), max(0, darkened))

        # Right shadow — 1 column (clipped to max_x)
        col = win_x + win_w
        if col < max_x and 0 <= col < self.width:
            for row in range(win_y + 1, min(win_y + win_h, max_y, self.height)):
                _tint(self._cells[row][col])

        # Bottom shadow — 1 row (clipped to max_y)
        row = win_y + win_h
        if row < max_y and 0 <= row < self.height:
            for col in range(win_x + 1, min(win_x + win_w + 1, max_x, self.width)):
                _tint(self._cells[row][col])

    def darken(self, x: int, y: int, w: int, h: int, factor: float = 0.35):
        """Darken a region of cells — used for dialog overlay effect."""
        for row in range(max(0, y), min(y + h, self.height)):
            for col in range(max(0, x), min(x + w, self.width)):
                c = self._cells[row][col]
                if c.bg:
                    r, g, b = c.bg
                    c.bg = (int(r * factor), int(g * factor), int(b * factor))
                else:
                    c.bg = (0, 0, 0)
                if c.fg:
                    r, g, b = c.fg
                    c.fg = (int(r * factor), int(g * factor), int(b * factor))

    # ── Rendering ─────────────────────────────────────────────────────────

    # When bridging changed spans, re-emitting up to this many *unchanged* cells
    # is cheaper than the ~9-byte cursor jump a new span would cost.
    _GAP_BRIDGE = 4

    def render(self):
        """Flush the composed frame to the terminal — differentially.

        The previously rendered frame is kept, and only cells that changed since
        then are emitted (as per-row spans with cursor jumps). An unchanged frame
        writes zero bytes. The first frame after construction or resize() is a
        full repaint. The visible result is pixel-identical to a full repaint —
        proven by the emulator equivalence tests in tests/test_screen.py.

        Buffers are swapped, not copied: the just-rendered grid becomes the
        reference and the old reference is recycled as the next compose target
        (the run loop's clear() rewrites every cell before widgets draw).
        """
        cells = self._cells
        prev  = self._prev
        full  = (prev is None or len(prev) != self.height
                 or (self.height > 0 and len(prev[0]) != self.width))

        out  = []
        last = None   # SGR state currently on the wire (cursor jumps don't reset it)

        def emit(row, y, xs, xe):
            nonlocal last
            out.append(f'\x1b[{y + 1};{xs + 1}H')
            for x in range(xs, xe):
                cell  = row[x]
                attrs = (cell.fg, cell.bg, cell.bold, cell.italic, cell.dim)
                if attrs != last:
                    parts = [_R]
                    if cell.bold:   parts.append('\x1b[1m')
                    if cell.italic: parts.append('\x1b[3m')
                    if cell.dim:    parts.append('\x1b[2m')
                    if cell.fg:     parts.append(_fg(*cell.fg))
                    if cell.bg:     parts.append(_bg(*cell.bg))
                    out.append(''.join(parts))
                    last = attrs
                out.append(cell.char)

        if full:
            for y in range(self.height):
                emit(cells[y], y, 0, self.width)
        else:
            W      = self.width
            bridge = self._GAP_BRIDGE

            def same(a, b):
                return (a.char == b.char and a.fg == b.fg and a.bg == b.bg
                        and a.bold == b.bold and a.italic == b.italic
                        and a.dim == b.dim)

            for y in range(self.height):
                row, prow = cells[y], prev[y]
                x = 0
                while x < W:
                    if same(row[x], prow[x]):
                        x += 1
                        continue
                    start, end = x, x + 1        # end: one past the last changed cell
                    x += 1
                    gap = 0
                    while x < W:
                        if same(row[x], prow[x]):
                            gap += 1
                            if gap > bridge:
                                break
                        else:
                            end = x + 1
                            gap = 0
                        x += 1
                    emit(row, y, start, end)

        if out:
            out.append(_R)
            sys.stdout.write(''.join(out))
            sys.stdout.flush()

        self._prev  = cells
        self._cells = prev if not full else self._alloc()

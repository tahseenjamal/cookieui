"""The diff renderer is pixel-identical to a full repaint — proven, not assumed.

A tiny ANSI emulator applies exactly the escape subset Screen.render() emits
(cursor jumps + SGR) to a virtual grid. Every test composes real frames through
real apps, renders them (first full, then differential), feeds the bytes to the
emulator, and compares the emulator's grid cell-for-cell — char, fg, bg, bold,
italic, dim — against the composed frame. An unchanged frame must emit nothing.
"""
import io
import re
from contextlib import redirect_stdout

from conftest import make, paint, press, W, H
from cookieui import TuiApp
from cookieui.core.event import KeyType
from cookieui.core.screen import Screen


# ── The emulator: applies render()'s escape subset to a virtual terminal ──────

ESC = re.compile(r'\x1b\[([0-9;]*)([Hm])')


class Emu:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.grid = [[(' ', None, None, False, False, False) for _ in range(w)]
                     for _ in range(h)]
        self.x = self.y = 0
        self.fg = self.bg = None
        self.bold = self.italic = self.dim = False

    def feed(self, s):
        i = 0
        while i < len(s):
            if s[i] == '\x1b':
                m = ESC.match(s, i)
                assert m, f'render() emitted an escape the emulator does not model: {s[i:i+24]!r}'
                if m.group(2) == 'H':
                    row, col = m.group(1).split(';')
                    self.y, self.x = int(row) - 1, int(col) - 1
                else:
                    self._sgr(m.group(1))
                i = m.end()
            else:
                assert 0 <= self.x < self.w and 0 <= self.y < self.h, \
                    f'render() wrote outside the screen at ({self.x},{self.y})'
                self.grid[self.y][self.x] = (s[i], self.fg, self.bg,
                                             self.bold, self.italic, self.dim)
                self.x += 1
                i += 1

    def _sgr(self, params):
        nums = [int(p) for p in params.split(';') if p] or [0]
        j = 0
        while j < len(nums):
            n = nums[j]
            if n == 0:
                self.fg = self.bg = None
                self.bold = self.italic = self.dim = False
            elif n == 1:
                self.bold = True
            elif n == 2:
                self.dim = True
            elif n == 3:
                self.italic = True
            elif n == 38 and nums[j + 1] == 2:
                self.fg = tuple(nums[j + 2:j + 5]); j += 4
            elif n == 48 and nums[j + 1] == 2:
                self.bg = tuple(nums[j + 2:j + 5]); j += 4
            else:
                raise AssertionError(f'unhandled SGR code {n}')
            j += 1


def snapshot(screen):
    """The composed frame as comparable tuples — taken BEFORE render() (which swaps
    the buffers)."""
    return [[(c.char, c.fg, c.bg, c.bold, c.italic, c.dim) for c in row]
            for row in screen._cells]


def flush(screen) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        screen.render()
    return buf.getvalue()


def assert_grids_equal(emu, snap):
    for y, (erow, srow) in enumerate(zip(emu.grid, snap)):
        for x, (e, s) in enumerate(zip(erow, srow)):
            assert e == s, f'cell ({x},{y}) diverged: terminal={e} composed={s}'


# ── A real app to compose real frames ─────────────────────────────────────────

class DemoApp(TuiApp):
    def build_view(self):
        page = self.page(0.6, 0.8, title='Diff')
        self.inp = page.input(label='Name')
        self.bar = page.progressbar()
        self.lbl = page.label('status')
        self.lb  = page.listbox(rows=5)
        self.lb.items = [f'row {i}' for i in range(20)]
        page.footer([('OK', lambda: None), ('Quit', self.quit)])
        return page


def frame(app):
    """Compose, snapshot, render — returns (snapshot, emitted_bytes)."""
    screen = paint(app)
    snap = snapshot(screen)
    return snap, flush(screen)


# ── The proofs ────────────────────────────────────────────────────────────────

def test_first_frame_is_a_full_repaint_and_exact():
    app = make(DemoApp)
    snap, out = frame(app)
    assert out.count('\x1b[') >= H              # at least one cursor jump per row
    emu = Emu(W, H)
    emu.feed(out)
    assert_grids_equal(emu, snap)


def test_unchanged_frame_emits_zero_bytes():
    app = make(DemoApp)
    frame(app)                                  # full paint
    _, out = frame(app)                         # recomposed, nothing changed
    assert out == ''


def test_diff_stream_stays_pixel_identical_through_real_interaction():
    app = make(DemoApp)
    emu = Emu(W, H)
    snap, out = frame(app)
    emu.feed(out)
    assert_grids_equal(emu, snap)

    # A storm of real state changes — every diff must keep the terminal exact.
    steps = [
        lambda: press(app, 'hello'),                            # typing
        lambda: setattr(app.bar, 'value', 0.37),                # bar fill
        lambda: setattr(app.lbl, 'text', 'updated ✓'),          # label text
        lambda: press(app, KeyType.TAB, KeyType.TAB, KeyType.TAB),   # focus moves
        lambda: press(app, KeyType.DOWN, KeyType.DOWN),         # list scroll
        lambda: setattr(app.bar, 'text', 'Done ✓'),             # bar-face text
        lambda: app.show_message('Hi', 'A dialog darkens everything behind it.'),
        lambda: app.close_dialog(),                             # and restores it
        lambda: setattr(app.lbl, 'text', ''),                   # text shrinks
    ]
    for step in steps:
        step()
        snap, out = frame(app)
        emu.feed(out)
        assert_grids_equal(emu, snap)


def test_diff_emits_far_fewer_bytes_than_full():
    app = make(DemoApp)
    _, full_out = frame(app)
    app.bar.value = 0.5                          # one widget changed
    _, diff_out = frame(app)
    assert 0 < len(diff_out) < len(full_out) / 10


def test_resize_forces_one_full_repaint():
    app = make(DemoApp)
    frame(app)
    from conftest import at_size
    at_size(app, w=80, h=24)
    snap, out = frame(app)
    assert out.count('\x1b[') >= 24              # full repaint at the new size
    emu = Emu(80, 24)
    emu.feed(out)
    assert_grids_equal(emu, snap)
    _, out2 = frame(app)                         # and diffing resumes
    assert out2 == ''


def test_render_standalone_screen_roundtrip():
    # Property-style: random-ish direct Screen mutations, no app machinery.
    s = Screen(40, 12)
    emu = Emu(40, 12)
    s.clear(bg=(10, 20, 30))
    s.write(2, 3, 'hello', fg=(200, 0, 0), bold=True)
    emu.feed(flush(s))

    s.clear(bg=(10, 20, 30))
    s.write(2, 3, 'hellp', fg=(200, 0, 0), bold=True)    # 1-char change
    s.write(30, 11, 'edge', fg=(0, 200, 0), italic=True) # bottom-right corner
    s.fill(0, 0, 40, 1, bg=(0, 0, 0))                    # whole top row
    snap = snapshot(s)
    emu.feed(flush(s))
    assert_grids_equal(emu, snap)


def test_zero_terminal_size_is_ignored():
    # A pty reporting 0x0 must not produce a zero-cell (invisible) app.
    from cookieui.core.terminal import Terminal
    import os
    t = Terminal.__new__(Terminal)
    t._fd = -1                       # headless: keep defaults
    t.width, t.height = 80, 24
    t._update_size()
    assert (t.width, t.height) == (80, 24)

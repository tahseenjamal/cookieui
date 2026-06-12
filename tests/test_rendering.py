"""Screen-cell inspection: what actually lands on the grid when a frame is composed."""
from conftest import make, paint, press, row_text, screen_text, W, H
from cookieui import TuiApp
from cookieui.core.event import KeyType
from cookieui.theme import DEFAULT


class BarApp(TuiApp):
    def build_view(self):
        page = self.page(0.5, title='Render')
        self.bar = page.progressbar()
        page.buttons([('Quit', self.quit)])
        return page


def bar_row(app):
    screen = paint(app)
    return screen, app.bar.y, row_text(screen, app.bar.y)


# ── ProgressBar: the bar face is the status area ──────────────────────────────

def test_percent_renders_centered_while_progressing():
    app = make(BarApp)
    app.bar.value = 0.42
    _, _, row = bar_row(app)
    assert ' 42% ' in row
    assert row[app.bar.x] == '[' and row[app.bar.x + app.bar.width - 1] == ']'
    # centered, not left-aligned: text starts past the first quarter of the track
    assert row.index(' 42% ') > app.bar.x + app.bar.width // 4


def test_text_replaces_percent():
    app = make(BarApp)
    app.bar.value = 0.42
    app.bar.text = 'Complete ✓'
    _, _, row = bar_row(app)
    assert 'Complete ✓' in row and '42%' not in row


def test_label_over_fill_is_carved_into_the_bar_color():
    app = make(BarApp)
    app.bar.value = 1.0                      # label sits entirely on the fill
    app.bar.text = 'Done'
    screen, y, row = bar_row(app)
    cx = row.index('Done')
    cell = screen._cells[y][cx]
    assert cell.bg == DEFAULT.accent         # bar color behind the text
    assert cell.fg == DEFAULT.surface        # surface-colored text — the carved look


def test_label_over_track_blends_not_punches():
    app = make(BarApp)
    app.bar.value = 0.0                      # label sits entirely on the empty track
    app.bar.text = 'Starting'
    screen, y, row = bar_row(app)
    cx = row.index('Starting')
    cell = screen._cells[y][cx]
    # blended 25% accent over the window surface — neither pure surface nor pure accent
    assert cell.bg != DEFAULT.surface and cell.bg != DEFAULT.accent
    expected = tuple(int(a * 0.25 + s * 0.75)
                     for a, s in zip(DEFAULT.accent, DEFAULT.surface))
    assert cell.bg == expected


def test_value_clamped_at_draw_time():
    app = make(BarApp)
    app.bar.value = 7.3                      # overshoot must be harmless
    _, _, row = bar_row(app)
    assert '100%' in row
    app.bar.value = -2
    _, _, row = bar_row(app)
    assert ' 0% ' in row


# ── Label: max_width clips at draw time, the border survives live updates ─────

def test_long_label_cannot_overflow_the_border():
    class LabelApp(TuiApp):
        def build_view(self):
            page = self.page(30, title='Clip')          # exactly 30 cells wide
            self.lbl = page.label('short')
            self.win = page.win
            page.buttons([('Quit', self.quit)])
            return page
    app = make(LabelApp)
    app.lbl.text = 'X' * 200                            # live update, way too long
    screen = paint(app)
    y = app.lbl.y
    right = app.win.x + app.win.width - 1
    assert screen._cells[y][right].char == DEFAULT.v    # right border intact
    assert screen._cells[y][right + 1].char != 'X'      # nothing leaked past it


# ── Status bar: a real 3-row window flush with the bottom ─────────────────────

def test_auto_status_bar_geometry_and_text():
    app = make(BarApp)
    screen = paint(app)
    assert DEFAULT.h in row_text(screen, H - 3)         # top border row
    row = row_text(screen, H - 2)
    assert 'Tab cycle focus' in row                     # text INSIDE the frame
    assert DEFAULT.h in row_text(screen, H - 1)         # bottom border row
    # and the hint is centered in the bar (matching button rows and dialogs)
    text = row.strip(DEFAULT.v + ' ')
    left  = row.index(text)
    right = W - (left + len(text))
    assert abs(left - right) <= 2


# ── TextView: wrap, clip, follow ──────────────────────────────────────────────

class TvApp(TuiApp):
    def build_view(self):
        page = self.page(0.5, 0.8, title='TV')
        self.tv = page.textview(text='', title='log')
        page.footer([('Quit', self.quit)])
        return page


def test_textview_wraps_long_lines():
    app = make(TvApp)
    app.tv.text = 'alpha beta gamma delta ' * 20
    screen = paint(app)
    text = screen_text(screen)
    assert 'alpha beta' in text                         # words intact: wrapped, not chopped
    y = app.tv.y + 1
    right = app.tv.x + app.tv.width - 1
    assert screen._cells[y][right].char in (DEFAULT.v, DEFAULT.sc_up)   # frame intact


def test_textview_scroll_to_end_shows_last_line():
    app = make(TvApp)
    app.tv.text = '\n'.join(f'line {i}' for i in range(100))
    app.tv.scroll_to_end()
    text = screen_text(paint(app))
    assert 'line 99' in text and 'line 0\n' not in text


# ── Listbox: the selected row is highlighted, exactly one ─────────────────────

def test_listbox_selection_highlight_moves():
    class LbApp(TuiApp):
        def build_view(self):
            page = self.page(0.5, 0.8, title='LB')
            self.lb = page.listbox()
            self.lb.items = [f'item {i}' for i in range(5)]
            page.footer([('Quit', self.quit)])
            return page
    app = make(LbApp)
    press(app, KeyType.DOWN)
    screen = paint(app)
    lb = app.lb
    # scan only the listbox interior (Newt red is also the button bg elsewhere)
    sel_rows = [y for y in range(lb.y + 1, lb.y + lb.height - 1)
                if any(screen._cells[y][x].bg == DEFAULT.list_sel_bg
                       for x in range(lb.x + 1, lb.x + lb.width - 1))]
    assert len(sel_rows) == 1
    assert 'item 1' in row_text(screen, sel_rows[0])

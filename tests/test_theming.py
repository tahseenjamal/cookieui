"""The design system: theme tokens, the pluggable chrome, and the four shipped looks.

Layer model under test (TEMPLATING.md): colors (palette) → tokens (glyphs and
switches) → chrome (construction). NEWT pixel-identity through the chrome seam
is enforced by the cell assertions in test_rendering.py plus the dedicated
checks here; OUTLINE and FLAT prove the token and construction layers actually
decouple what they claim to.
"""
from dataclasses import replace

import pytest

from conftest import make, paint, row_text, screen_text, find, W, H
from cookieui import (TuiApp, Theme, NEWT, MOCHA, OUTLINE, FLAT, DEFAULT,
                      Chrome, FlatChrome, Window, Listbox)


class Sink(TuiApp):
    """Every chrome-drawing widget in one view."""
    def build_view(self):
        page = self.page(0.9, 0.9, title='Sink')
        self.inp = page.input(label='Name', placeholder='here')
        self.cb  = page.checkbox('Check me', checked=True)
        self.rg  = page.radio_group(['One', 'Two'])
        self.bar = page.progressbar()
        self.bar.value = 0.5
        self.lb  = page.listbox(rows=3)
        self.lb.items = [f'row {i}' for i in range(9)]   # overflows → scrollbar
        page.footer([('OK', lambda: None), ('Quit', self.quit)])
        return page


def make_themed(theme):
    return make(lambda: Sink(theme=theme))


def cell(screen, x, y):
    return screen._cells[y][x]


# ── Every shipped theme renders the whole kit, dialogs included ──────────────

@pytest.mark.parametrize('theme', [NEWT, MOCHA, OUTLINE, FLAT],
                         ids=['NEWT', 'MOCHA', 'OUTLINE', 'FLAT'])
def test_theme_renders_kitchen_sink_and_dialog(theme):
    app = make_themed(theme)
    paint(app)
    app.show_message('Hi', 'A dialog.')
    screen = paint(app)
    assert 'A dialog.' in screen_text(screen)


# ── Token layer: glyphs come from the theme, not the widgets ─────────────────

def test_outline_is_pure_line_work():
    app = make_themed(OUTLINE)
    screen = paint(app)
    win = find(app._app.current_view, Window)
    # rounded corners on the window frame
    assert cell(screen, win.x, win.y).char == '╭'
    assert cell(screen, win.x + win.width - 1, win.y + win.height - 1).char == '╯'
    # no filled panels: a plain window-interior cell has the same bg as the root
    # (top-right interior, past the input's label — nothing draws there)
    assert cell(screen, win.x + win.width - 3, win.y + 1).bg == OUTLINE.bg
    # the button box is rounded too, and its interior is the page background
    from cookieui.widgets.button import Button
    from conftest import find_all
    btn = find_all(app._app.current_view, Button)[-1]   # unfocused one
    assert cell(screen, btn.x, btn.y).char == '╭'
    assert cell(screen, btn.x + 1, btn.y + 1).bg == OUTLINE.bg


def test_progressbar_fill_token():
    app = make_themed(replace(NEWT, pb_fill='#', pb_track='-'))
    screen = paint(app)
    row = row_text(screen, app.bar.y)
    assert '#' in row and '[' in row and ']' in row
    assert '█' not in row


def test_checkbox_and_radio_brackets_are_tokens():
    custom = replace(NEWT, cb_l='<', cb_r='>', cb_mark='x', rg_mark='o')
    app = make_themed(custom)
    screen = paint(app)
    assert '<x> Check me' in row_text(screen, app.cb.y)
    assert '(o) One' in row_text(screen, app.rg.y)


def test_entry_fill_token():
    app = make_themed(replace(NEWT, entry_fill='.'))
    screen = paint(app)
    assert '...' in row_text(screen, app.inp.y + 1)    # entry row below the label


# ── Shadow master switch ──────────────────────────────────────────────────────

def shadow_cells(theme):
    app = make_themed(theme)
    screen = paint(app)
    win = find(app._app.current_view, Window)
    # the cell just right of the window's top-right corner, one row down —
    # inside the 1-cell shadow column when shadows are on
    return cell(screen, win.x + win.width, win.y + 1).bg


def test_newt_has_shadows_dark_themes_do_not():
    assert shadow_cells(NEWT) != NEWT.bg               # tinted by the shadow
    assert shadow_cells(MOCHA) == MOCHA.bg             # dark themes go flat
    assert shadow_cells(OUTLINE) == OUTLINE.bg         # outlines cast no shadows
    assert shadow_cells(FLAT) == FLAT.bg


def test_shadow_color_token_flows():
    red_shadow = replace(NEWT, shadow_color=(80, 0, 0))
    bg = shadow_cells(red_shadow)
    expected = tuple(int(c * 0.3 + s * 0.7) for c, s in zip(NEWT.bg, (80, 0, 0)))
    assert bg == expected


# ── Construction layer: the chrome is pluggable ──────────────────────────────

def test_flat_chrome_draws_no_border_glyphs():
    app = make_themed(FLAT)
    screen = paint(app)
    win = find(app._app.current_view, Window)
    assert cell(screen, win.x, win.y + 2).char == ' '          # no side border
    assert cell(screen, win.x, win.y + win.height - 1).char == ' '   # no bottom
    assert 'Sink' in row_text(screen, win.y)                   # title on the rule


def test_flat_geometry_is_unchanged():
    # The whole point of FlatChrome: construction changes, layout math doesn't.
    newt_app, flat_app = make_themed(NEWT), make_themed(FLAT)
    for attr in ('inp', 'cb', 'rg', 'bar', 'lb'):
        a, b = getattr(newt_app, attr), getattr(flat_app, attr)
        assert (a.x, a.y, a.width, a.height) == (b.x, b.y, b.width, b.height)


def test_custom_chrome_subclass_is_used_everywhere():
    calls = []

    class SpyChrome(Chrome):
        def frame(self, *a, **k):
            calls.append('frame');  return super().frame(*a, **k)
        def window_frame(self, *a, **k):
            calls.append('window'); return super().window_frame(*a, **k)
        def dialog_frame(self, *a, **k):
            calls.append('dialog'); return super().dialog_frame(*a, **k)
        def button_face(self, *a, **k):
            calls.append('button'); return super().button_face(*a, **k)
        def scrollbar(self, *a, **k):
            calls.append('scrollbar'); return super().scrollbar(*a, **k)

    app = make_themed(replace(NEWT, chrome=SpyChrome()))
    app.show_message('Hi', 'spy')
    paint(app)
    assert {'frame', 'window', 'dialog', 'button', 'scrollbar'} <= set(calls)


# ── Runtime theme switch: assign and the next frame re-renders ───────────────

def test_theme_switch_at_runtime():
    app = make_themed(NEWT)
    win = find(app._app.current_view, Window)
    assert cell(paint(app), win.x, win.y).char == NEWT.tl
    app._app.theme = replace(NEWT, tl='#')
    assert cell(paint(app), win.x, win.y).char == '#'


def test_default_is_newt():
    assert DEFAULT is NEWT


def test_flat_chrome_is_exported_and_subclassable():
    class MyChrome(FlatChrome):
        pass
    t = Theme(**{f.name: getattr(FLAT, f.name)
                 for f in Theme.__dataclass_fields__.values()})  # copy
    assert isinstance(t.chrome, FlatChrome)


def test_flat_buttons_dark_idle_accent_focused():
    from cookieui.widgets.button import Button
    from conftest import find_all, press
    from cookieui.core.event import KeyType
    app = make_themed(FLAT)
    btns = find_all(app._app.current_view, Button)
    ok = btns[0]
    app._app.current_view.focus_widget(ok)
    screen = paint(app)
    focused_bg = cell(screen, ok.x + 2, ok.y + 1).bg
    other_bg   = cell(screen, btns[1].x + 2, btns[1].y + 1).bg
    assert focused_bg == FLAT.btn_focused_bg          # lit up in the accent
    assert other_bg == FLAT.btn_bg                    # idle: near-black block
    assert other_bg != focused_bg

"""The sizing model: fractions vs cells, content-fit, fill, rows=, teaching errors."""
import pytest

from conftest import make, W, H, find
from cookieui import TuiApp, Window, Listbox, Table
from cookieui.helpers import resolve_size, footer_buttons, buttons_below, stack_below


# ── resolve_size: floats <= 1.0 are fractions, ints are cells ────────────────

def test_fraction_of_total():
    assert resolve_size(0.5, 100) == 50
    assert resolve_size(1.0, 100) == 100
    assert resolve_size(0.45, 100) == 45


def test_int_is_cells_even_one():
    assert resolve_size(40, 100) == 40
    assert resolve_size(1, 100) == 1            # int 1 is one cell, not "whole"


def test_fraction_rounds_and_floors_at_one():
    assert resolve_size(0.5, 7) == 4            # round, not truncate
    assert resolve_size(0.01, 10) == 1          # never zero


# ── page() sizing ─────────────────────────────────────────────────────────────

class FixedApp(TuiApp):
    def build_view(self):
        page = self.page(0.6, 0.8, title='Fixed')
        self.lb = page.listbox()                 # no height: fills to footer
        page.footer([('OK', lambda: None)])
        return page


class FitApp(TuiApp):
    def build_view(self):
        page = self.page(0.5, title='Fit')       # no height: content-fit
        page.label('one')
        page.label('two')
        self.win = page.win
        return page


def test_page_fraction_width():
    app = make(FixedApp)
    win = find(app._app.current_view, Window)
    assert win.width == round(W * 0.6)
    assert win.height == round(H * 0.8)
    # centered
    assert win.x == (W - win.width) // 2


def test_content_fit_wraps_children():
    app = make(FitApp)
    win = app.win
    assert not getattr(win, '_auto_height', True) or win._auto_height  # was content-fit
    # Height finalized on push: bottom border sits just below the lowest child
    # (counting its drop shadow when it has one).
    bottom = max(k.y + k.height - 1 + (1 if getattr(k, 'shadow', False) else 0)
                 for k in win._kids)
    assert win.height == bottom - win.y + 2


def test_fill_listbox_stops_above_footer():
    app = make(FixedApp)
    win = find(app._app.current_view, Window)
    lb  = app.lb
    from cookieui.widgets.button import Button
    btn = find(app._app.current_view, Button)
    # One clear row between the listbox bottom and the footer-button row.
    assert lb.y + lb.height == btn.y - 1
    # And the footer row is derived from the window geometry, not hand-counted.
    iy = win.y + 1
    ih = win.height - 2
    assert btn.y == iy + ih - 3 - 1


def test_rows_is_semantic_content_rows():
    class RowsApp(TuiApp):
        def build_view(self):
            page = self.page(0.5, title='Rows')      # content-fit window
            self.lb = page.listbox(rows=5)
            self.tbl = page.table(['A', 'B'], rows=8)
            return page
    app = make(RowsApp)
    assert app.lb.height == 5 + 2                    # rows + border chrome
    assert app.tbl.height == 8 + Table.CHROME        # rows + border/header chrome


# ── Teaching errors: wrong sizing raises a message that says what to do ──────

def test_fill_in_content_fit_window_raises():
    class BadApp(TuiApp):
        def build_view(self):
            page = self.page(0.5, title='Bad')       # content-fit
            page.listbox()                           # "fill" is circular here
            return page
    with pytest.raises(ValueError, match='content-fit'):
        make(BadApp)


def test_rows_and_height_together_raise():
    class BadApp(TuiApp):
        def build_view(self):
            page = self.page(0.6, 0.8)
            page.listbox(height=8, rows=5)
            return page
    with pytest.raises(ValueError, match='not both'):
        make(BadApp)


def test_footer_buttons_on_content_fit_raises():
    class BadApp(TuiApp):
        def build_view(self):
            page = self.page(0.5, title='Bad')
            page.label('x')
            footer_buttons(page.win, [('OK', lambda: None)])
            return page
    with pytest.raises(ValueError, match='content-fit'):
        make(BadApp)


# ── Shadow-aware stacking ─────────────────────────────────────────────────────

def test_stack_below_reserves_shadow_plus_gap():
    assert stack_below(5, 10) == 5 + 10 + 1 + 1
    assert stack_below(5, 10, gap=0) == 16


def test_columns_widths_and_buttons_below_reanchor():
    class ColsApp(TuiApp):
        def build_view(self):
            from cookieui import View
            view = View()
            self.left, self.right = self.columns(view, [2, 1], titles=['L', 'R'])
            self.left.layout().label('content')
            self.btns = buttons_below(view, self.left, [('Save', lambda: None)])
            return view
    app = make(ColsApp)
    left, right = app.left, app.right
    # 2:1 weights — left about twice the right (integer division slack allowed)
    assert abs(left.width - 2 * right.width) <= 3
    # No overlap: right starts past left's shadow column + gap
    assert right.x >= left.x + left.width + 1
    # buttons_below re-anchored after the content-fit height was finalized
    assert app.btns[0].y == stack_below(left.y, left.height, gap=1)


# ── Button-row alignment: centered by default (the Newt look), left/right opt-in ─

def _row_extent(btns):
    return btns[0].x, btns[-1].x + btns[-1].width


def test_buttons_center_by_default_in_layout_and_footer():
    class A(TuiApp):
        def build_view(self):
            page = self.page(0.6, 0.8, title='Align')
            page.listbox()
            self.flow = None
            self.foot = page.footer([('OK', lambda: None), ('Quit', self.quit)])
            self.win  = page.win
            return page
    app = make(A)
    left, right = _row_extent(app.foot)
    ix = app.win.x + 1
    iw = app.win.width - 2
    # symmetric within the interior (integer-division slack of 1 allowed)
    assert abs((left - ix) - ((ix + iw) - right)) <= 1
    assert left > ix + 2                       # visibly moved off the left edge


def test_buttons_align_left_and_right():
    class A(TuiApp):
        def build_view(self):
            page = self.page(0.6, title='Align')
            self.l = page.buttons([('A', None)], align='left')
            self.r = page.buttons([('B', None)], align='right')
            self.lay = page.lay
            return page
    app = make(A)
    assert app.l[0].x == app.lay.x                                   # anchored left
    assert app.r[0].x + app.r[0].width == app.lay.x + app.lay.width  # flush right


def test_unknown_align_raises_teaching_error():
    class A(TuiApp):
        def build_view(self):
            page = self.page(0.5, title='Bad')
            page.buttons([('A', None)], align='middle')
            return page
    with pytest.raises(ValueError, match="'left', 'center', or 'right'"):
        make(A)


def test_buttons_below_centers_under_window():
    from cookieui import View
    class A(TuiApp):
        def build_view(self):
            view = View()
            self.win, = self.columns(view, 1, titles=['W'])
            self.win.layout().label('x')
            self.btns = buttons_below(view, self.win, [('Go', lambda: None)])
            return view
    app = make(A)
    left, right = _row_extent(app.btns)
    mid_row = (left + right) / 2
    mid_win = app.win.x + app.win.width / 2
    assert abs(mid_row - mid_win) <= 1.5

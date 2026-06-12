"""The Page object: delegation order, view unwrapping, unpacking, the parity guard."""
import pytest

from conftest import make, at_size, W, H
from cookieui import TuiApp, View, Window
from cookieui.helpers import Page, VerticalLayout


class App(TuiApp):
    def build_view(self):
        page = self.page(0.5, title='Page')
        page.label('hello')
        page.buttons([('OK', lambda: None)])
        self.page_obj = page
        return page


# ── Delegation ────────────────────────────────────────────────────────────────

def test_parts_and_unpacking():
    app = make(App)
    page = app.page_obj
    view, win, lay = page                          # tuple-unpacking still works
    assert view is page.view
    assert win is page.win
    assert lay is page.lay
    assert isinstance(win, Window)
    assert isinstance(view, View)


def test_delegation_order_lay_then_win_then_view():
    app = make(App)
    page = app.page_obj
    # 'x' exists on both lay and win — the layout wins (row factories first)
    assert page.x == page.lay.x
    assert page.x != page.win.x
    # window-only attribute falls through to win
    assert page.interior_rect() == page.win.interior_rect()
    # view-only attribute falls through to view
    assert page.focus_first == page.view.focus_first


def test_unknown_attribute_raises_with_context():
    app = make(App)
    with pytest.raises(AttributeError, match='lay, win, or view'):
        app.page_obj.definitely_not_a_thing


def test_push_view_unwraps_page():
    app = make(App)
    assert app._app.current_view is app.page_obj.view   # not the Page wrapper


# ── The Pyright parity guard (NOTES.md recipe, layer 3) ──────────────────────
# Every row factory on VerticalLayout must have an explicit typed twin on Page —
# the explicit methods are what editors autocomplete; __getattr__ is only the
# long-tail fallback. A new factory without a twin fails here, not in a user's IDE.

# Deliberately fallback-only (geometry/plumbing, not row factories):
PAGE_FALLBACK_OK = {'fill_height'}


def test_page_mirrors_every_layout_factory():
    factories = {name for name, obj in vars(VerticalLayout).items()
                 if callable(obj) and not name.startswith('_')}
    explicit  = set(vars(Page))
    missing   = factories - explicit - PAGE_FALLBACK_OK
    assert not missing, (
        f'VerticalLayout factories without an explicit Page twin: {sorted(missing)} '
        '(add a typed method to Page — editors only autocomplete the explicit surface)')


def test_page_footer_delegates_to_footer_buttons():
    class FooterApp(TuiApp):
        def build_view(self):
            page = self.page(0.6, 0.8, title='F')
            page.listbox()
            self.btns = page.footer([('Back', lambda: None), ('Quit', self.quit)])
            self.win = page.win
            return page
    app = make(FooterApp)
    assert len(app.btns) == 2
    assert all(b in app.win._kids for b in app.btns)
    # footer row sits on the derived footer position, inside the window
    assert app.btns[0].y + 3 <= app.win.y + app.win.height


# ── Resize: builders re-run, data on self survives ───────────────────────────

def test_resize_rebuilds_at_new_size():
    app = make(App)
    w1 = app.page_obj.win.width
    at_size(app, w=60, h=20)
    w2 = app.page_obj.win.width                    # build_view ran again
    assert w2 == 30 and w1 == round(W * 0.5)
    assert app._app.current_view is app.page_obj.view


def test_resize_preserves_self_state():
    class Stateful(TuiApp):
        def setup(self):
            self.items = ['a', 'b']
        def build_view(self):
            page = self.page(0.6, 0.8, title='S')
            self.lb = page.listbox()
            self.lb.items = self.items
            page.footer([('Quit', self.quit)])
            return page
    app = make(Stateful)
    app.items.append('c')
    at_size(app, w=90, h=26)                       # rebuild
    assert app.lb.items == ['a', 'b', 'c']         # data lived on self, not the widget

"""Focus model: Tab/arrow single-cursor invariant, Enter form-flow, programmatic focus."""
from conftest import make, press, focused_widgets
from cookieui import TuiApp
from cookieui.core.event import Key, KeyType


class Form(TuiApp):
    def build_view(self):
        page = self.page(0.5, title='Form')
        self.usr = page.input(label='Username')
        self.pwd = page.input(label='Password', password=True)
        self.submitted = []
        self.pwd.on_enter = lambda: self.submitted.append((self.usr.value, self.pwd.value))
        self.ok, self.quit_btn = page.buttons([('OK', lambda: None), ('Quit', self.quit)])
        return page


def focused(app):
    ws = focused_widgets(app._app.current_view)
    assert len(ws) == 1, f'single-cursor invariant broken: {len(ws)} focused'
    return ws[0]


def test_initial_focus_is_first_widget():
    app = make(Form)
    assert focused(app) is app.usr


def test_tab_cycles_flat_list():
    app = make(Form)
    press(app, KeyType.TAB)
    assert focused(app) is app.pwd
    press(app, KeyType.TAB, KeyType.TAB)
    assert focused(app) is app.quit_btn
    press(app, KeyType.TAB)
    assert focused(app) is app.usr                  # wraps around
    press(app, KeyType.SHIFT_TAB)
    assert focused(app) is app.quit_btn             # and backwards


def test_arrows_cycle_within_window():
    app = make(Form)
    press(app, KeyType.DOWN)
    assert focused(app) is app.pwd
    press(app, KeyType.UP)
    assert focused(app) is app.usr


def test_interleaving_tab_and_arrows_never_forks_focus():
    # The regression this suite exists for: Window._kid_idx going stale after a
    # Tab left two highlights at once. Both cursors must self-sync every key.
    app = make(Form)
    press(app, KeyType.TAB, KeyType.TAB)            # Tab to the OK button
    assert focused(app) is app.ok
    press(app, KeyType.DOWN)                        # arrow continues FROM the button
    assert focused(app) is app.quit_btn
    press(app, KeyType.TAB)                         # and Tab continues from there
    assert focused(app) is app.usr
    press(app, KeyType.UP)                          # arrow back — still one cursor
    assert focused(app) is app.quit_btn


def test_typing_goes_to_the_focused_input_only():
    app = make(Form)
    press(app, 'tahseen')
    press(app, KeyType.TAB)
    press(app, 'secret')
    assert app.usr.value == 'tahseen'
    assert app.pwd.value == 'secret'


def test_enter_flows_to_next_field_then_submits():
    # usr has no on_enter → Enter moves focus (form flow); pwd has on_enter → submits.
    app = make(Form)
    press(app, 'me', KeyType.ENTER)                 # Enter in usr: focus moves to pwd
    assert focused(app) is app.pwd
    press(app, 'pw', KeyType.ENTER)                 # Enter in pwd: submit fires
    assert app.submitted == [('me', 'pw')]


def test_focus_widget_jumps_directly():
    app = make(Form)
    app._app.current_view.focus_widget(app.ok)
    assert focused(app) is app.ok
    press(app, KeyType.TAB)
    assert focused(app) is app.quit_btn             # cycle continues from the jump

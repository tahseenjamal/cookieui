"""The whiptail quartet + dialog mechanics: auto-close, Escape, key capture, wrap."""
from conftest import make, press, settle
from cookieui import TuiApp
from cookieui.core.event import KeyType


class Host(TuiApp):
    def build_view(self):
        page = self.page(0.5, title='Host')
        self.inp = page.input(label='Field')
        page.buttons([('Quit', self.quit)])
        return page


# ── show_message ──────────────────────────────────────────────────────────────

def test_show_message_sets_overlay_and_enter_closes():
    app = make(Host)
    closed = []
    app.show_message('Info', 'All good.', on_close=closed.append)
    assert app._app._dialog is not None
    press(app, KeyType.ENTER)               # OK button (≈150 ms pressed animation)
    settle()
    assert app._app._dialog is None         # auto-closed — no close_dialog() anywhere
    assert closed == ['OK']


def test_dialog_captures_all_keys_while_open():
    app = make(Host)
    press(app, 'abc')
    app.show_message('Info', 'modal')
    press(app, 'xyz')                       # must NOT reach the input behind
    assert app.inp.value == 'abc'
    press(app, KeyType.ESCAPE)              # Escape closes (last button), synchronously
    assert app._app._dialog is None
    press(app, 'd')
    assert app.inp.value == 'abcd'


def test_new_dialog_replaces_current():
    app = make(Host)
    first = app.show_message('One', 'first')
    second = app.show_message('Two', 'second')
    assert app._app._dialog is second and first is not second


# ── confirm ───────────────────────────────────────────────────────────────────

def test_confirm_yes_runs_on_yes():
    app = make(Host)
    picked = []
    app.confirm('Sure?', 'Really?', on_yes=lambda: picked.append('yes'))
    press(app, KeyType.ENTER)               # Yes is focused first
    settle()
    assert picked == ['yes'] and app._app._dialog is None


def test_confirm_escape_means_no():
    app = make(Host)
    picked = []
    app.confirm('Sure?', 'Really?',
                on_yes=lambda: picked.append('yes'),
                on_no=lambda: picked.append('no'))
    press(app, KeyType.ESCAPE)
    assert picked == ['no'] and app._app._dialog is None


def test_confirm_custom_labels():
    app = make(Host)
    picked = []
    app.confirm('Unsaved', 'Discard changes?', yes='Discard', no='Keep',
                on_yes=lambda: picked.append('discard'))
    press(app, KeyType.ENTER)
    settle()
    assert picked == ['discard']


# ── prompt ────────────────────────────────────────────────────────────────────

def test_prompt_enter_submits_text():
    app = make(Host)
    got = []
    app.prompt('New task', 'What needs doing?', on_submit=got.append)
    press(app, 'write tests', KeyType.ENTER)        # Enter in the field = OK
    assert got == ['write tests'] and app._app._dialog is None


def test_prompt_default_prefills_and_escape_cancels():
    app = make(Host)
    got, cancelled = [], []
    dlg = app.prompt('Rename', on_submit=got.append, default='old.txt',
                     on_cancel=lambda: cancelled.append(True))
    assert dlg.value == 'old.txt'
    press(app, KeyType.ESCAPE)
    assert got == [] and cancelled == [True] and app._app._dialog is None


# ── choose ────────────────────────────────────────────────────────────────────

def test_choose_enter_picks_the_paired_value():
    app = make(Host)
    got = []
    app.choose('Theme', [('Newt blue', 'newt'), ('Mocha', 'mocha')], on_pick=got.append)
    press(app, KeyType.DOWN, KeyType.ENTER)         # pick the second row
    assert got == ['mocha'] and app._app._dialog is None


def test_choose_plain_labels_pick_the_label():
    app = make(Host)
    got = []
    app.choose('Branch', ['main', 'dev'], on_pick=got.append)
    press(app, KeyType.ENTER)
    assert got == ['main']


def test_choose_escape_cancels():
    app = make(Host)
    got, cancelled = [], []
    app.choose('Branch', ['main'], on_pick=got.append,
               on_cancel=lambda: cancelled.append(True))
    press(app, KeyType.ESCAPE)
    assert got == [] and cancelled == [True]


# ── Dialogs never balloon: max_width word-wrap ───────────────────────────────

LONG = ('This is an exceptionally long error message that would, unwrapped, force the '
        'dialog to span nearly the entire terminal width and look nothing like a dialog.')


def test_long_message_wraps_at_max_width_cap():
    app = make(Host)                                # W=100 → default cap 60
    dlg = app.show_message('Error', LONG)
    assert dlg.width <= 60
    assert all(len(line) <= 60 - 6 for line in dlg.message.split('\n'))
    assert len(dlg.message.split('\n')) > 1         # actually wrapped, not clipped


def test_max_width_is_tunable():
    app = make(Host)
    wide   = app.show_message('E', LONG, max_width=0.9)
    narrow = app.show_message('E', LONG, max_width=0.4)
    assert narrow.width < wide.width <= 90


def test_prompt_and_choose_wrap_too():
    app = make(Host)
    dlg = app.prompt('Q', LONG, on_submit=lambda s: None)
    assert dlg.width <= 60
    press(app, KeyType.ESCAPE)
    dlg = app.choose('Q', ['a'], message=LONG)
    assert dlg.width <= 60

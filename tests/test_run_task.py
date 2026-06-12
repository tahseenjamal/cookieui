"""run_task: the one-call worker thread — guard, auto-detection, status flows, errors."""
import threading

import pytest

from conftest import make, wait_task
from cookieui import TuiApp


class BarApp(TuiApp):
    """One ProgressBar + one status Label — the canonical run_task view."""
    def build_view(self):
        page = self.page(0.5, title='Bar')
        self.bar = page.progressbar()
        self.status = page.label('idle')
        page.buttons([('Quit', self.quit)])
        return page


class TwoBarApp(TuiApp):
    def build_view(self):
        page = self.page(0.5, title='Two')
        self.bar1 = page.progressbar()
        self.bar2 = page.progressbar()
        page.buttons([('Quit', self.quit)])
        return page


class PlainApp(TuiApp):
    """No bar, no spinner, no status — the error-dialog fallback path."""
    def build_view(self):
        page = self.page(0.5, title='Plain')
        page.label('nothing to target')
        page.buttons([('Quit', self.quit)])
        return page


class SpinnerApp(TuiApp):
    def build_view(self):
        page = self.page(0.5, title='Spin')
        self.spin = page.spinner('Working')
        self.status = page.label('idle')
        page.buttons([('Quit', self.quit)])
        return page


# ── Single-flight guard ───────────────────────────────────────────────────────

def test_guard_rejects_second_task_while_busy():
    app = make(BarApp)
    gate = threading.Event()
    started = app.run_task(lambda on_progress: gate.wait(2), status=app.status)
    assert started is True
    assert app.run_task(lambda on_progress: None, status=app.status) is False
    gate.set()
    wait_task(app)
    # and the busy flag resets — a new task is accepted afterwards
    assert app.run_task(lambda on_progress: 'ok', status=app.status) is True
    wait_task(app)


# ── Auto-detection ────────────────────────────────────────────────────────────

def test_sole_bar_auto_detected_and_filled():
    app = make(BarApp)
    seen = []

    def work(on_progress):
        on_progress(0.5)
        seen.append(app.bar.value)
        return 'done'

    app.run_task(work, status=app.status)
    wait_task(app)
    assert seen == [0.5]                    # on_progress was wired straight to the bar
    assert app.bar.value == 1.0             # filled on success


def test_two_bars_means_no_auto_injection():
    app = make(TwoBarApp)
    kwargs_seen = []

    def work(**kwargs):
        kwargs_seen.append(set(kwargs))
        return 'x'

    app.run_task(work, status=None)
    wait_task(app)
    assert kwargs_seen == [set()]           # ambiguous → nothing injected


def test_explicit_progress_targets_that_bar():
    app = make(TwoBarApp)
    app.run_task(lambda on_progress: on_progress(0.3), progress=app.bar2, status=None)
    wait_task(app)
    assert app.bar2.value == 1.0
    assert app.bar1.value == 0.0


def test_progress_none_disables_injection():
    app = make(BarApp)
    kwargs_seen = []
    app.run_task(lambda **kw: kwargs_seen.append(set(kw)), progress=None, status=app.status)
    wait_task(app)
    assert kwargs_seen == [set()]
    assert app.bar.value == 0.0


# ── Status flows: bare noun = value, on_noun = callable ──────────────────────

def test_running_shows_synchronously_then_done_value():
    app = make(BarApp)
    gate = threading.Event()
    app.run_task(lambda on_progress: gate.wait(2), status=app.status,
                 running='Working…', done='Saved ✓')
    assert app.status.text == 'Working…'    # set before the thread even starts
    gate.set()
    wait_task(app)
    assert app.status.text == 'Saved ✓'


def test_bar_is_the_status_area_when_no_status():
    app = make(BarApp)
    app.status = None
    app.run_task(lambda on_progress: None, done='Complete ✓')
    wait_task(app)
    assert app.bar.text == 'Complete ✓'     # rendered centered on the bar face


def test_on_done_callable_supplies_dynamic_text():
    app = make(BarApp)
    app.run_task(lambda on_progress: 1234, status=app.status,
                 on_done=lambda n: f'✓ {n:,} bytes')
    wait_task(app)
    assert app.status.text == '✓ 1,234 bytes'


def test_done_value_and_on_done_behavior_together():
    app = make(BarApp)
    ran = []
    app.run_task(lambda on_progress: 'r', status=app.status,
                 done='Static ✓', on_done=lambda r: ran.append(r) or 'ignored')
    wait_task(app)
    assert ran == ['r']                     # callback ran for behavior
    assert app.status.text == 'Static ✓'    # the value owns the display


def test_no_done_no_on_done_shows_str_result():
    app = make(BarApp)
    app.run_task(lambda on_progress: 42, status=app.status)
    wait_task(app)
    assert app.status.text == '42'


def test_on_done_string_raises_teaching_typeerror():
    app = make(BarApp)
    with pytest.raises(TypeError, match='bare noun = value'):
        app.run_task(lambda on_progress: None, status=app.status, on_done='Saved ✓')
    assert getattr(app, '_task_busy', False) is False   # guard not left stuck


# ── Errors are never silently lost ────────────────────────────────────────────

def boom(**kwargs):
    raise RuntimeError('kaput')


def test_error_value_shown_on_status():
    app = make(BarApp)
    app.run_task(boom, status=app.status, error='✗ failed')
    wait_task(app)
    assert app.status.text == '✗ failed'


def test_on_error_callable_gets_the_exception():
    app = make(BarApp)
    app.run_task(boom, status=app.status, on_error=lambda e: f'✗ {e}')
    wait_task(app)
    assert app.status.text == '✗ kaput'


def test_default_error_text_on_status():
    app = make(BarApp)
    app.run_task(boom, status=app.status)
    wait_task(app)
    assert app.status.text == 'Error: kaput'


def test_error_dialog_when_nothing_to_write_to():
    app = make(PlainApp)
    app.run_task(boom)
    wait_task(app)
    dlg = app._app._dialog
    assert dlg is not None and dlg.title == 'Error'
    assert 'kaput' in dlg.message


# ── Spinner lifecycle: its disappearance IS the done signal ───────────────────

def test_spinner_shown_during_and_hidden_after():
    app = make(SpinnerApp)
    gate = threading.Event()
    app.run_task(lambda: gate.wait(2), status=app.status, running='Working…')
    assert app.spin.visible is True
    gate.set()
    wait_task(app)
    assert app.spin.visible is False
    assert app.status.text == 'True'        # gate.wait returned True → str(result)

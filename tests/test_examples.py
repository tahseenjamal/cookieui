"""Every shipped example constructs, draws, survives resize, and its core flow works
under real key dispatch. (html2pdf is excluded: extra deps, deliberate escape hatch.)"""
import importlib.util
import sys
import pathlib

import pytest

from conftest import ROOT, at_size, press, paint, wait_task, settle, find, W, H
from cookieui import TuiApp, Listbox, Table, TextView
from cookieui.core.event import KeyType

EXAMPLES_DIR = ROOT / 'examples'

EXAMPLES = ['commander', 'demo', 'envbrowser', 'file-copy-progress', 'filebrowsing', 'gitlog',
            'processes', 'progressdemo', 'quickdialogs', 'spinnerdemo', 'sysinfo',
            'themedemo', 'todo']

# Constructor args for the examples whose __init__ takes them
CTOR_ARGS = {
    'filebrowsing': lambda: (EXAMPLES_DIR,),
    'gitlog':       lambda: (ROOT,),            # this repo is a git repo
}


def load_example(name: str, tmp_path=None):
    """Import an example module from its file (the dash-named one included)."""
    modname = 'example_' + name.replace('-', '_')
    spec = importlib.util.spec_from_file_location(modname, EXAMPLES_DIR / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    if hasattr(mod, 'TODOS_FILE') and tmp_path is not None:
        mod.TODOS_FILE = tmp_path / 'todos.json'    # never touch the user's real file
    return mod


def app_class(mod):
    classes = [c for c in vars(mod).values()
               if isinstance(c, type) and issubclass(c, TuiApp)
               and c.__module__ == mod.__name__]
    assert len(classes) == 1, f'{mod.__name__}: expected exactly one TuiApp subclass'
    return classes[0]


def construct(name: str, tmp_path=None):
    mod = load_example(name, tmp_path)
    cls = app_class(mod)
    args = CTOR_ARGS.get(name, tuple)()
    return mod, at_size(cls(*args))


# ── The sweep: every example boots, draws, resizes, takes keys ────────────────

@pytest.mark.parametrize('name', EXAMPLES)
def test_example_boots_draws_and_resizes(name, tmp_path):
    _, app = construct(name, tmp_path)
    assert app._app.current_view is not None
    paint(app)
    press(app, KeyType.TAB, KeyType.DOWN, KeyType.UP)       # basic dispatch, no crash
    at_size(app, w=80, h=24)                                # rebuild smaller
    paint(app)
    at_size(app, w=W, h=H)                                  # and back
    paint(app)


# ── Deep flows ────────────────────────────────────────────────────────────────

def test_todo_add_persists_to_disk(tmp_path):
    mod, app = construct('todo', tmp_path)
    press(app, 'write tests', KeyType.ENTER)                # input is focused first
    lb = find(app._app.current_view, Listbox)
    assert any('write tests' in item for item in lb.items)
    saved = mod.load_todos()
    assert [t.text for t in saved] == ['write tests']       # really wrote the JSON
    # a second app over the same file starts with the saved task (survives restart)
    _, app2 = construct('todo', tmp_path)
    lb2 = find(app2._app.current_view, Listbox)
    assert any('write tests' in item for item in lb2.items)


def test_file_copy_round_trips_real_bytes(tmp_path):
    _, app = construct('file-copy-progress', tmp_path)
    src = tmp_path / 'src.bin'
    dst = tmp_path / 'dst.bin'
    payload = bytes(range(256)) * 4096                      # 1 MiB
    src.write_bytes(payload)

    app.src.set_value(str(src))
    app.dst.set_value(str(dst))
    app._app.current_view.focus_widget(app.dst)
    press(app, KeyType.ENTER)                               # Enter in last field = Copy
    wait_task(app)
    assert dst.read_bytes() == payload
    assert app.status.text.startswith('✓')
    assert not dst.with_name('dst.bin.part').exists()       # atomic publish, no stray


def test_file_copy_engine_is_pure_and_atomic(tmp_path):
    mod = load_example('file-copy-progress', tmp_path)
    src = tmp_path / 'a'; src.write_bytes(b'x' * 1000)
    fractions = []
    n = mod.copy_file(src, tmp_path / 'b', fractions.append)
    assert n == 1000 and (tmp_path / 'b').read_bytes() == b'x' * 1000
    assert fractions and fractions[-1] == 1.0               # byte-accurate progress
    with pytest.raises(Exception):
        mod.copy_file(tmp_path / 'missing', tmp_path / 'c', lambda f: None)
    assert not (tmp_path / 'c.part').exists()               # failure leaves no .part


def test_envbrowser_live_filter(monkeypatch, tmp_path):
    monkeypatch.setenv('COOKIEUI_TEST_VAR', 'sentinel-value')
    _, app = construct('envbrowser', tmp_path)              # ALL_VARS read at import
    lb = find(app._app.current_view, Listbox)
    total = len(lb.items)
    press(app, 'COOKIEUI_TEST_VAR')                         # search field focused first
    assert len(lb.items) == 1 < total                       # narrowed per keystroke
    assert 'sentinel-value' in lb.items[0]
    press(app, KeyType.BACKSPACE)                           # edits keep filtering
    assert len(lb.items) >= 1


def test_gitlog_shows_commits_and_pushes_detail_view(tmp_path):
    _, app = construct('gitlog', tmp_path)
    lb = find(app._app.current_view, Listbox)
    assert len(lb.items) > 0                                # this repo has commits
    app._app.current_view.focus_widget(lb)
    press(app, KeyType.ENTER)                               # Show → pushes commit view
    assert len(app._app._views) == 2
    tv = find(app._app.current_view, TextView)
    assert 'commit' in tv.text.splitlines()[0]
    press(app, KeyType.ESCAPE)                              # bind_quit → back, not quit
    assert len(app._app._views) == 1


def test_processes_table_filters_live(tmp_path):
    _, app = construct('processes', tmp_path)
    tbl = find(app._app.current_view, Table)
    assert len(tbl.rows) > 0                                # ps returned something
    press(app, 'zz-no-such-command-zz')
    assert len(tbl.rows) == 0                               # filter narrows to nothing
    for _ in range(len('zz-no-such-command-zz')):
        press(app, KeyType.BACKSPACE)
    assert len(tbl.rows) > 0


def test_quickdialogs_message_flow(tmp_path):
    _, app = construct('quickdialogs', tmp_path)
    press(app, KeyType.ENTER)                               # Message button (focused first)
    settle()                                                # button animation
    assert app._app._dialog is not None
    press(app, KeyType.ESCAPE)
    assert app._app._dialog is None

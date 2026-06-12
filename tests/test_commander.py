"""Cookie Commander (the book's capstone): end-to-end through real key dispatch."""
import importlib.util
import pathlib
import sys
import time

from conftest import ROOT, make, press, paint, wait_task
from cookieui.core.event import Key, KeyType


def load():
    spec = importlib.util.spec_from_file_location(
        'example_commander', ROOT / 'examples' / 'commander.py')
    mod = importlib.util.module_from_spec(spec)
    sys.modules['example_commander'] = mod
    spec.loader.exec_module(mod)
    return mod


def select(browser, name):
    browser.selected_index = browser.items.index(name)


def test_commander_copy_delete_view_roundtrip(tmp_path):
    mod = load()
    A = (tmp_path / 'a').resolve(); A.mkdir()
    B = (tmp_path / 'b').resolve(); B.mkdir()
    payload = bytes(range(256)) * 512
    (A / 'hello.bin').write_bytes(payload)

    app = make(lambda: mod.Commander(left=A, right=B))
    paint(app)

    # copy left → right through the real 'c' binding
    select(app.left, 'hello.bin')
    press(app, 'c')
    wait_task(app)
    assert (B / 'hello.bin').read_bytes() == payload
    assert app.status.text.startswith('✓ Copy')

    # the guard: copying onto an existing name is a status line, not a crash
    # (refresh after the copy reset the selection to the top — re-select first)
    select(app.left, 'hello.bin')
    press(app, 'c')
    assert 'already exists' in app.status.text

    # delete from the right pane, through the confirmation dialog
    app._app.current_view.focus_widget(app.right)
    app.refresh()
    select(app.right, 'hello.bin')
    press(app, 'd')
    assert app._app._dialog is not None             # confirm is up
    press(app, Key(KeyType.ENTER))                  # 'Delete' is focused first
    time.sleep(0.25)                                # button animation
    wait_task(app)
    assert not (B / 'hello.bin').exists()

    # the viewer: Enter on a file pushes, Escape pops (bind_quit, not quit)
    app._app.current_view.focus_widget(app.left)
    select(app.left, 'hello.bin')
    press(app, Key(KeyType.ENTER))
    assert len(app._app._views) == 2
    press(app, Key(KeyType.ESCAPE))
    assert len(app._app._views) == 1


def test_commander_engines_tree_and_move(tmp_path):
    mod = load()
    A = tmp_path / 'src'; A.mkdir()
    (A / 'deep').mkdir()
    (A / 'deep' / 'x.txt').write_text('tree')
    (A / 'top.txt').write_text('top')

    fractions = []
    n = mod.copy_path(A, tmp_path / 'dst', fractions.append)
    assert (tmp_path / 'dst' / 'deep' / 'x.txt').read_text() == 'tree'
    assert (tmp_path / 'dst' / 'top.txt').read_text() == 'top'
    assert n == 7 and fractions[-1] == 1.0          # 'tree' + 'top' bytes... names lie;
    # byte count: len('tree') + len('top') == 7 — byte-accurate, file-spanning

    mod.move_path(tmp_path / 'dst' / 'top.txt', tmp_path / 'moved.txt', fractions.append)
    assert (tmp_path / 'moved.txt').read_text() == 'top'
    assert not (tmp_path / 'dst' / 'top.txt').exists()


def test_filebrowser_selected_path(tmp_path):
    from cookieui.contrib import FileBrowser
    (tmp_path / 'f.txt').write_text('x')
    fb = FileBrowser(0, 0, 40, 10, tmp_path)
    fb.selected_index = fb.items.index('../  (go up)')
    assert fb.selected_path is None                  # navigation, not selection
    fb.selected_index = fb.items.index('f.txt')
    assert fb.selected_path == (tmp_path / 'f.txt')

"""Shared headless-testing harness for the CookieUI suite.

The rules here are the ones in CLAUDE.md's "Verifying changes" section, made permanent:

- Drive apps with **real key dispatch** (`App._dispatch` → view/dialog `handle_key`),
  never by calling private handlers — bypassing dispatch hides exactly the bugs
  (focus desync, dialog capture) this suite exists to catch.
- **Fake the terminal size first, then rebuild** through the real resize path —
  AUTO_VIEW builds the first view inside __init__ at whatever size the environment
  reports, so the harness re-runs the builders at the fake size.
- Button clicks fire ~150 ms after Enter (pressed-state animation on a daemon
  thread) — use `settle()` before asserting on a click's effect.
- run_task work happens on a worker thread — use `wait_task(app)`.
"""
import sys
import time
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cookieui.core.event import Key, KeyType                     # noqa: E402

W, H = 100, 30          # the standard fake terminal for the whole suite


def at_size(app, w: int = W, h: int = H):
    """Pin a constructed TuiApp to a fake terminal size and rebuild its views
    through the real resize path (same code SIGWINCH runs)."""
    app._app._terminal.width  = w
    app._app._terminal.height = h
    app._app._on_resize(w, h)
    app._app._apply_resize()
    return app


def make(app_cls, *args, w: int = W, h: int = H, **kwargs):
    """Construct an app normally (real __init__, AUTO_VIEW and all), then pin it
    to the fake size."""
    return at_size(app_cls(*args, **kwargs), w, h)


def press(app, *keys):
    """Dispatch keys through the real run-loop entry point (dialog capture included).

    Each key is a KeyType, a ready-made Key, or a string (each char typed in turn).
    """
    for k in keys:
        if isinstance(k, str):
            for ch in k:
                app._app._dispatch(Key(KeyType.CHAR, ch))
        elif isinstance(k, Key):
            app._app._dispatch(k)
        else:
            app._app._dispatch(Key(k))


def settle(seconds: float = 0.25):
    """Wait out the Button pressed-state animation (~150 ms) before asserting."""
    time.sleep(seconds)


def wait_task(app, timeout: float = 5.0):
    """Block until the app's run_task worker finishes (poll the busy flag)."""
    deadline = time.time() + timeout
    while getattr(app, '_task_busy', False):
        if time.time() > deadline:
            raise AssertionError('run_task did not finish within %ss' % timeout)
        time.sleep(0.01)
    time.sleep(0.02)        # let the finally-block writes land


def paint(app):
    """Compose the current frame into the Screen cell grid (no terminal output)
    and return the Screen for cell inspection."""
    a = app._app
    a._screen.clear(bg=a.theme.bg)
    if a.current_view:
        a.current_view.draw(a._screen, a.theme)
    if a._dialog:
        a._dialog.draw(a._screen, a.theme)
    return a._screen


def row_text(screen, y: int) -> str:
    """The characters of one screen row as a string."""
    return ''.join(screen._cells[y][x].char for x in range(screen.width))


def screen_text(screen) -> str:
    """The whole screen as newline-joined rows (for substring asserts)."""
    return '\n'.join(row_text(screen, y) for y in range(screen.height))


def find_all(view, cls):
    """Every widget of `cls` in a view — top level and inside windows."""
    out = []
    for w in view._all:
        if isinstance(w, cls):
            out.append(w)
        out.extend(k for k in getattr(w, '_kids', []) if isinstance(k, cls))
    return out


def find(view, cls, index: int = 0):
    """The index-th widget of `cls` in the view (raises if missing)."""
    found = find_all(view, cls)
    assert found, f'no {cls.__name__} in view'
    return found[index]


def focused_widgets(view):
    """All widgets with .focused set — the single-cursor invariant says len == 1."""
    return [w for w in view._focusable if w.focused]

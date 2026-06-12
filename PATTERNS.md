# Pattern → Example cheat sheet

Every example app (in `examples/`) documents its patterns in a `DESIGN PATTERNS DEMONSTRATED`
docstring section. This table maps each pattern to the file(s) that show it best, so you can
jump straight to working code instead of scanning all twelve files. All file names below refer
to `examples/<file>`.

> Learning order: `demo.py` → `quickdialogs.py` → `todo.py`, then `file-copy-progress.py` for
> background work, then whichever matches your app.
> `html2pdf.py` is the **low-level escape hatch** — read it last, copy from it never.

## App scaffolding

| Pattern | Best example | Also in |
|---|---|---|
| The standard app shape (`TuiApp` subclass + `build_view`, **no `__init__`**) | `quickdialogs.py` | `demo.py`, `sysinfo.py`, `envbrowser.py`, `spinnerdemo.py`, `progressdemo.py` |
| App state in `setup()` (runs before the auto-pushed `build_view`) | `todo.py` | |
| Constructor arguments: state *before* `super().__init__()` | `gitlog.py` | `filebrowsing.py` |
| `page()` one-line view scaffold | `quickdialogs.py` | all but html2pdf |
| Builder views → automatic resize rebuild (`build_view` auto-pushed as one; extra views: `push_view(self.build_detail)`, no parens) | `demo.py` | all |
| Builders with arguments (capture, then lambda) | `demo.py` (`replace_view(lambda: ...)`) | `gitlog.py`, `filebrowsing.py` |
| Multi-screen navigation: `replace_view` (login ↔ settings) | `demo.py` | |
| Drill-down navigation: `push_view`/`pop_view` (list → detail → back) | `gitlog.py` | `filebrowsing.py` |
| State on the app, not in widgets (survives resize rebuilds) | `todo.py` (`self.todos`) | `filebrowsing.py` (`self._dir`) |

## Sizing (see "The sizing model" in the README)

| Pattern | Best example | Also in |
|---|---|---|
| Fractions of the terminal: `page(0.7, 0.8)` | `todo.py` | `envbrowser.py`, `gitlog.py`, `filebrowsing.py` |
| Content-fit window (no height — wraps the content) | `sysinfo.py` | `demo.py` login, `quickdialogs.py`, `spinnerdemo.py`, `progressdemo.py` |
| Side-by-side windows: `columns(view, 2, titles=[...])` | `demo.py` settings | |
| Fill widget with no size (`page.listbox()` → fills to the footer) | `todo.py` | `envbrowser.py`, `gitlog.py` |
| One-call window body: `page.fill_with(WidgetClass, ...)` (or `win.fill_with` on a raw Window) | `filebrowsing.py` | `gitlog.py` commit view |
| Semantic row counts: `page.listbox(rows=5)` | *(documented in README — use inside content-fit windows)* | |
| Consecutive label rows: `page(..., spacing=0)` | `sysinfo.py` | |
| Table column widths by weight, right-aligned numbers (`('CPU%', 1, '>')`) | `processes.py` | |

## Widgets & state

**The local-vs-`self.` rule.** Where a widget reference lives is a statement about who needs it:

- **Local variable** (`result = page.label(...)`, `inp`, `lb`) — the widget is only touched by
  callbacks defined *in the same `build_view`*. Closures capture it; nothing outside needs it.
  On a resize rebuild the whole view — widgets and closures together — is recreated as a unit,
  so nothing can go stale. This is the default: most widgets should be locals.
  (`quickdialogs.py`'s `result`, `todo.py`'s `inp`/`lb`, `demo.py`'s `usr`/`pwd`.)
- **`self.widget`** — the widget is accessed from *outside* `build_view`: another method
  (`sysinfo.py`'s `refresh()` writing `self._info_labels`; `file-copy-progress.py`'s `copy()`
  passing `status=self.status` to run_task), or another view's callback
  (`filebrowsing.py`'s `go_up` using `self.browser`). Threads re-read `self.x` on each
  access — a resize rebuild swaps in the new widget, and the fresh lookup keeps them correct.
- **`self.data` (app state, never widget state)** — domain data like `todo.py`'s `self.todos` or
  `filebrowsing.py`'s `self._dir` always lives on the app: it must survive rebuilds, and widgets
  merely *render* it.

Rule of thumb: **widgets are locals until something outside `build_view` needs them; data is
always on `self`.**

| Pattern | Best example | Also in |
|---|---|---|
| Mutate-and-redraw (set `.text` / `.value` / `.items`, never call draw) | `sysinfo.py` (`refresh()`) | all |
| Value-carrying rows: `(label, value)` items + `selected_value` | `envbrowser.py` | `gitlog.py`, `quickdialogs.py` choose |
| Value-carrying **table** rows: `t.rows = [((cells…), obj), …]` | `processes.py` | |
| Sorting is data logic — sort the data, assign `.rows` (the widget never sorts) | `processes.py` | |
| Live `label.text` refresh in place (no view rebuild) | `sysinfo.py` | `file-copy-progress.py` validation |
| Draw-time clipping (never slice text to a width) | `sysinfo.py`, `envbrowser.py` | gitlog labels |
| Spinner / ProgressBar during background work | via `run_task` — see **Background work** below | |
| TextView for long output (scroll, `wrap=False` for code) | `gitlog.py` | `filebrowsing.py` viewer |
| Composite contrib widget (FileBrowser navigating in place) | `filebrowsing.py` | `html2pdf.py` |
| Checkbox batches: `page.checkboxes([...])` | `demo.py` settings | |
| Spinner styles + live restyle (`rg.on_change` mutates `spin.frames` mid-run) | `spinnerdemo.py` | |

## Buttons

| Pattern | Best example | Also in |
|---|---|---|
| Labels + callbacks together: `page.buttons([('OK', fn), ...])` | `quickdialogs.py` | `demo.py`, `sysinfo.py` |
| Footer row in a fixed-height window: `page.footer([...])` | `todo.py` (4 buttons) | `envbrowser.py`, `gitlog.py`, `filebrowsing.py` |
| Buttons in the flow (content-fit windows): `page.buttons` | `sysinfo.py` | `spinnerdemo.py`, `progressdemo.py` |
| Floating row below a window: `buttons_below(view, win, [...])` | `demo.py` settings | |

## Keys & events

| Pattern | Best example | Also in |
|---|---|---|
| Enter moves to the next field automatically (no wiring) | `demo.py` login | |
| Enter submits on the last field: `inp.on_enter = do_login` | `demo.py` | `todo.py` |
| Live filtering: `inp.on_change = refresh` | `envbrowser.py` | `processes.py` (on a Table) |
| One-line shortcut: `bind_key(page.view, KeyType.CHAR, fn, char='r')` | `sysinfo.py` | |
| Esc means something else: `AUTO_QUIT = False` + `bind_key(ESCAPE, ...)` | `filebrowsing.py` (Esc = up a dir) | |
| Esc/q = "back" on one pushed view: `bind_quit(page.view, self.pop_view)` | `gitlog.py` commit view | `filebrowsing.py` viewer |
| Enter on a listbox row: `bind_enter_action(lb, fn)` | `todo.py` (toggle) | `envbrowser.py` |

## Dialogs (the whiptail quartet)

| Pattern | Best example | Also in |
|---|---|---|
| `show_message` / `confirm` / `prompt` / `choose` — one line each | `quickdialogs.py` | |
| Quit confirmation: `confirm('Quit?', ..., self.quit)` | `demo.py` | |
| Dialogs auto-close; callback only says what to do *after* | `quickdialogs.py` | all |

## Background work

**The domain/UI boundary rule.** Domain logic lives in **pure module-level functions**
(`copy_file`, `load_log`, `collect_info`, `filtered`, `read_text`); the app class only *wires
widgets to them*. For long-running work the engine's entire UI dependency is an `on_progress`
callback — it **returns** results (the UI decides how to render them), **raises** on failure
(the UI decides what an error looks like), and never knows it runs on a thread (threading is a
UI concern). This keeps the engine testable without a terminal and reusable outside the TUI.
A callback parameter is the whole boundary — no observer classes, no event bus.

**Which way do the arrows point?** Two different "directions" live here, and they point
opposite ways — both on purpose:

- **Knowledge (dependency)** points UI → domain: the app imports and calls `download`;
  `download` knows nothing. Inverting it (`download(app)` poking `app.bar`) would make the
  stable core depend on the most volatile layer — rename a widget and your file-copy logic
  breaks, and the engine can no longer be tested or reused without a terminal.
- **Control at runtime** flows domain → UI: `download` *calls* `on_progress(0.42)`, which runs
  a UI-supplied closure that sets `bar.value`. The engine drives the calls *blindly* — it
  doesn't know whether the listener is a progress bar, a log line, or a test's `list.append`.
  That split — domain drives the calls, UI owns the knowledge — is what "inversion of control"
  means, and the callback parameter is the entire mechanism.

The framework direction is the opposite, also on purpose: `TuiApp` calls *your* `build_view()`
and `setup()` ("don't call us, we'll call you"). One question decides which side calls which:
**whichever side is the stable core gets called by the volatile side.** `TuiApp` is stable →
it calls your app. `copy_file` is stable → your app calls it.

```
TuiApp (framework) ──calls──► YourApp (UI) ──calls──► copy_file (engine)
                                   ▲                        │
                                   ╰── on_progress (blind) ─╯
```

| Pattern | Best example | Also in |
|---|---|---|
| `self.run_task(fn, status=..., running=...)` — the one-call worker (guard, auto progress/spinner, status text, thread) | `spinnerdemo.py` | `progressdemo.py`, `file-copy-progress.py` |
| Domain logic as a pure function + `on_progress` callback | `file-copy-progress.py` (`copy_file`) | `progressdemo.py` (`download`), `spinnerdemo.py` (`long_task`) |
| The worker pattern on **real I/O** (chunked read, byte-accurate progress) | `file-copy-progress.py` | |
| Auto-detected progress bar / spinner (sole one in the view; widget stays a local) | `progressdemo.py` | `spinnerdemo.py`, `file-copy-progress.py` |
| The bar as its own status area — texts render centered on the bar face (no `status=` label) | `progressdemo.py` | |
| The noun/on_noun rule: `done='Complete ✓'` is a value, `on_done=lambda n: f'✓ {n:,} bytes'` is a callable — like `confirm`'s `yes=`/`on_yes=` | `progressdemo.py` (value) / `file-copy-progress.py` (callable) | |
| Engine's return value *is* the status (no on_done at all) | `spinnerdemo.py` | |
| Failure text via `on_error=lambda e: f'✗ {e}'` (defaults: status 'Error: …' or a dialog) | `file-copy-progress.py` | |
| Atomic publish (write `.part`, `os.replace` at the end — daemon-thread safe) | `file-copy-progress.py` | |
| Worker mutates widget attributes (no locks, no draw calls); raw `threading.Thread` only in the escape hatch | `html2pdf.py` | |
| External commands (`subprocess`) feeding widgets | `gitlog.py` | |

## The low-level escape hatch

| Pattern | Example |
|---|---|
| Raw `App`/`View` (no TuiApp auto-wiring), manual geometry, `WindowColumn`, `stack_beside`/`stack_below`, custom status bar, background thread + custom widget | `html2pdf.py` — read the banner in that file first |

#!/usr/bin/env python3
"""Cookie Commander — a two-pane file manager (the book's capstone).

OVERVIEW:
  Two FileBrowser panes side by side, a framed transfer bar and a status bar
  beneath them, and single-key actions: copy or move the selection to the
  other pane, delete with confirmation, make a directory, view a file.

KEYBOARD CONTROLS:
  - Tab: switch panes (the focused pane is the source of every action)
  - Up/Down/Enter: navigate; Enter on a file opens the viewer
  - c: copy selection to the other pane     - m: move it
  - d: delete selection (confirms first)    - n: new directory (prompts)
  - Esc / q: quit (in the viewer they mean back)

DESIGN PATTERNS DEMONSTRATED:
  - Engines and adapters: copy_path/move_path/delete_path are pure module-level
    functions — thin shutil wrappers, kept deliberately boring so the example is
    about the UI, not file I/O (the domain logic should never be the clever part)
  - run_task with auto-detection: the view's sole ProgressBar is adopted, the
    engines' on_progress is injected, outcomes land on the status label, the
    single-flight guard makes a second 'c' during a copy a safe no-op
  - Composite reuse: FileBrowser panes via fill_with — zero geometry
  - The view stack: the viewer is a pushed builder; Esc pops back
  - columns + shadow-aware stacking: no coordinates anywhere
"""
import shutil
import pathlib

from cookieui import (TuiApp, View, Window, FileBrowser, TextView, ProgressBar, Label,
                      bind_key, bind_quit, stack_below)
from cookieui.core.event import KeyType


# ── Domain logic — pure, no UI, no threads. Deliberately boring: shutil does
#    the real work, so the example stays about the UI, not file I/O. ───────────

def copy_path(src: pathlib.Path, dst: pathlib.Path, on_progress):
    """Copy a file, or a whole directory tree."""
    (shutil.copytree if src.is_dir() else shutil.copy2)(src, dst)
    on_progress(1.0)


def move_path(src: pathlib.Path, dst: pathlib.Path, on_progress):
    """Move a file or tree — a rename in place, or copy + delete across volumes."""
    shutil.move(str(src), str(dst))
    on_progress(1.0)


def delete_path(path: pathlib.Path, on_progress):
    """Delete a file, or a whole tree."""
    shutil.rmtree(path) if path.is_dir() else path.unlink()
    on_progress(1.0)


def read_text(path: pathlib.Path, limit: int = 512 * 1024) -> str:
    """First `limit` bytes as text, decoding errors replaced — viewers must
    never crash on the file they were pointed at."""
    return path.read_bytes()[:limit].decode('utf-8', errors='replace')


HINT = ('Tab switch pane · Enter open/view · c copy · m move · '
        'd delete · n new dir · q quit')


# ── UI — a thin adapter over the engines ─────────────────────────────────────

class Commander(TuiApp):
    AUTO_STATUS = False          # the status label below the panes is the hint line

    def __init__(self, left=None, right=None):
        self.ldir = pathlib.Path(left or pathlib.Path.cwd())
        self.rdir = pathlib.Path(right or pathlib.Path.home())
        super().__init__()

    def build_view(self):
        view = View()
        H, W = self.ts.height(), self.ts.width()
        lwin, rwin = self.columns(view, 2, height=H - 12, y=1)   # leave room below
        self.left = lwin.fill_with(FileBrowser, self.ldir,
                                   on_select=self.view_file,
                                   on_dir_change=lambda p: self._remember(0, p))
        self.right = rwin.fill_with(FileBrowser, self.rdir,
                                    on_select=self.view_file,
                                    on_dir_change=lambda p: self._remember(1, p))

        # the shared progress bar lives in a framed 'Transfer' window under the
        # panes — a 3-row window IS a frame + title + one content row (Ch 18)
        span = (rwin.x + rwin.width) - lwin.x
        xfer = Window(lwin.x, stack_below(lwin.y, lwin.height), span, 3, title='Transfer')
        view.add(xfer)
        ix, iy, iw, _ = xfer.interior_rect()
        bar = ProgressBar(ix, iy, iw)                # run_task adopts the sole bar
        xfer.add(bar)

        # a real status bar along the bottom row — surface-filled, not a bare
        # label floating on the background — carrying the hint and outcomes
        sbar = Window(0, H - 3, W, 3, shadow=False)
        view.add(sbar)
        sx, sy = sbar.interior()
        self.status = Label(sx + 1, sy, HINT, max_width=W - 4)
        sbar.add(self.status)

        bind_key(view, KeyType.CHAR, self.copy, char='c')
        bind_key(view, KeyType.CHAR, self.move, char='m')
        bind_key(view, KeyType.CHAR, self.delete, char='d')
        bind_key(view, KeyType.CHAR, self.mkdir, char='n')
        return view

    # ── pane bookkeeping ──────────────────────────────────────────────────
    def _remember(self, side, path):
        if side == 0:
            self.ldir = path                          # survives resize rebuilds
        else:
            self.rdir = path

    def panes(self):
        """(source, destination) panes, source = the focused one."""
        return (self.right, self.left) if self.right.focused else (self.left, self.right)

    def selection(self):
        src, _ = self.panes()
        sel = src.selected_path                  # None on the go-up row
        return sel if sel is not None and sel.exists() else None

    def refresh(self):
        self.left.open_dir(self.left.current_dir)
        self.right.open_dir(self.right.current_dir)

    # ── actions: validate, then hand an engine to run_task ───────────────
    def _transfer(self, engine, verb):
        sel = self.selection()
        if sel is None:
            self.status.text = f'✗ Nothing selected to {verb.lower()}.'
            return
        _, dst = self.panes()
        target = dst.current_dir / sel.name
        if target.exists():
            self.status.text = f'✗ {target.name} already exists in the other pane.'
            return

        def done(_):
            self.refresh()
            return f'✓ {verb} {sel.name}'

        self.run_task(engine, sel, target, status=self.status,
                      running=f'{verb}ing {sel.name} …',
                      on_done=done, on_error=lambda e: f'✗ {e}')

    def copy(self):
        self._transfer(copy_path, 'Copy')

    def move(self):
        self._transfer(move_path, 'Move')

    def delete(self):
        sel = self.selection()
        if sel is None:
            self.status.text = '✗ Nothing selected to delete.'
            return

        def really():
            def done(_):
                self.refresh()
                return f'✓ Deleted {sel.name}'
            self.run_task(delete_path, sel, status=self.status,
                          running=f'Deleting {sel.name} …',
                          on_done=done, on_error=lambda e: f'✗ {e}')

        self.confirm('Delete?', f'Delete "{sel.name}" for good?',
                     yes='Delete', no='Keep', on_yes=really)

    def mkdir(self):
        src, _ = self.panes()

        def make(name):
            name = name.strip()
            if not name:
                return
            try:
                (src.current_dir / name).mkdir()
                self.refresh()
                self.status.text = f'✓ Created {name}/'
            except OSError as e:
                self.status.text = f'✗ {e}'

        self.prompt('New directory', f'Create inside {src.current_dir.name}/:',
                    on_submit=make)

    # ── the viewer: a pushed builder ──────────────────────────────────────
    def view_file(self, path: pathlib.Path):
        self.push_view(lambda: self.build_viewer(path))

    def build_viewer(self, path: pathlib.Path):
        page = self.page(0.85, 0.9, title=path.name)
        page.fill_with(TextView, read_text(path), wrap=False)
        page.footer([('Back', self.pop_view), ('Quit', self.quit)])
        bind_quit(page.view, self.pop_view)           # Esc/q mean back in here
        self.status_bar(page.view, 'Up/Down/PgUp/PgDn scroll · Esc back')
        return page


if __name__ == '__main__':
    Commander().run()

#!/usr/bin/env python3
"""Cookie Commander — a two-pane file manager (the book's capstone, Part IX).

OVERVIEW:
  Two FileBrowser panes side by side, a shared progress bar and status line
  beneath them, and single-key actions: copy or move the selection to the
  other pane, delete with confirmation, make a directory, view a file.

KEYBOARD CONTROLS:
  - Tab: switch panes (the focused pane is the source of every action)
  - Up/Down/Enter: navigate; Enter on a file opens the viewer
  - c: copy selection to the other pane     - m: move it
  - d: delete selection (confirms first)    - n: new directory (prompts)
  - Esc / q: quit (in the viewer they mean back)

DESIGN PATTERNS DEMONSTRATED:
  - Engines and adapters (Ch 28/29): copy_path/move_path/delete_path are pure
    module-level functions — chunked, byte-accurate progress, atomic per-file
    publish (.part + os.replace), BaseException sweep, re-raise the truth
  - run_task with auto-detection: the view's sole ProgressBar is adopted, the
    engines' on_progress is injected, outcomes land on the status label, the
    single-flight guard makes a second 'c' during a copy a safe no-op
  - Composite reuse (Ch 39): FileBrowser panes via fill_with — zero geometry
  - The view stack (Ch 26): the viewer is a pushed builder; Esc pops back
  - columns + shadow-aware stacking (Ch 5/22): no coordinates anywhere
"""
import os
import shutil
import pathlib

from cookieui import (TuiApp, View, FileBrowser, TextView, ProgressBar, Label,
                      bind_key, bind_quit, stack_below)
from cookieui.core.event import KeyType


# ── Domain logic — pure, no UI, no threads ───────────────────────────────────

def _files_under(src: pathlib.Path, dst: pathlib.Path):
    """(source file, destination file) pairs for a file or a whole tree."""
    if src.is_file():
        return [(src, dst)]
    return [(p, dst / p.relative_to(src))
            for p in sorted(src.rglob('*')) if p.is_file()]


def copy_path(src: pathlib.Path, dst: pathlib.Path, on_progress) -> int:
    """Copy a file or directory tree, reporting byte-accurate progress.

    Each file is published atomically (.part then os.replace); any failure
    sweeps the stray .part and re-raises — what an error looks like is the
    adapter's decision. Returns the bytes copied.
    """
    pairs = _files_under(src, dst)
    total = sum(s.stat().st_size for s, _ in pairs) or 1
    done = 0
    for s, d in pairs:
        d.parent.mkdir(parents=True, exist_ok=True)
        part = d.with_name(d.name + '.part')
        try:
            with open(s, 'rb') as fin, open(part, 'wb') as fout:
                while chunk := fin.read(256 * 1024):
                    fout.write(chunk)
                    done += len(chunk)
                    on_progress(done / total)
            os.replace(part, d)
        except BaseException:
            part.unlink(missing_ok=True)
            raise
    if src.is_dir() and not pairs:                 # an empty directory still copies
        dst.mkdir(parents=True, exist_ok=True)
    on_progress(1.0)
    return done


def move_path(src: pathlib.Path, dst: pathlib.Path, on_progress) -> int:
    """Move: instant rename on the same filesystem, copy + delete across."""
    try:
        os.replace(src, dst)
        on_progress(1.0)
        return 0
    except OSError:                                # crossing filesystems
        n = copy_path(src, dst, on_progress)
        delete_path(src, on_progress)
        return n


def delete_path(path: pathlib.Path, on_progress) -> str:
    """Delete a file or tree. Returns the name, for the outcome message."""
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    on_progress(1.0)
    return path.name


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
        lwin, rwin = self.columns(view, 2, height=0.72, y=1)
        self.left = lwin.fill_with(FileBrowser, self.ldir,
                                   on_select=self.view_file,
                                   on_dir_change=lambda p: self._remember(0, p))
        self.right = rwin.fill_with(FileBrowser, self.rdir,
                                    on_select=self.view_file,
                                    on_dir_change=lambda p: self._remember(1, p))

        # shared progress + status, stacked under the panes (shadow-aware)
        span = (rwin.x + rwin.width) - lwin.x
        by = stack_below(lwin.y, lwin.height)
        bar = ProgressBar(lwin.x, by, span)          # run_task adopts the sole bar
        view.add(bar)
        self.status = Label(lwin.x, by + 1, HINT, max_width=span)
        view.add(self.status)

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

        def done(n):
            self.refresh()
            return f'✓ {verb} {sel.name} ({n:,} bytes)' if n else f'✓ {verb} {sel.name}'

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
            def done(name):
                self.refresh()
                return f'✓ Deleted {name}'
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

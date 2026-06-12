#!/usr/bin/env python3
"""CookieUI File Copy — a real chunked file copy driving a ProgressBar.

OVERVIEW:
  The progressdemo.py pattern applied to real work: copy any file with a
  byte-accurate progress bar. The worker thread reads the source in 256 KB
  chunks, writes to a temp file, and publishes atomically (rename) so a
  half-finished copy never masquerades as the real destination.

  Tip: copy something big (a video, an ISO) to actually watch the bar move —
  small files finish within one redraw tick.

KEYBOARD CONTROLS:
  - Tab / Enter: Move between the path fields (Enter in the last field starts the copy)
  - "Copy" button: Start the copy
  - Esc / q: Quit (q still types normally inside the path fields)

HOW TO USE:
  1. Run: python file-copy-progress.py
  2. Type a source file path and a destination (a directory works too —
     the source's name is appended)
  3. Press Enter or click "Copy"; the bar fills as bytes land, the status
     line reports success or the exact error

DESIGN PATTERNS DEMONSTRATED:
  - Domain/UI separation: copy_file(src, dst, on_progress) is a pure module-level
    function — no widgets, no threads, testable standalone. The UI's entire
    dependency surface is the on_progress callback; the engine raises on failure
    (the UI decides what an error looks like) and returns its result (the UI
    decides how to render it)
  - self.run_task(copy_file, src, dst, status=..., running=..., on_done=..., on_error=...):
    the whole worker ceremony in one call — double-start guard, auto-detected bar
    (reset + on_progress wiring), daemon thread, busy cleanup; running= appears only
    if the task actually starts, and on_done/on_error return their status text
  - Byte-accurate progress: on_progress(copied / total) per chunk
  - Atomic publish: write to dst.part, os.replace() at the end — quitting
    mid-copy (daemon thread) can never leave a truncated destination
  - Content-fit window (page with no height), buttons in the flow
"""

import os
import pathlib

from cookieui import TuiApp


# ── Domain logic — pure, no UI, no threads ───────────────────────────────────

def copy_file(src: pathlib.Path, dst: pathlib.Path, on_progress) -> int:
    """Chunked copy with atomic publish.

    Calls on_progress(fraction 0.0–1.0) per chunk, returns the bytes copied, and
    raises on failure (after removing the stray .part). That's the entire contract —
    this function doesn't know widgets or threads exist, so it works unchanged from a
    CLI, a test, or any UI. The progress callback is the UI's whole dependency surface.
    """
    part = dst.with_name(dst.name + '.part')
    try:
        total  = src.stat().st_size or 1
        copied = 0
        with open(src, 'rb') as fin, open(part, 'wb') as fout:
            while chunk := fin.read(256 * 1024):
                fout.write(chunk)
                copied += len(chunk)
                on_progress(copied / total)
        os.replace(part, dst)                     # atomic publish
        return copied
    except BaseException:
        part.unlink(missing_ok=True)              # never leave a stray .part
        raise


# ── UI — wires widgets to the domain function ────────────────────────────────

class FileCopyApp(TuiApp):
    # No __init__/setup needed: run_task carries the busy state

    def build_view(self):
        page = self.page(0.55, title='File Copy', pad_x=0)
        self.src    = page.input(label='Source file', placeholder='/path/to/source')
        self.dst    = page.input(label='Destination', placeholder='/path/to/dest (or a directory)')
        page.progressbar()               # a local concern: run_task auto-detects it
        self.status = page.label('Enter paths, then Copy.')
        page.gap()
        page.buttons([('Copy', self.copy), ('Quit', self.quit)])
        self.dst.on_enter = self.copy    # Enter in the last field submits
        return page

    def copy(self):
        src = pathlib.Path(self.src.value.strip()).expanduser()
        dst = pathlib.Path(self.dst.value.strip()).expanduser()
        if not src.is_file():
            self.status.text = f'✗ Not a file: {src}'
            return
        if dst.is_dir():
            dst = dst / src.name         # copying *into* a directory
        if dst == src:
            self.status.text = '✗ Source and destination are the same file'
            return

        # The UI decides what success and failure look like — as returned text;
        # run_task does the ceremony (guard, auto bar + on_progress wiring, thread,
        # status updates, busy cleanup). running= is shown only if it actually starts.
        self.run_task(copy_file, src, dst, status=self.status,
                      running=f'Copying {src.name} …',
                      on_done=lambda n: f'✓ {n:,} bytes → {dst}',
                      on_error=lambda e: f'✗ {e}')


if __name__ == '__main__':
    FileCopyApp().run()

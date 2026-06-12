#!/usr/bin/env python3
"""Progress bar demo — a bar that fills as a simulated download runs.

Demonstrates the ProgressBar widget: a worker thread just sets `.value` (0.0–1.0) and the
next redraw reflects it — no draw calls, no locking, nothing else to wire.

DESIGN PATTERNS DEMONSTRATED:
  - Domain/UI separation: download(on_progress) is a pure module-level function —
    the UI's entire dependency surface is one callback; the app's work() is a thin
    adapter mapping it onto bar.value
  - self.run_task(download, done='Complete ✓'): one call does the double-start
    guard, auto-detects the view's sole ProgressBar (reset, on_progress wiring,
    filled to 1.0), spawns the worker — and with no status= widget, the BAR IS
    THE STATUS AREA: done= renders centered on the bar face, installer-style.
    The bar stays a *local* in build_view (nothing references it)
  - The naming rule (library-wide): a bare noun is a VALUE (done='…', error='…',
    like confirm's yes='Yes'), an on_-noun is a CALLABLE (on_done=fn for behavior
    or dynamic text, like confirm's on_yes)
  - Content-fit window: page(0.45) with no height — label + bar + buttons, wrapped
  - Buttons in the flow (lay.buttons) — the content-fit style; no footer pinning
"""
import time

from cookieui import TuiApp


# ── Domain logic — pure, no UI, no threads ───────────────────────────────────

def download(on_progress) -> None:
    """Simulated download — stands in for any chunked operation. Reports through the
    on_progress(0.0–1.0) callback, which is the UI's entire dependency surface.
    (For the same shape on real I/O, see file-copy-progress.py.)"""
    for i in range(101):
        on_progress(i / 100)
        time.sleep(0.03)


# ── UI — wires widgets to the domain function ────────────────────────────────

class ProgressDemo(TuiApp):
    # No __init__ needed: TuiApp pushes build_view automatically (AUTO_VIEW)

    def build_view(self):
        # One object to talk to: page delegates to its layout/window/view
        page = self.page(0.45, title='Progress', pad_x=0)
        page.label('Downloading…')
        page.progressbar()       # a local concern: run_task finds the view's only bar

        page.gap()
        page.buttons([('Start', self.start), ('Quit', self.quit)])
        return page

    def start(self):
        # One line, no lambdas, no status label: the bar is auto-detected AND is its
        # own status area — done= renders centered on the bar face, installer-style.
        # (Dynamic text or behavior? on_done=lambda n: f'✓ {n} files'.)
        self.run_task(download, done='Complete ✓')


if __name__ == '__main__':
    ProgressDemo().run()

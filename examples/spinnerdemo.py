#!/usr/bin/env python3
"""Spinner demo — pick a spinner style, press Run, and watch it work.

Demonstrates the Spinner widget and its named styles (dots, line, arc, circle, square,
arrow, pulse): choose one in the radio group — the spinner switches look instantly, even
mid-run — then Run starts a fake 3s task with the spinner shown for the duration.

DESIGN PATTERNS DEMONSTRATED:
  - Spinner styles: rows carry each style's frame cycle as the value
    ((name, frames) pairs); rg.on_change mutates spin.frames and the very next
    tick animates the new look — live mutation, no rebuild, works mid-run
  - Domain/UI separation: long_task() is a pure module-level function that returns
    its result — it knows nothing about widgets or threads; the app's work() is a
    thin adapter that renders the return value
  - self.run_task(long_task, status=self.status, running='Working…'): one line —
    the view's sole Spinner is auto-detected (shown during, hidden after), and with
    no on_done the engine's return value becomes the status text; failures would
    land on the status as 'Error: …'
  - Content-fit window: page(0.4) with no height — spinner + status + buttons, wrapped
  - Buttons in the flow (lay.buttons) — the content-fit style; no footer pinning
"""
import time

from cookieui import TuiApp, Spinner


# ── Domain logic — pure, no UI, no threads ───────────────────────────────────

def long_task() -> str:
    """Stand-in for real work (a network call, a computation). Returns its result —
    the UI decides how to display it. Knows nothing about widgets or threads."""
    time.sleep(3)
    return 'Done ✓  (press Run again)'


# ── UI — wires widgets to the domain function ────────────────────────────────

class SpinnerDemo(TuiApp):
    # No __init__ needed: TuiApp pushes build_view automatically (AUTO_VIEW)

    def build_view(self):
        # One object to talk to: page delegates to its layout/window/view
        page = self.page(0.4, title='Spinner', pad_x=0)
        spin = page.spinner(label='Working…')   # a local: run_task finds the view's
        spin.visible = False                    # only Spinner and shows/hides it
        self.status = page.label('Idle — press Run to start a task')
        page.gap()

        # Live style switch: rows carry the frame cycle as the value; the on_change
        # callback mutates spin.frames and the very next tick animates the new look
        page.label('Style:', dim=True)
        rg = page.radio_group([(name, frames) for name, frames in Spinner.STYLES.items()])
        rg.on_change = lambda i: setattr(spin, 'frames', rg.selected_value)

        page.gap()
        page.buttons([('Run', self.start), ('Quit', self.quit)])
        return page

    def start(self):
        # One line: spinner auto-detected; with no on_done, the engine's return
        # value *is* the status text — engines that return their message need nothing
        self.run_task(long_task, status=self.status, running='Working…')


if __name__ == '__main__':
    SpinnerDemo().run()

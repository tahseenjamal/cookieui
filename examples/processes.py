#!/usr/bin/env python3
"""CookieUI Process Viewer — live-filtered process table sorted by CPU.

OVERVIEW:
  A `top`-flavoured tool built on the Table widget: every process with PID, CPU%,
  MEM%, and command, sorted by CPU. Type to filter, Enter for details, 'r' to
  refresh.

KEYBOARD CONTROLS:
  - Type in "Filter": narrows the table as you type (matches the command name)
  - Arrow Up/Down, PgUp/PgDn, Home/End: move through the table
  - Enter (on a row) / "Info": details dialog for the selected process
  - r / "Refresh": re-run ps and re-render (keeps the current filter)
  - Esc / q: quit ('q' still types in the filter field)

HOW TO USE:
  1. Run: python processes.py
  2. The table fills with processes, hottest CPU first
  3. Type e.g. "python" to filter; press Enter on a row for details

DESIGN PATTERNS DEMONSTRATED:
  - Table: column specs with weights and right-aligned numeric columns
    (('PID', 1, '>'), ..., ('Command', 5)) — widths derived, never counted;
    cells passed untrimmed (the table clips per column at draw time)
  - Value-carrying rows: each row carries its process tuple; callbacks read
    table.selected_value — no parallel array
  - Sorting is data logic, not widget logic: list_procs() returns CPU-sorted
    rows; the table just renders them
  - Domain/UI separation: list_procs() is pure (subprocess → tuples; raises on
    failure); the app only wires widgets to it
  - Live filtering: flt.on_change re-renders the rows (envbrowser's pattern,
    on a Table)
  - page.table() with no size — fills down to the footer buttons
  - Widgets stay locals (tbl, flt: closure-only); the process list is data → self
"""

import subprocess

from cookieui import TuiApp, bind_enter_action, bind_key
from cookieui.core.event import KeyType


# ── Domain logic — pure, no UI, no threads ───────────────────────────────────

def list_procs():
    """Every process as (pid, cpu, mem, command), hottest CPU first. Raises if ps
    fails — the UI decides what an error looks like."""
    out = subprocess.check_output(['ps', '-axo', 'pid=,pcpu=,pmem=,comm='], text=True)
    procs = []
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4:
            pid, cpu, mem, cmd = parts
            procs.append((int(pid), float(cpu), float(mem), cmd))
    procs.sort(key=lambda p: (p[1], p[2]), reverse=True)   # sorting is data logic
    return procs


# ── UI — wires widgets to the domain function ────────────────────────────────

class Processes(TuiApp):
    def setup(self):
        self._procs = []                      # data on self — survives resize rebuilds

    def build_view(self):
        page = self.page(0.85, 0.85, title='Processes')
        flt = page.input(label='Filter', placeholder='type to filter by command')
        tbl = page.table([('PID', 1, '>'), ('CPU%', 1, '>'),
                          ('MEM%', 1, '>'), ('Command', 5)])   # fills to the footer

        def render(query=''):
            q = query.lower()
            tbl.rows = [((p[0], f'{p[1]:.1f}', f'{p[2]:.1f}', p[3]), p)
                        for p in self._procs if q in p[3].lower()]
            tbl.selected_index = 0

        def refresh():
            self._procs = list_procs()
            render(flt.value)

        def details():
            p = tbl.selected_value
            if p:
                self.show_message(f'PID {p[0]}',
                                  f'  CPU {p[1]:.1f}%    MEM {p[2]:.1f}%\n\n  {p[3]}')

        flt.on_change = render                # live filter, per edit
        bind_enter_action(tbl, details)       # Enter on a row = details
        page.footer([('Info', details), ('Refresh', refresh), ('Quit', self.quit)])
        bind_key(page.view, KeyType.CHAR, refresh, char='r')
        self.status_bar(page.view, 'Type to filter  Enter info  r refresh  Esc quit')

        refresh()                             # initial load
        return page


if __name__ == '__main__':
    Processes().run()

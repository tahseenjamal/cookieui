#!/usr/bin/env python3
"""CookieUI Environment Variable Browser — Search and view environment variables in real-time.

OVERVIEW:
  A utility to explore environment variables with live search filtering. Useful for debugging
  shell configuration, understanding environment setup, and investigating system variables.

FEATURES:
  - Live search: Type in the "Search" field to filter variables by name or value
  - Results display: rows clip at draw time — long values never overflow the border
  - Value viewer: Click "View" to see full variable value with word-wrapping
  - Real-time filtering: Updates list as you type (no need to press Enter)

KEYBOARD CONTROLS:
  - Type in search field: Filters variables as you type
  - Tab: Move focus between search, listbox, buttons
  - Arrow Up/Down: Navigate listbox
  - Enter: View selected variable's full value
  - Esc/q: Quit application

HOW TO USE:
  1. Run: python envbrowser.py
  2. Type in the "Search" field (e.g., "PATH", "HOME", "PYTHON")
  3. Results update automatically as you type
  4. Select an entry and press Enter or click "View"
  5. Dialog shows full variable value with word-wrapping
  6. Click "OK" to close dialog and continue filtering

DESIGN PATTERNS DEMONSTRATED:
  - Sizing model: page(0.75, 0.8) — fractions of the terminal, FIXED height because
    the result list fills the window
  - lay.listbox() with no size — fills from below the search field to the footer
  - Value-carrying rows: items are (label, (key, value)) pairs; the View callback
    reads lb.selected_value — no parallel array indexed by selection
  - Live filtering: inp.on_change = refresh — fires with the new text after every
    edit (typing, backspace, delete); no key handling needed at all
  - Listbox rows clip at draw time — values are passed untrimmed
  - footer_buttons + bind_enter_action (Enter on a row = View)
"""

import os

# Run from anywhere (e.g. `python envbrowser.py`): put the repo root on the import path.
import sys, pathlib
from cookieui import TuiApp, bind_enter_action


ALL_VARS = sorted(os.environ.items(), key=lambda kv: kv[0].lower())


def filtered(query):
    q = query.strip().lower()
    if not q:
        return ALL_VARS
    return [(k, v) for k, v in ALL_VARS
            if q in k.lower() or q in v.lower()]


class EnvBrowser(TuiApp):
    """Environment variable browser application.

    No __init__ needed: TuiApp pushes build_view automatically (AUTO_VIEW).
    """

    def build_view(self):
        # Fractional size (¾ wide, 0.8 tall): fixed height because the list fills it
        page = self.page(0.75, 0.8, title='Environment Variables', pad_x=0)
        inp = page.input(label='Search')
        lb  = page.listbox()                # no height: auto-fills down to the footer buttons

        def refresh(query=''):
            # Listbox clips rows at draw time — no manual width slicing needed
            lb.items = [(f'{k}={v}', (k, v)) for k, v in filtered(query)]
            lb.selected_index = 0     # reset to top on new query (clamps + scrolls)

        def do_view():
            value = lb.selected_value
            if value is None:
                return
            key, val = value
            lines = [val[i:i+60] for i in range(0, max(1, len(val)), 60)]
            msg = f'  {key}\n\n' + '\n'.join(f'  {l}' for l in lines[:10])
            if len(lines) > 10:
                msg += f'\n  ... ({len(val)} chars)'
            self.show_message('Value', msg)

        refresh()
        inp.on_change = refresh             # live filter: fires with the new text per edit
        page.footer([('View', do_view), ('Quit', self.quit)])
        bind_enter_action(lb, do_view)      # Enter = view
        self.status_bar(page.view, f'Type to filter  Enter view  Tab focus  |  {len(ALL_VARS)} vars')
        return page


if __name__ == '__main__':
    EnvBrowser().run()

#!/usr/bin/env python3
"""CookieUI Quick Dialogs — the whiptail quartet, one line each.

OVERVIEW:
  CookieUI descends from Newt (the library behind whiptail), and these four TuiApp
  methods are its whiptail equivalents — each a single call, each auto-sizing,
  auto-centering, and auto-closing:

    self.show_message(title, message)                  # ── like `whiptail --msgbox`
    self.confirm(title, message, on_yes)               # ── like `whiptail --yesno`
    self.prompt(title, message, on_submit=fn)          # ── like `whiptail --inputbox`
    self.choose(title, items, on_pick=fn)              # ── like `whiptail --menu`

  This demo wires one button to each. The label at the top shows the last result —
  callbacks receive the entered text (prompt) or the picked value (choose).

KEYBOARD CONTROLS:
  - Tab / Arrow keys: Move between buttons
  - Enter: Press the focused button; submit a prompt; pick a list row
  - Esc: Cancel the open dialog (or quit the app)

DESIGN PATTERNS DEMONSTRATED:
  - Content-fit window: page(0.5) with no height — label + two button rows, wrapped
  - prompt(): on_submit receives the entered string; password=True masks input
  - choose(): items as (label, value) pairs — on_pick receives the paired value
  - confirm(): on_yes runs only on the Yes button; Escape means No
  - Dialogs auto-close before your callback runs — never call close_dialog()
  - Builder-based view → automatic rebuild on terminal resize
"""


from cookieui import TuiApp


FLAVOURS = [
    ('Vanilla',    'vanilla'),
    ('Chocolate',  'chocolate'),
    ('Strawberry', 'strawberry'),
    ('Pistachio',  'pistachio'),
    ('Cookie dough — obviously', 'cookie-dough'),
]


class QuickDialogs(TuiApp):
    # No __init__ needed: TuiApp pushes build_view automatically (AUTO_VIEW)

    def build_view(self):
        # One object to talk to: page delegates to its layout/window/view
        page = self.page(0.5, title='Quick Dialogs', pad_x=0)

        result = page.label('Press a button — the result lands here.')
        page.gap()

        # Dialog callbacks just mutate the label — the next frame shows it.
        def agreed():    result.text = 'Agreed ✓'
        def disagreed(): result.text = 'Disagreed ✗'
        def greet(name): result.text = f'Hello, {name}!'
        def picked(v):   result.text = f'Picked: {v}'

        page.buttons([
            ('Message', lambda: self.show_message('Hello', 'A one-line message box.')),
            ('Confirm', lambda: self.confirm('Confirm', 'Cookies are the best food?',
                                             agreed, on_no=disagreed)),
        ])
        page.buttons([
            ('Prompt', lambda: self.prompt('Your Name', 'Who is asking?',
                                           on_submit=greet, placeholder='type here')),
            ('Choose', lambda: self.choose('Ice Cream', FLAVOURS,
                                           on_pick=picked, message='Pick a flavour')),
        ])
        return page


if __name__ == '__main__':
    QuickDialogs().run()

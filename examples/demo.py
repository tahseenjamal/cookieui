#!/usr/bin/env python3
"""CookieUI Demo Application — Multi-screen login flow with settings and dialogs.

OVERVIEW:
  This application demonstrates a complete multi-screen TUI workflow:
  1. Login screen: Username/Password inputs with Sign In and Quit buttons
  2. Settings screen: 2-column layout with preferences and protocol selection
  3. Modal dialogs: Confirmation and message dialogs

FEATURES DEMONSTRATED:
  - Class-based TuiApp architecture (extend TuiApp instead of using global app)
  - Multi-screen navigation (push_view/pop_view/replace_view)
  - self.columns(view, 2) — side-by-side windows with derived widths, content-fit heights
  - VerticalLayout for widget stacking (auto-increment Y positions)
  - TextInput with password masking
  - Checkbox and RadioGroup widgets
  - Modal dialogs with callbacks
  - Custom key handlers (Enter to submit, Esc to quit)
  - Status bar with keyboard shortcuts

KEYBOARD CONTROLS:
  - Tab/Shift-Tab: Focus next/previous widget (global cycle)
  - Arrow keys: Navigate between window children
  - Enter: Activate buttons, submit text fields
  - Space: Toggle checkboxes, cycle radio buttons
  - Esc / q: Quit (with confirmation)

HOW IT WORKS:
  1. Start with login_view (username/password inputs)
  2. Click "Sign In" → shows settings_view (if username not empty)
  3. Settings window has two columns:
     - Left: Preferences (checkboxes)
     - Right: Protocol selection (radio group)
  4. Buttons:
     - Save: Shows confirmation with current settings
     - Back: Returns to login
     - Discard: Confirmation dialog with custom button labels (Discard / Keep Editing)
  5. Esc/q from any screen shows quit confirmation

DESIGN PATTERNS USED:
  - Zero geometry numbers: page(0.5) is a fraction of the terminal, no height means
    the window wraps its content; columns(view, 2) derives both windows' widths
  - lay.buttons([('Sign In', do_login), ...]) — labels and callbacks together
  - lay.checkboxes([...]) — a checkbox batch in one call
  - buttons_below(view, win, [...]) — floating button row under a window (shadow-aware,
    re-anchored automatically once the content-fit window knows its height)
  - Enter in a TextInput without on_enter moves to the next field automatically;
    only the last field sets on_enter (submit)
  - Zero __init__: TuiApp auto-pushes build_view (AUTO_VIEW) as a builder, so every
    screen rebuilds and re-centers automatically when the terminal is resized
  - replace_view(lambda: self.build_settings_view(name)) — capture args, pass a builder
"""

# Run from anywhere (e.g. `python demo.py`): put the repo root on the import path.
import sys, pathlib
from cookieui import View, TuiApp, buttons_below, bind_quit


PROTOCOLS = [
    'SMPP 3.4 — direct SMSC',
    'HTTP gateway (REST)',
    'NATS JetStream relay',
    'SS7 TCAP / MAP',
    'SIGTRAN M3UA',
    'Diameter Gy/Ro',
]


class Demo(TuiApp):
    """Demo application with login → settings → dialogs flow."""

    AUTO_QUIT = False   # custom quit: login confirms before quitting, settings goes back

    # No __init__ needed: TuiApp auto-pushes build_view (the login screen);
    # build_settings_view is reached via replace_view.

    def build_view(self):
        # No cell counts: width is half the terminal, height wraps the content
        page = self.page(0.5, title='Sign In', pad_x=0)

        usr = page.input(label='Username', placeholder='user')  # Enter → next field (automatic)
        pwd = page.input(label='Password', placeholder='****', password=True)
        page.gap(1)

        def do_login():
            name = usr.value.strip()
            if name:
                # Capture the argument, pass the builder → settings re-centers on resize
                self.replace_view(lambda: self.build_settings_view(name))
            else:
                self.show_message('Missing Username', 'Please enter a username.')

        def do_quit():
            self.confirm('Quit?', 'Are you sure?', self.quit)

        pwd.on_enter = do_login                          # Enter on the last field → submit
        page.buttons([('Sign In', do_login), ('Quit', do_quit)])

        self.status_bar(page.view, 'Tab focus   Enter submit   Esc quit')
        bind_quit(page.view, do_quit)                    # custom: confirm before quit
        return page

    def build_settings_view(self, username: str) -> View:
        view = View()
        # Two equal columns — widths derived from the terminal, heights wrap the content
        left, right = self.columns(view, 2, titles=['Preferences', 'Protocol'])

        prefs = left.layout().checkboxes([
            ('Enable notifications', True),
            ('Dark mode', True),
            'Compact view',
            ('Auto-reconnect', True),
            'Verbose logging',
        ])
        proto_radio = right.layout().radio_group(PROTOCOLS, selected=0)

        def do_save():
            enabled = [p.label for p in prefs if p.checked]
            self.show_message('Settings Saved',
                              f'User: {username}\n'
                              f'Protocol: {proto_radio.selected}\n'
                              f'Enabled: {len(enabled)} options')

        def do_back():
            self.replace_view(self.build_view)

        def do_discard():
            self.confirm('Unsaved Changes', 'Discard and go back?',
                         do_back, yes='Discard', no='Keep Editing')

        # Action buttons float just below the left window (shadow-aware, one call)
        buttons_below(view, left, [('Save', do_save), ('Back', do_back),
                                   ('Discard', do_discard)])

        self.status_bar(view, f'Settings ({username})  Tab focus  Space toggle')
        bind_quit(view, do_back)            # custom: Esc/q goes back, not quit
        return view


if __name__ == '__main__':
    Demo().run()

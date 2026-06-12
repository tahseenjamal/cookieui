#!/usr/bin/env python3
"""Theme gallery — every shipped look, switched live.

Pick a theme in the radio group and the whole app re-renders on the next
frame: NEWT (the signature), MOCHA (palette swap), OUTLINE (wireframe — no filled
panels, rounded line work only), FLAT (construction-level design —
FlatChrome draws borderless panels with rule-titles and block buttons).

DESIGN PATTERNS DEMONSTRATED:
  - The three-layer design model (TEMPLATING.md): colors → tokens → chrome.
    All four looks run the SAME app code — the theme carries the whole design.
  - Value-carrying RadioGroup: options are (label, Theme) pairs; the callback
    reads rg.selected_value — no parallel list (PATTERNS.md).
  - Runtime theme switch: assign `self._app.theme` and the next redraw uses it
    (the run loop redraws every tick; mutate, never call draw).
  - The widgets below are just a sampler so every kind of chrome is visible:
    frames, scrollbar, entry, brackets, progress, buttons, dialog.
"""

from cookieui import TuiApp, NEWT, MOCHA, OUTLINE, FLAT

THEMES = [('Newt — the signature', NEWT),
          ('Mocha — palette swap', MOCHA),
          ('Outline — wireframe, rounded', OUTLINE),
          ('Flat — borderless chrome', FLAT)]


class ThemeGallery(TuiApp):
    # No __init__ needed: TuiApp pushes build_view automatically (AUTO_VIEW)

    def build_view(self):
        page = self.page(0.62, 0.85, title='Theme Gallery')

        rg = page.radio_group(THEMES)

        def switch(_idx):
            self._app.theme = rg.selected_value      # next frame renders in it
        rg.on_change = switch

        page.gap()
        self.inp = page.input(label='Entry', placeholder='type something')
        page.checkbox('A checkbox', checked=True)
        bar = page.progressbar()
        bar.value = 0.42
        lb = page.listbox()                          # fills to the footer
        lb.items = [f'list row {i}' for i in range(20)]

        page.footer([
            ('Dialog', lambda: self.show_message('Dialog', 'Same dialog, current theme.')),
            ('Quit', self.quit),
        ])
        self.status_bar(page.view, 'Up/Down pick a theme — the whole app re-renders live')
        return page


if __name__ == '__main__':
    ThemeGallery().run()

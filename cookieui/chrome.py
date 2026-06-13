"""The chrome: how surfaces are *constructed* — borders, titles, scrollbars,
button faces, shadows. One pluggable object owns every box the library draws.

The design model has three layers (see TEMPLATING.md):
  1. Theme **colors** — palette swap (NEWT vs MOCHA vs FLAT).
  2. Theme **tokens** — the glyphs and switches design is made of (border sets,
     `[x]` brackets, progress fill pair, entry fill, shadows on/off). OUTLINE
     is a colors-and-tokens design: no filled panels, rounded line work only.
  3. The **Chrome** — this class. Subclass it to change construction itself:
     what a frame *is*, how a title sits, what a button face looks like.
     `FlatChrome` below is the worked example (borderless, rule-under-title).

Widgets never hardcode chrome: they call ``theme.chrome.frame(...)`` etc., so a
theme carries its whole look — colors, tokens, and construction — in one value.
Chrome methods draw *boxes*; widget content (list rows, table cells, entry
text) stays in the widgets, so a custom chrome can never break behavior.
"""


class Chrome:
    """The classic Newt construction: rounded frames, centred titles, drop
    shadows, ▲░█▼ scrollbars, bordered 3-row buttons."""

    # ── shared frame for boxed widgets (Listbox, TextView, Table) ─────────

    def frame(self, screen, theme, x, y, width, height, *,
              focused=False, title='', bg=None):
        """Border with an optional title. Returns the bg used for the interior."""
        t   = theme
        bg  = bg if bg is not None else t.surface
        bfg = t.border_focused if focused else t.border

        screen.put(x,             y,              t.tl, fg=bfg, bg=bg)
        screen.put(x + width - 1, y,              t.tr, fg=bfg, bg=bg)
        screen.put(x,             y + height - 1, t.bl, fg=bfg, bg=bg)
        screen.put(x + width - 1, y + height - 1, t.br, fg=bfg, bg=bg)
        for col in range(1, width - 1):
            screen.put(x + col, y,              t.h, fg=bfg, bg=bg)
            screen.put(x + col, y + height - 1, t.h, fg=bfg, bg=bg)
        for row in range(1, height - 1):
            screen.put(x,             y + row, t.v, fg=bfg, bg=bg)
            screen.put(x + width - 1, y + row, t.v, fg=bfg, bg=bg)

        if title:
            self._title(screen, theme, x, y, width, f' {title} ',
                        fg=t.title_fg, bg=bg, brackets=(t.title_l, t.title_r),
                        border_fg=bfg)
        return bg

    def scrollbar(self, screen, theme, x_col, y_top, inner_h, total, scroll, *,
                  bg=None):
        """Scrollbar in column `x_col`, rows y_top .. y_top+inner_h-1; glyphs
        come from the theme tokens (sc_up/sc_down/sc_track/sc_thumb)."""
        t  = theme
        bg = bg if bg is not None else t.surface

        track_h = inner_h - 2                   # rows between the arrows
        if track_h > 0 and total > 0:
            thumb = int(scroll * track_h // max(1, total - inner_h)) + 1
            thumb = max(1, min(track_h, thumb))
        else:
            thumb = 1

        screen.put(x_col, y_top, t.sc_up, fg=t.text, bg=bg)
        for i in range(1, inner_h - 1):
            glyph = t.sc_thumb if i == thumb else t.sc_track
            screen.put(x_col, y_top + i, glyph, fg=t.text, bg=bg)
        screen.put(x_col, y_top + inner_h - 1, t.sc_down, fg=t.text, bg=bg)

    # ── containers ─────────────────────────────────────────────────────────

    def window_frame(self, screen, theme, x, y, width, height, *,
                     title='', icon=''):
        """A Window's surface: fill + border + title. Children draw on top."""
        t   = theme
        bg  = t.surface
        bfg = t.border
        screen.fill(x, y, width, height, bg=bg)

        screen.put(x,             y,              t.tl, fg=bfg, bg=bg)
        screen.put(x + width - 1, y,              t.tr, fg=bfg, bg=bg)
        screen.put(x,             y + height - 1, t.bl, fg=bfg, bg=bg)
        screen.put(x + width - 1, y + height - 1, t.br, fg=bfg, bg=bg)
        for col in range(1, width - 1):
            screen.put(x + col, y,              t.h, fg=bfg, bg=bg)
            screen.put(x + col, y + height - 1, t.h, fg=bfg, bg=bg)
        for row in range(1, height - 1):
            screen.put(x,             y + row, t.v, fg=bfg, bg=bg)
            screen.put(x + width - 1, y + row, t.v, fg=bfg, bg=bg)

        if title:
            icon_part = f'{icon} ' if icon else ''
            self._title(screen, theme, x, y, width, f' {icon_part}{title} ',
                        fg=t.title_fg, bg=bg, brackets=(t.title_l, t.title_r),
                        border_fg=bfg)
        return bg

    def dialog_frame(self, screen, theme, x, y, width, height, *,
                     title='', icon=''):
        """A Dialog's surface: raised fill + elevated (double-line) border + title."""
        t   = theme
        bg  = t.surface_raised
        bfg = t.border
        screen.fill(x, y, width, height, bg=bg)

        screen.put(x,             y,              t.etl, fg=bfg, bg=bg)
        screen.put(x + width - 1, y,              t.etr, fg=bfg, bg=bg)
        screen.put(x,             y + height - 1, t.ebl, fg=bfg, bg=bg)
        screen.put(x + width - 1, y + height - 1, t.ebr, fg=bfg, bg=bg)
        for col in range(1, width - 1):
            screen.put(x + col, y,              t.eh, fg=bfg, bg=bg)
            screen.put(x + col, y + height - 1, t.eh, fg=bfg, bg=bg)
        for row in range(1, height - 1):
            screen.put(x,             y + row, t.ev, fg=bfg, bg=bg)
            screen.put(x + width - 1, y + row, t.ev, fg=bfg, bg=bg)

        if title:
            ic    = f'{icon} ' if icon else ''
            label = f' {ic}{title} '[:max(1, width - 2)]
            self._title(screen, theme, x, y, width, label, fg=t.title_fg, bg=bg,
                        brackets=(t.etitle_l, t.etitle_r), border_fg=bfg)
        return bg

    # ── controls ───────────────────────────────────────────────────────────

    def button_face(self, screen, theme, x, y, width, content, *, focused=False):
        """A 3-row button face at (x, y). `content` is the padded label text.
        The caller (Button) owns position shifting, the pressed offset, and
        the shadow — the face only draws the three rows."""
        t         = theme
        bg        = t.button_bg
        border_fg = t.button_border
        if focused:
            label_bg, label_fg = t.button_fg, t.button_bg
        else:
            label_bg, label_fg = bg, t.button_fg

        label_width   = len(content)
        padding_total = width - 2 - label_width
        left_pad      = max(0, padding_total // 2)

        screen.put(x,             y, t.btl, fg=border_fg, bg=bg)
        for col in range(1, width - 1):
            screen.put(x + col,   y, t.bh, fg=border_fg, bg=bg)
        screen.put(x + width - 1, y, t.btr, fg=border_fg, bg=bg)

        screen.put(x, y + 1, t.bv, fg=border_fg, bg=bg)
        for col in range(1, 1 + left_pad):
            screen.put(x + col, y + 1, ' ', fg=label_fg, bg=label_bg)
        screen.write(x + 1 + left_pad, y + 1, content,
                     fg=label_fg, bg=label_bg, bold=False)
        for col in range(1 + left_pad + label_width, width - 1):
            screen.put(x + col, y + 1, ' ', fg=label_fg, bg=label_bg)
        screen.put(x + width - 1, y + 1, t.bv, fg=border_fg, bg=bg)

        screen.put(x,             y + 2, t.bbl, fg=border_fg, bg=bg)
        for col in range(1, width - 1):
            screen.put(x + col,   y + 2, t.bh, fg=border_fg, bg=bg)
        screen.put(x + width - 1, y + 2, t.bbr, fg=border_fg, bg=bg)

    # ── shadow ─────────────────────────────────────────────────────────────

    def shadow(self, screen, theme, x, y, width, height, *,
               max_x=None, max_y=None):
        """Drop shadow below/right of a surface — the theme's master switch
        (`shadow_on`) and color (`shadow_color`) decide; widgets never check."""
        if not theme.shadow_on:
            return
        screen.cast_shadow(x, y, width, height, color=theme.shadow_color,
                           max_x=max_x, max_y=max_y)

    # ── helpers ────────────────────────────────────────────────────────────

    def _title(self, screen, theme, x, y, width, label, *, fg, bg,
               brackets=None, border_fg=None):
        """Place a title on a top edge, flanked by the theme's title brackets (the
        classic Newt ┤ … ├ cut into the border), honoring the title_align token.
        The brackets are part of the border, so they take `border_fg`; only the
        title text takes `fg`."""
        bl, br = brackets or ('', '')
        total  = len(bl) + len(label) + len(br)
        tx = x + 2 if theme.title_align == 'left' else x + max(1, (width - total) // 2)
        bfg = border_fg if border_fg is not None else fg
        cx = tx
        if bl:
            screen.put(cx, y, bl, fg=bfg, bg=bg); cx += 1
        screen.write(cx, y, label, fg=fg, bg=bg, bold=True); cx += len(label)
        if br:
            screen.put(cx, y, br, fg=bfg, bg=bg)


class FlatChrome(Chrome):
    """Borderless construction: panels are color fields, titles sit on a thin
    rule, buttons are solid blocks. Same geometry as the classic chrome (every
    frame still reserves its 1-cell edge), so layout math never changes — only
    what gets drawn there. The worked example for TEMPLATING.md layer 3."""

    def _rule_title(self, screen, theme, x, y, width, title, *, focused, bg):
        t   = theme
        col = t.border_focused if focused else t.border
        for cx in range(x, x + width):
            screen.put(cx, y, t.h, fg=col, bg=bg)
        if title:
            label = f' {title} '
            fg = t.border_focused if focused else t.title_fg
            screen.write(x + 1, y, label[:max(1, width - 2)], fg=fg, bg=bg, bold=True)

    def frame(self, screen, theme, x, y, width, height, *,
              focused=False, title='', bg=None):
        bg = bg if bg is not None else theme.surface
        screen.fill(x, y, width, height, bg=bg)
        self._rule_title(screen, theme, x, y, width, title, focused=focused, bg=bg)
        return bg

    def window_frame(self, screen, theme, x, y, width, height, *,
                     title='', icon=''):
        bg = theme.surface
        screen.fill(x, y, width, height, bg=bg)
        icon_part = f'{icon} ' if icon else ''
        self._rule_title(screen, theme, x, y, width,
                         f'{icon_part}{title}'.strip(), focused=False, bg=bg)
        return bg

    def dialog_frame(self, screen, theme, x, y, width, height, *,
                     title='', icon=''):
        bg = theme.surface_raised
        screen.fill(x, y, width, height, bg=bg)
        ic = f'{icon} ' if icon else ''
        self._rule_title(screen, theme, x, y, width,
                         f'{ic}{title}'.strip(), focused=True, bg=bg)
        return bg

    def button_face(self, screen, theme, x, y, width, content, *, focused=False):
        # A flat button signals focus with its fill: idle buttons recede into a
        # dark block (btn_bg/btn_fg), the focused one lights up in the accent
        # (btn_focused_bg/btn_focused_fg) — the compact-button color slots.
        t = theme
        if focused:
            bg, fg = t.btn_focused_bg, t.btn_focused_fg
        else:
            bg, fg = t.btn_bg, t.btn_fg
        screen.fill(x, y, width, 3, bg=bg)
        label_width = len(content)
        lx = x + max(1, (width - label_width) // 2)
        screen.write(lx, y + 1, content, fg=fg, bg=bg, bold=focused)

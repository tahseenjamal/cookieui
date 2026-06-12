# TEMPLATING — design your own look

CookieUI decouples **what widgets do** from **how they are drawn**. A theme is not
just colors: it carries every design decision, in three layers, and you can change
any layer without touching app code. The proof: `python examples/themedemo.py` runs
one app in four completely different looks, live.

```
Layer 1  COLORS   the palette                     Theme color fields
Layer 2  TOKENS   the glyphs design is made of    Theme token fields ([x], █░, ╭╮, _)
Layer 3  CHROME   construction itself             theme.chrome (a Chrome subclass)
```

Rule of thumb: **recolor → layer 1, re-skin → layer 2, redesign → layer 3.**
Behavior (keys, focus, callbacks) is never in any layer — a theme cannot break an app.

## The shipped looks (read these as worked examples)

| Theme | What it demonstrates | Layers used |
|---|---|---|
| `NEWT` | the signature — blue sea, beige windows, shadows | defaults |
| `MOCHA` | dark palette + dialog border glyphs; shadows off (dark themes go flat — shadow tints read as mud on a dark ground) | 1 + 2 |
| `OUTLINE` | wireframe: no filled panels (every surface is the background), rounded corners everywhere — buttons included — line-track scrollbar, no shadows | 1 + 2 |
| `FLAT` | borderless: panels are color fields, titles sit on a rule, buttons are solid blocks | 1 + 2 + 3 |

All are importable from `cookieui` and switchable at runtime: assign
`self._app.theme = FLAT` and the next frame renders in it (mutate, never call draw).

## Layer 1 — a palette in ten lines

`Theme` is a dataclass; `dataclasses.replace` is the theming tool. Start from the
shipped look closest to yours and override:

```python
from dataclasses import replace
from cookieui import NEWT

OCEAN = replace(
    NEWT,
    bg      = (12, 60, 90),
    surface = (222, 234, 238),
    accent  = (0, 120, 160),
    button_bg = (0, 120, 160),
)

class MyApp(TuiApp):
    def __init__(self):
        super().__init__(theme=OCEAN)
```

## Layer 2 — the design tokens

Every glyph the widgets draw comes from the theme. Change a token and every widget
using it re-renders accordingly — same construction, different characters:

| Token(s) | Default | Drawn by |
|---|---|---|
| `tl tr bl br h v` | `╭ ╮ ╰ ╯ ─ │` | Window, Listbox, TextView, Table frames |
| `etl etr ebl ebr eh ev` | `╔ ╗ ╚ ╝ ═ ║` | Dialog (the elevated border) |
| `btl btr bbl bbr bh bv` | `┌ ┐ └ ┘ ─ │` | Button box |
| `sc_up sc_down sc_track sc_thumb` | `▲ ▼ ░ █` | scrollbars |
| `cb_l cb_r cb_mark` | `[ ] *` | Checkbox |
| `rg_l rg_r rg_mark` | `( ) *` | RadioGroup |
| `pb_l pb_r pb_fill pb_track` | `[ ] █ ░` | ProgressBar |
| `entry_fill` | `_` | TextInput empty space |
| `title_align` | `'center'` | frame titles (`'left'` supported) |
| `shadow_on` / `shadow_color` | `True` / `(1, 57, 75)` | every drop shadow (master switch) |

`OUTLINE` shows the token layer at work — rounded button corners (`btl='╭' …`), a
line-track scrollbar (`sc_track='│'`) — combined with a no-fill palette (its
`surface` *is* its `bg`, which is how panels become pure line work with the
classic chrome). Read its definition in `cookieui/theme.py`.

**Glyph rule:** tokens must be single-cell-width characters (no emoji, no
double-width CJK) — the cell grid assumes one glyph per cell.

## Layer 3 — the chrome: redesign construction

`theme.chrome` is an object that draws every *box* in the library. Widgets never
hardcode chrome — they call:

| Method | Draws |
|---|---|
| `frame(...)` | bordered box + title for Listbox / TextView / Table |
| `scrollbar(...)` | the scroll column |
| `window_frame(...)` | a Window's fill + border + title |
| `dialog_frame(...)` | a Dialog's raised fill + elevated border + title |
| `button_face(...)` | the 3-row button face (borders, label, focus treatment) |
| `shadow(...)` | the drop shadow (honors `shadow_on` / `shadow_color`) |

Subclass `Chrome` (or `FlatChrome`), override what you want, hang it on a theme:

```python
from dataclasses import replace
from cookieui import Chrome, NEWT

class HeavyTop(Chrome):
    """Frames whose top edge is a solid bar carrying the title."""
    def frame(self, screen, theme, x, y, w, h, *, focused=False, title='', bg=None):
        bg = super().frame(screen, theme, x, y, w, h,
                           focused=focused, title='', bg=bg)
        for cx in range(x, x + w):                       # solid top bar
            screen.put(cx, y, ' ', bg=theme.accent)
        if title:
            screen.write(x + 2, y, f' {title} ', fg=theme.surface,
                         bg=theme.accent, bold=True)
        return bg

MY_LOOK = replace(NEWT, chrome=HeavyTop())
```

`FlatChrome` (in `cookieui/chrome.py`) is the full worked example: it overrides
`frame`, `window_frame`, `dialog_frame`, and `button_face` to draw borderless
panels — read it top to bottom before writing your own.

**The geometry contract (the one hard rule).** A chrome changes what is *drawn*,
never what is *reserved*: frames still own their 1-cell edge (interiors start at
`+1,+1`), buttons are still 3 rows tall. All layout math (`content-fit`,
`fill_height`, footer rows) relies on those metrics. FlatChrome draws nothing in
the border cells — but it leaves them reserved, which is why every layout helper
works unchanged in FLAT. If you want different *metrics*, that is not a chrome —
that is a custom widget (subclass it; see PATTERNS.md, the composite pattern).

## The visual grammar (recommended, not enforced)

The shipped looks keep CookieUI's grammar: **full frames mean containers, brackets
mean inline controls, underscores mean entry**. A custom design may break it
knowingly — but if users of your theme can't tell a Listbox from a Label, that's
the reason.

## Limits, honestly

- **Spinner style** is a constructor argument (`Spinner(style='line')`), not a
  theme token — the spinner picks its frames at construction.
- **Swapping widget classes** (your own `Button` everywhere, including inside
  dialogs) is not themeable — that is deliberate. Subclassing a widget and using
  it in your views works today; a registry that injects it into the factories is
  on the rejected-ideas ledge until real demand shows up (PLAN.md).

## Testing your theme

The harness in `tests/conftest.py` makes look-verification one assert:

```python
from conftest import make, paint, row_text
app = make(lambda: MyApp(theme=MY_LOOK))
screen = paint(app)
assert row_text(screen, some_row).count('▔') > 0   # cell-level truth
```

`tests/test_theming.py` shows the patterns: glyph asserts per token, a SpyChrome
proving the seam is hit everywhere, and the shadow master-switch checks. NEWT
itself is pixel-gated — the chrome refactor reproduced it cell-for-cell, and any
future change to the default look has to do the same on purpose.

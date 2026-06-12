from dataclasses import dataclass, field, replace
from typing import Tuple

from .chrome import Chrome, FlatChrome

Color = Tuple[int, int, int]

# ── Original Newt palette (from reference screenshot) ──────────────────────────
_BLACK  = (  1,  57,  75)   # dark blue-gray (shadows)
_RED    = (236,  76,  47)   # coral/orange-red (buttons)
_BLUE   = ( 28, 144, 219)   # saturated blue (background)
_LGRAY  = (241, 234, 218)   # warm beige (window surface)
_WHITE  = (255, 215, 188)   # warm peachy-white (button text)
_BROWN  = (170,  85,   0)   # dark yellow / brown

# ── Catppuccin Mocha palette (kept for MOCHA secondary theme) ─────────────────
_BASE    = ( 30,  30,  46)
_MANTLE  = ( 24,  24,  37)
_SURF0   = ( 49,  50,  68)
_SURF1   = ( 69,  71,  90)
_SURF2   = ( 88,  91, 112)
_OVL0    = (108, 112, 134)
_OVL1    = (127, 132, 156)
_TEXT    = (205, 214, 244)
_SUB0    = (166, 173, 200)
_LAVEN   = (180, 190, 254)
_C_BLUE  = (137, 180, 250)
_GREEN   = (166, 227, 161)
_YELLOW  = (249, 226, 175)
_C_RED   = (243, 139, 168)
_MAUVE   = (203, 166, 247)


@dataclass
class Theme:
    # ── Surfaces ──────────────────────────────────────────────────────────
    bg:             Color   # root/background fill
    surface:        Color   # window interior
    surface_raised: Color   # dialog interior (sits above windows)

    # ── Borders ───────────────────────────────────────────────────────────
    border:         Color   # border character fg
    border_focused: Color
    border_dim:     Color

    # ── Text ──────────────────────────────────────────────────────────────
    text:           Color   # primary text (e.g. window content, list items)
    text_dim:       Color   # label-style text (blue on lightgray in Newt)
    text_muted:     Color

    # ── Semantic ──────────────────────────────────────────────────────────
    title_fg:       Color   # window/dialog title text
    accent:         Color   # general accent (selected item indicators etc.)
    success:        Color
    warning:        Color
    error:          Color

    # ── Button ────────────────────────────────────────────────────────────
    btn_bg:         Color   # compact button bg  (unfocused: blends with window)
    btn_fg:         Color   # compact button fg  (unfocused)
    btn_focused_bg: Color   # compact button bg  (focused / highlighted)
    btn_focused_fg: Color   # compact button fg  (focused)

    # 3-line button (large, with border — Newt-style)
    button_bg:      Color   # interior background
    button_fg:      Color   # text color
    button_border:  Color   # border character color

    # ── Entry / TextInput ─────────────────────────────────────────────────
    input_bg:         Color  # entry field background
    entry_fg:         Color  # entry field text + underscore fill
    input_cursor_bg:  Color  # cursor highlight bg
    input_cursor_fg:  Color  # cursor highlight fg

    # ── Checkbox ──────────────────────────────────────────────────────────
    checkbox_bg:      Color  # bracket-area bg when unfocused
    checkbox_fg:      Color  # bracket-area fg when unfocused
    checkbox_act_bg:  Color  # mark-char bg when focused  (red in Newt)
    checkbox_act_fg:  Color  # mark-char fg when focused

    # ── List ──────────────────────────────────────────────────────────────
    list_sel_bg:    Color
    list_sel_fg:    Color

    # ── Help / status line ────────────────────────────────────────────────
    help_bg:        Color
    help_fg:        Color

    # ── Regular box (windows, listboxes) ─────────────────────────────────
    tl: str = '╭'
    tr: str = '╮'
    bl: str = '╰'
    br: str = '╯'
    h:  str = '─'
    v:  str = '│'

    # ── Elevated box (dialogs) — double-line for visual hierarchy ────────
    etl: str = '╔'
    etr: str = '╗'
    ebl: str = '╚'
    ebr: str = '╝'
    eh:  str = '═'
    ev:  str = '║'

    # title_l / title_r removed — titles are now written directly over the
    # border line without connector characters (looks correct on rounded corners)

    # ── Scrollbar ─────────────────────────────────────────────────────────
    sc_up:    str = '▲'
    sc_down:  str = '▼'
    sc_track: str = '░'   # SLSMG_CKBRD_CHAR
    sc_thumb: str = '█'   # SLSMG_BLOCK_CHAR

    # ── Design tokens — every remaining glyph/switch design is made of ────
    # (TEMPLATING.md layer 2: change these and the same construction renders
    # in different characters — OUTLINE's rounded buttons and line scrollbar
    # are exactly this.)

    # Drop shadows: master switch + the color surfaces blend toward
    shadow_on:    bool  = True
    shadow_color: Color = (1, 57, 75)

    # Checkbox `[*] label` and RadioGroup `(*) label` brackets/marks
    cb_l:    str = '['
    cb_r:    str = ']'
    cb_mark: str = '*'
    rg_l:    str = '('
    rg_r:    str = ')'
    rg_mark: str = '*'

    # ProgressBar `[██░░]` brackets and fill/track pair
    pb_l:     str = '['
    pb_r:     str = ']'
    pb_fill:  str = '█'
    pb_track: str = '░'

    # TextInput empty-space fill (the Newt underscore row)
    entry_fill: str = '_'

    # 3-row Button box (square corners in Newt, distinct from window rounding)
    btl: str = '┌'
    btr: str = '┐'
    bbl: str = '└'
    bbr: str = '┘'
    bh:  str = '─'
    bv:  str = '│'

    # Title placement on frames: 'center' (Newt) or 'left'
    title_align: str = 'center'

    # ── Construction (TEMPLATING.md layer 3) ──────────────────────────────
    # The chrome draws every box: frames, titles, scrollbars, button faces,
    # shadows. Swap it (e.g. FlatChrome) to change construction itself.
    chrome: Chrome = field(default_factory=Chrome)

    # ── Nerd Font glyphs (only used where explicitly requested) ───────────
    ic_user:     str = ''
    ic_lock:     str = ''
    ic_cog:      str = ''
    ic_check:    str = ''
    ic_times:    str = ''
    ic_terminal: str = ''
    ic_list:     str = ''
    ic_circle_o: str = ''
    ic_circle:   str = ''
    ic_arrow_r:  str = ''
    pl_right:    str = ''
    pl_left:     str = ''
    pl_right_t:  str = ''
    pl_left_t:   str = ''


# ── Newt (default) ────────────────────────────────────────────────────────────
# Exact color mapping from newtDefaultColorPalette in newt.c
NEWT = Theme(
    bg             = _BLUE,    # root fg=white, bg=blue
    surface        = _LGRAY,   # window fg=black, bg=lightgray
    surface_raised = _LGRAY,   # dialog: same as window

    border         = _BLACK,   # border fg=black, bg=lightgray
    border_focused = _BLACK,
    border_dim     = (85, 85, 85),

    text           = _BLACK,   # window text: black on lightgray
    text_dim       = (85, 85, 85),  # label color: dark grey on lightgray (COLORSET_LABEL)
    text_muted     = (85, 85, 85),

    title_fg       = _RED,     # title: fg=red, bg=lightgray  (COLORSET_TITLE)
    accent         = _BLUE,
    success        = ( 0, 170,   0),
    warning        = _BROWN,
    error          = _RED,

    # compact button: black/lightgray unfocused; lightgray/red focused
    btn_bg         = _LGRAY,   # COLORSET_COMPACTBUTTON
    btn_fg         = _BLACK,
    btn_focused_bg = _RED,     # COLORSET_BUTTON: fg=lightgray, bg=red
    btn_focused_fg = _LGRAY,

    input_bg        = _BLUE,   # entry box: fg=white, bg=blue (COLORSET_ENTRY)
    entry_fg        = _WHITE,  # white text for better contrast on blue
    input_cursor_bg = _WHITE,  # cursor: inverted to white bg
    input_cursor_fg = _BLUE,

    # checkbox bracket area: lightgray/blue inactive; mark char lightgray/red focused
    checkbox_bg     = _BLUE,   # COLORSET_CHECKBOX
    checkbox_fg     = _LGRAY,
    checkbox_act_bg = _RED,    # COLORSET_ACTCHECKBOX — only the mark char
    checkbox_act_fg = _LGRAY,

    list_sel_bg    = _RED,     # COLORSET_ACTSELLISTBOX: lightgray/red
    list_sel_fg    = _LGRAY,

    help_bg        = _BLUE,    # COLORSET_HELPLINE: blue background
    help_fg        = _BLACK,   # black text for better contrast on bright blue

    # 3-line button: red background with white border and text (Newt-style)
    button_border  = _WHITE,    # border color (white frame)
    button_bg      = _RED,      # interior background (red)
    button_fg      = _WHITE,    # text color (white on red)
)

# ── Catppuccin Mocha (secondary) ──────────────────────────────────────────────
MOCHA = Theme(
    bg             = _BASE,
    surface        = _SURF0,
    surface_raised = _SURF1,

    border         = _SURF2,
    border_focused = _C_BLUE,
    border_dim     = _OVL0,

    text           = _TEXT,
    text_dim       = _SUB0,
    text_muted     = _OVL0,

    title_fg       = _C_BLUE,
    accent         = _C_BLUE,
    success        = _GREEN,
    warning        = _YELLOW,
    error          = _C_RED,

    btn_bg         = _SURF1,
    btn_fg         = _TEXT,
    btn_focused_bg = _C_BLUE,
    btn_focused_fg = _BASE,

    input_bg        = _MANTLE,
    entry_fg        = _TEXT,
    input_cursor_bg = _C_BLUE,
    input_cursor_fg = _BASE,

    checkbox_bg     = _MANTLE,
    checkbox_fg     = _TEXT,
    checkbox_act_bg = _C_BLUE,
    checkbox_act_fg = _BASE,

    list_sel_bg    = _C_BLUE,
    list_sel_fg    = _BASE,

    help_bg        = _SURF0,
    help_fg        = _OVL1,

    # 3-line button: stays inside the Catppuccin palette — blue surface, dark
    # text, lavender frame. (The Newt coral belongs to NEWT alone.)
    button_border  = _LAVEN,    # border color (lavender frame)
    button_bg      = _C_BLUE,   # interior background (blue)
    button_fg      = _BASE,     # text color (dark on blue)

    tl = '╭', tr = '╮', bl = '╰', br = '╯',
    # Mocha dialogs: heavy single-line for a different flavour
    etl = '┌', etr = '┐', ebl = '└', ebr = '┘',
    eh  = '─', ev  = '│',

    # Shadows blend everything toward one dark tone — on a dark palette that
    # reads as mud, not depth. Dark themes go flat (FLAT does the same).
    shadow_on = False,
)

# ── OUTLINE (wireframe) ───────────────────────────────────────────────────────
# Nothing is a filled panel: every surface shares the background, so the UI is
# pure line work — rounded-corner frames (╭╮╰╯), outlined buttons (rounded
# too), a line-track scrollbar. Color appears only where the eye needs it:
# titles, the focused border, the selection bar, the focused button label.
# A colors-and-tokens design (layers 1+2) — the classic chrome draws it.
_OUT_BG    = ( 16,  17,  20)    # graphite — the one and only surface
_OUT_LINE  = (118, 126, 138)    # the wire
_OUT_TEXT  = (222, 226, 232)
_OUT_DIM   = (140, 147, 158)
_OUT_TEAL  = ( 86, 214, 196)    # the accent
_OUT_GREEN = (158, 206, 106)
_OUT_AMBER = (255, 196,  92)
_OUT_RED   = (244, 122, 122)

OUTLINE = Theme(
    bg             = _OUT_BG,
    surface        = _OUT_BG,        # same as bg: panels are outlines, not fills
    surface_raised = _OUT_BG,

    border         = _OUT_LINE,
    border_focused = _OUT_TEAL,
    border_dim     = ( 70,  75,  85),

    text           = _OUT_TEXT,
    text_dim       = _OUT_DIM,
    text_muted     = _OUT_DIM,

    title_fg       = _OUT_TEAL,
    accent         = _OUT_TEAL,
    success        = _OUT_GREEN,
    warning        = _OUT_AMBER,
    error          = _OUT_RED,

    btn_bg         = _OUT_BG,
    btn_fg         = _OUT_TEXT,
    btn_focused_bg = _OUT_TEAL,
    btn_focused_fg = _OUT_BG,

    input_bg        = _OUT_BG,       # entry is the underscore line, not a box
    entry_fg        = _OUT_TEXT,
    input_cursor_bg = _OUT_TEAL,
    input_cursor_fg = _OUT_BG,

    checkbox_bg     = _OUT_BG,
    checkbox_fg     = _OUT_TEXT,
    checkbox_act_bg = _OUT_TEAL,
    checkbox_act_fg = _OUT_BG,

    list_sel_bg    = _OUT_TEAL,      # the selection bar: the one allowed fill
    list_sel_fg    = _OUT_BG,

    help_bg        = _OUT_BG,
    help_fg        = _OUT_DIM,

    # outlined button: background IS the page background; only the frame and
    # label show. Focused → the label area highlights in the accent.
    button_border  = _OUT_LINE,
    button_bg      = _OUT_BG,
    button_fg      = _OUT_TEAL,

    # rounded corners everywhere — buttons included
    btl='╭', btr='╮', bbl='╰', bbr='╯',

    # line-track scrollbar
    sc_track='│', sc_thumb='█',

    shadow_on = False,               # outlines cast no shadows
)

# ── FLAT (ink) ────────────────────────────────────────────────────────────────
# A construction-level design: FlatChrome draws no borders at all — panels are
# color fields, titles sit on a thin rule, buttons are solid blocks. Geometry
# is identical to the classic chrome, so every layout helper works unchanged.
_INK_BG     = ( 22,  24,  31)
_INK_PANEL  = ( 32,  35,  44)
_INK_RAISED = ( 42,  46,  58)
_INK_LINE   = ( 70,  76,  94)
_INK_TEXT   = (214, 219, 230)
_INK_DIM    = (138, 145, 162)
_INK_BLUE   = (122, 162, 247)
_INK_SKY    = (165, 199, 255)
_INK_GREEN  = (158, 206, 106)
_INK_AMBER  = (224, 175,  104)
_INK_RED    = (247, 118, 142)

FLAT = Theme(
    bg             = _INK_BG,
    surface        = _INK_PANEL,
    surface_raised = _INK_RAISED,

    border         = _INK_LINE,
    border_focused = _INK_BLUE,
    border_dim     = _INK_LINE,

    text           = _INK_TEXT,
    text_dim       = _INK_DIM,
    text_muted     = _INK_DIM,

    title_fg       = _INK_BLUE,
    accent         = _INK_BLUE,
    success        = _INK_GREEN,
    warning        = _INK_AMBER,
    error          = _INK_RED,

    # FlatChrome buttons read these: near-black idle block, accent when focused
    btn_bg         = ( 14,  16,  21),
    btn_fg         = _INK_DIM,
    btn_focused_bg = _INK_BLUE,
    btn_focused_fg = _INK_BG,

    input_bg        = ( 16,  18,  24),
    entry_fg        = _INK_TEXT,
    input_cursor_bg = _INK_BLUE,
    input_cursor_fg = _INK_BG,

    checkbox_bg     = ( 16,  18,  24),
    checkbox_fg     = _INK_TEXT,
    checkbox_act_bg = _INK_BLUE,
    checkbox_act_fg = _INK_BG,

    list_sel_bg    = _INK_BLUE,
    list_sel_fg    = _INK_BG,

    help_bg        = _INK_PANEL,
    help_fg        = _INK_DIM,

    button_border  = _INK_BLUE,
    button_bg      = _INK_BLUE,
    button_fg      = _INK_BG,

    # flat scrollbar: invisible track, a floating block thumb, no arrows
    sc_up=' ', sc_down=' ', sc_track=' ', sc_thumb='▐',

    title_align = 'left',
    shadow_on   = False,
    chrome      = FlatChrome(),
)

DEFAULT = NEWT

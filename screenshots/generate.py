#!/usr/bin/env python3
"""Regenerate every README screenshot from real composed frames.

Each example app is constructed headlessly, staged with real key dispatch so it
looks alive, rendered cell-by-cell with JetBrains Mono, and framed in a macOS
style terminal window. Deterministic: re-run after any visual change and the
screenshots cannot go stale.

Usage:  python screenshots/generate.py
Font:   JetBrains Mono (Regular + Bold). Looked up in COOKIEUI_SHOT_FONT_DIR,
        then common locations. `pip install pillow` is the only extra need.
"""
import importlib.util
import os
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from conftest import make, press, paint, settle, find          # noqa: E402
from cookieui import NEWT, MOCHA, OUTLINE, FLAT, ProgressBar   # noqa: E402
from cookieui.core.event import Key, KeyType                   # noqa: E402

FONT_DIRS = [
    os.environ.get('COOKIEUI_SHOT_FONT_DIR', ''),
    str(ROOT.parent / 'cookieui-book' / 'book' / 'fonts' / 'jetbrains-mono'),
    str(pathlib.Path.home() / 'Library' / 'Fonts'),
    '/usr/share/fonts/truetype/jetbrains-mono',
]


def find_font(name):
    for d in FONT_DIRS:
        p = pathlib.Path(d) / name
        if d and p.exists():
            return str(p)
    sys.exit(f'JetBrains Mono not found ({name}) — set COOKIEUI_SHOT_FONT_DIR')


SIZE = 32
FONT = ImageFont.truetype(find_font('JetBrainsMono-Regular.ttf'), SIZE)
BOLD = ImageFont.truetype(find_font('JetBrainsMono-Bold.ttf'), SIZE)
TITLEFONT = ImageFont.truetype(find_font('JetBrainsMono-Regular.ttf'), 24)
CW = round(FONT.getlength('M'))
CH = round(SIZE * 1.30)
TERM_W, TERM_H = 92, 30


def load(name):
    spec = importlib.util.spec_from_file_location(
        'shot_' + name.replace('-', '_'), ROOT / 'examples' / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


BLOCKS = {'\u2588': 1.0, '\u2593': 0.75, '\u2592': 0.5, '\u2591': 0.25}
LOWER = {chr(0x2581 + i): (i + 1) / 8 for i in range(7)}    # \u2581\u2582\u2583\u2584\u2585\u2586\u2587
HALVES = {'\u258c': 'left', '\u2590': 'right', '\u2580': 'top'}


def _load_fallback():
    for p in ('/System/Library/Fonts/Menlo.ttc',
              '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'):
        try:
            return ImageFont.truetype(p, SIZE)
        except OSError:
            continue
    return None


FALLBACK = _load_fallback()
_TOFU = {True: bytes(BOLD.getmask('\ue000')), False: bytes(FONT.getmask('\ue000'))}
_FCACHE = {}


def glyph_font(ch, bold=False):
    """JetBrains Mono first; Menlo/DejaVu for glyphs it lacks (spinner arcs,
    braille) \u2014 like a real terminal's font fallback, instead of a tofu box."""
    f = BOLD if bold else FONT
    if FALLBACK is None:
        return f
    key = (ch, bold)
    if key not in _FCACHE:
        _FCACHE[key] = FALLBACK if bytes(f.getmask(ch)) == _TOFU[bold] else f
    return _FCACHE[key]


def grid_image(screen):
    img = Image.new('RGB', (screen.width * CW, screen.height * CH))
    drw = ImageDraw.Draw(img)
    for y, row in enumerate(screen._cells):
        for x, c in enumerate(row):
            drw.rectangle([x * CW, y * CH, (x + 1) * CW - 1, (y + 1) * CH - 1],
                          fill=c.bg or (0, 0, 0))
            ch = c.char
            if ch in BLOCKS:
                # block/shade elements fill the whole cell, edge to edge —
                # exactly as real terminals special-case them (no glyph gaps)
                k = BLOCKS[ch]
                fg = c.fg or (255, 255, 255)
                bg = c.bg or (0, 0, 0)
                mix = tuple(int(f * k + b * (1 - k)) for f, b in zip(fg, bg))
                drw.rectangle([x * CW, y * CH, (x + 1) * CW - 1, (y + 1) * CH - 1],
                              fill=mix)
            elif ch in LOWER:
                # lower-eighth blocks (pulse spinner): solid fg from the bottom up
                top = y * CH + round(CH * (1 - LOWER[ch]))
                drw.rectangle([x * CW, top, (x + 1) * CW - 1, (y + 1) * CH - 1],
                              fill=c.fg or (255, 255, 255))
            elif ch in HALVES:
                # half blocks (FLAT scrollbar thumb): solid fg in that half-cell
                box = {'left':  [x * CW, y * CH, x * CW + CW // 2 - 1, (y + 1) * CH - 1],
                       'right': [x * CW + CW // 2, y * CH, (x + 1) * CW - 1, (y + 1) * CH - 1],
                       'top':   [x * CW, y * CH, (x + 1) * CW - 1, y * CH + CH // 2 - 1],
                       }[HALVES[ch]]
                drw.rectangle(box, fill=c.fg or (255, 255, 255))
            elif ch != ' ':
                drw.text((x * CW + CW // 2, y * CH + CH // 2), ch,
                         font=glyph_font(ch, c.bold),
                         fill=c.fg or (255, 255, 255), anchor='mm')
    return img


def terminal_frame(shot, title):
    BAR, RAD, PAD = 58, 18, 96
    W, H = shot.width, shot.height + BAR
    canvas = Image.new('RGBA', (W + 2 * PAD, H + 2 * PAD), (0, 0, 0, 0))
    # three shadow layers, like macOS (and the cover's CSS box-shadow):
    # a tight contact shadow plus two progressively larger, softer ones
    for dy, blur, alpha in ((6, 5, 70), (18, 12, 60), (34, 26, 55)):
        sh = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            [PAD, PAD + dy, PAD + W, PAD + H + dy], RAD, fill=(30, 24, 16, alpha))
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    term = Image.new('RGBA', (W, H))
    td = ImageDraw.Draw(term)
    td.rectangle([0, 0, W, BAR], fill=(58, 46, 34, 255))
    term.paste(shot, (0, BAR))
    for i, color in enumerate(((224, 99, 92), (232, 163, 61), (156, 201, 127))):
        cx = 34 + i * 30
        td.ellipse([cx - 10, BAR // 2 - 10, cx + 10, BAR // 2 + 10], fill=color)
    td.text((W // 2, BAR // 2), title, font=TITLEFONT,
            fill=(187, 169, 142), anchor='mm')
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W, H], RAD, fill=255)
    canvas.paste(term, (PAD, PAD), mask)
    return canvas


# ── the stagings ──────────────────────────────────────────────────────────────

def shot_filecopy():
    app = make(load('file-copy-progress').FileCopyApp, w=TERM_W, h=TERM_H)
    app._app.theme = MOCHA
    app.src.set_value('~/Movies/holiday-2026.mp4')
    app.dst.set_value('~/Backup/')
    find(app._app.current_view, ProgressBar).value = 0.67
    app.status.text = 'Copying holiday-2026.mp4 …'
    return app

def shot_filebrowsing():
    app = make(lambda: load('filebrowsing').FileBrowsingApp(ROOT / 'examples'),
               w=TERM_W, h=TERM_H)
    app._app.theme = FLAT
    press(app, Key(KeyType.DOWN), Key(KeyType.DOWN), Key(KeyType.DOWN))
    return app

def shot_processes():
    app = make(load('processes').Processes, w=TERM_W, h=TERM_H)
    press(app, Key(KeyType.TAB), Key(KeyType.DOWN), Key(KeyType.DOWN))
    return app

def shot_progressdemo():
    app = make(load('progressdemo').ProgressDemo, w=TERM_W, h=TERM_H)
    find(app._app.current_view, ProgressBar).value = 0.58
    return app

def shot_spinnerdemo():
    app = make(load('spinnerdemo').SpinnerDemo, w=TERM_W, h=TERM_H)
    press(app, Key(KeyType.DOWN), Key(KeyType.DOWN))
    return app

def shot_todo():
    mod = load('todo')
    mod.TODOS_FILE = pathlib.Path('/tmp/shot-todos.json')
    mod.TODOS_FILE.unlink(missing_ok=True)
    app = make(mod.TodoApp, w=TERM_W, h=TERM_H)
    for t in ('Preheat the oven', 'Mix the dough', 'Bake 12 minutes', 'Eat warm'):
        press(app, t, Key(KeyType.ENTER))
    press(app, Key(KeyType.TAB), Key(KeyType.ENTER))
    press(app, Key(KeyType.DOWN), Key(KeyType.ENTER))
    press(app, Key(KeyType.DOWN))
    return app

def shot_login():
    app = make(load('demo').Demo, w=TERM_W, h=TERM_H)
    press(app, 'tahseen', Key(KeyType.TAB), 'cookies!')
    return app

def shot_dialogs():
    app = make(load('quickdialogs').QuickDialogs, w=TERM_W, h=TERM_H)
    app._app.theme = OUTLINE
    press(app, Key(KeyType.TAB), Key(KeyType.ENTER))
    settle()
    return app

def shot_themes():
    app = make(load('themedemo').ThemeGallery, w=TERM_W, h=TERM_H)
    press(app, Key(KeyType.DOWN))                    # Mocha selected, live
    return app

def shot_commander():
    base = pathlib.Path('/tmp/shot-commander')
    left, right = base / 'projects', base / 'backup'
    for d in (left / 'cookieui', left / 'notes', right / 'old'):
        d.mkdir(parents=True, exist_ok=True)
    (left / 'recipe.md').write_text('# Cookies\n')
    (left / 'todo.txt').write_text('bake\n')
    (right / 'archive.tar').write_bytes(b'x' * 9)
    app = make(lambda: load('commander').Commander(left=left, right=right),
               w=TERM_W, h=TERM_H)
    press(app, Key(KeyType.DOWN), Key(KeyType.DOWN), Key(KeyType.DOWN))
    return app


SHOTS = [
    ('1',  shot_filecopy,     'python examples/file-copy-progress.py'),
    ('2',  shot_filebrowsing, 'python examples/filebrowsing.py'),
    ('3',  shot_processes,    'python examples/processes.py'),
    ('4',  shot_progressdemo, 'python examples/progressdemo.py'),
    ('5',  shot_spinnerdemo,  'python examples/spinnerdemo.py'),
    ('6',  shot_todo,         'python examples/todo.py'),
    ('7',  shot_login,        'python examples/demo.py'),
    ('8',  shot_dialogs,      'python examples/quickdialogs.py'),
    ('9',  shot_themes,       'python examples/themedemo.py'),
    ('10', shot_commander,    'python examples/commander.py'),
]


if __name__ == '__main__':
    out_dir = ROOT / 'screenshots'
    for num, stage, title in SHOTS:
        plate = terminal_frame(grid_image(paint(stage())), title)
        plate.save(out_dir / f'{num}.png')
        print(f'{num:>2}.png  {title}')

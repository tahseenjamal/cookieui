import time

from .base import Widget


class Spinner(Widget):
    """Animated activity spinner.

    Animates from the wall clock, so it spins at a steady rate regardless of how often the
    screen redraws — just add it to a window and it spins while visible. No threads or
    timers needed (the run loop already redraws every tick).

    Pick a look with `style=` ('dots', 'line', 'arc', 'circle', 'square', 'arrow',
    'pulse') or pass any glyph cycle via `frames=` — single-cell-width characters only.

    Control it by mutating attributes:
      • `.visible = False`  — hide it (e.g. when the work finishes)
      • `.spinning = False` — freeze it on the first frame without hiding
      • `.frames = Spinner.STYLES['arc']` — switch style live
    """
    focusable = False

    # Named styles — every frame is single-cell width (no emoji: double-width glyphs
    # break monospace alignment) and covered by common terminal fonts.
    STYLES = {
        'dots':   '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏',   # smooth braille (default)
        'line':   '|/-\\',          # pure ASCII — works on any terminal
        'arc':    '◜◠◝◞◡◟',         # orbiting arc
        'circle': '◐◓◑◒',           # rotating half-disc
        'square': '▖▘▝▗',           # corner chase
        'arrow':  '←↖↑↗→↘↓↙',       # compass sweep
        'pulse':  '▁▂▃▄▅▆▇█▇▆▅▄▃▂', # breathing bar
    }

    def __init__(self, x: int, y: int, label: str = '',
                 frames: str = None, fps: float = 12, color=None,
                 style: str = 'dots'):
        super().__init__(x, y, max(1, len(label) + 2), 1)
        if frames is None:
            if style not in self.STYLES:
                raise ValueError(f"unknown spinner style {style!r} — "
                                 f"one of {', '.join(self.STYLES)} (or pass frames=)")
            frames = self.STYLES[style]
        self.label    = label
        self.frames   = frames
        self.fps      = fps
        self.color    = color
        self.spinning = True
        self._t0      = time.monotonic()

    def draw(self, screen, theme):
        if self.spinning:
            i = int((time.monotonic() - self._t0) * self.fps) % len(self.frames)
        else:
            i = 0
        glyph = self.frames[i]
        text  = f'{glyph} {self.label}' if self.label else glyph
        screen.write_over(self.x, self.y, text, fg=self.color or theme.accent)

from .base import Widget


class ProgressBar(Widget):
    """Horizontal progress bar — a self-contained status area.

    Set ``.value`` in the range 0.0–1.0 from anywhere (e.g. a worker thread) and the next
    redraw reflects it — no method calls, no draw() of your own. The value is clamped at
    draw time, so over/undershooting is harmless.

    The bar's **center** carries its message, installer-style, and the track spans the
    full width (no side suffix eating columns):

        [██████████ 42% ░░░░░░░░░░]     while progressing (show_percent)
        [███████Complete ✓████████]     when .text is set — it replaces the percent

    ``.text`` is live-mutable like every attribute and clipped at draw time; run_task
    sets it for you (running/done/error) when the bar is the status target.
    """
    focusable = False

    def __init__(self, x: int, y: int, width: int,
                 value: float = 0.0, show_percent: bool = True, color=None,
                 text: str = ''):
        super().__init__(x, y, width, 1)
        self.value        = value
        self.show_percent = show_percent   # centered percent while .text is empty
        self.color        = color
        self.text         = text           # centered message; replaces the percent

    def draw(self, screen, theme):
        t      = theme
        v      = max(0.0, min(1.0, self.value))
        inner  = max(1, self.width - 2)              # full width minus the brackets
        filled = int(round(inner * v))
        cells  = t.pb_fill * filled + t.pb_track * (inner - filled)

        # Center label: the message when set, else the live percent
        label = self.text or (f' {int(round(v * 100))}% ' if self.show_percent else '')
        start = end = -1
        if label:
            label = label[:inner]                    # clipped at draw time
            start = max(0, (inner - len(label)) // 2)
            end   = start + len(label)
            cells = cells[:start] + label + cells[end:]

        color = self.color or t.accent
        screen.write_over(self.x, self.y, t.pb_l, fg=color)
        for i, ch in enumerate(cells):
            cx = self.x + 1 + i
            if not (start <= i < end):
                screen.write_over(cx, self.y, ch, fg=color)
            elif i < filled:
                # label over the fill: surface-colored on the bar color (carved look)
                screen.put(cx, self.y, ch, fg=t.surface, bg=color, bold=True)
            else:
                # label over the track: background blended to the track's visual
                # density (track ≈ 25% bar color over whatever is underneath), so
                # the text never punches a hole in the track
                under = screen.bg_at(cx, self.y) or t.bg
                track = tuple(int(c * 0.25 + u * 0.75) for c, u in zip(color, under))
                screen.put(cx, self.y, ch, fg=t.text, bg=track, bold=True)
        screen.write_over(self.x + 1 + inner, self.y, t.pb_r, fg=color)

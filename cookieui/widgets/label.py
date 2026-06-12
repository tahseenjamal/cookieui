from .base import Widget


class Label(Widget):
    """Static text. Set `.text` from anywhere — the next frame shows it.

    `max_width` clips the text **at draw time**, so live `.text` updates can never
    overflow a window border — no `text[:iw - 4]`-style eyeballed slicing at the call
    site. Labels built via a layout (`lay.label(...)`) get it set automatically.
    """
    focusable = False

    def __init__(self, x: int, y: int, text: str,
                 bold: bool = False, dim: bool = False, color=None,
                 max_width: int = None):
        super().__init__(x, y, len(text), 1)
        self.text      = text
        self.bold      = bold
        self.dim       = dim
        self.color     = color       # override fg; None = theme.text
        self.max_width = max_width   # clip at draw time; None = no clipping

    def draw(self, screen, theme):
        fg = self.color if self.color else (theme.text_dim if self.dim else theme.text)
        text = self.text if self.max_width is None else self.text[:self.max_width]
        screen.write_over(self.x, self.y, text, fg=fg,
                          bold=self.bold, dim=self.dim)

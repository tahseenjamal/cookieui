from typing import Optional, Callable, List

from .base import Widget
from ..core.event import Key, KeyType


class Table(Widget):
    """Scrollable table: a bold header row, a separator, and selectable data rows.

    Columns are declared once, as specs (the house pair convention — ints in column
    specs are **weights**, like `columns(view, [2, 1])`):

        'Name'                # weight 1, left-aligned
        ('Name', 2)           # weight 2
        ('CPU%', 1, '>')      # right-aligned (numbers)

    Column widths are **derived** — the interior is split by weight, never by
    character counts — and every cell is clipped to its column at draw time, so rows
    are passed untrimmed. Rows follow the value-carrying convention:

        t.rows = [((pid, cpu, cmd), proc) for proc in procs]   # cells, domain object
        picked = t.selected_value                              # → the proc

    Bare cell-tuples work too (the tuple is its own value). Keys and selection are
    identical to Listbox: Up/Down/PgUp/PgDn/Home/End move (clamped), Enter fires
    `on_select(index, value)`; assigning `.rows` re-clamps the selection.
    """
    focusable = True

    CHROME = 4   # border(2) + header(1) + separator(1) — rows above/below the data
    GAP    = 2   # spaces between columns

    def __init__(self, x: int, y: int, width: int, height: int,
                 columns=None, rows=None, title: str = '',
                 on_select: Optional[Callable] = None, shadow: bool = True):
        super().__init__(x, y, width, height)
        self.title      = title
        self.shadow     = shadow
        self._on_select = on_select
        self._sel       = 0
        self._scroll    = 0
        self._cells     = []
        self._values    = []
        self.columns    = columns or []
        self.rows       = list(rows or [])

    # ── Columns ──────────────────────────────────────────────────────────

    @property
    def columns(self) -> List[str]:
        return self._col_labels

    @columns.setter
    def columns(self, specs) -> None:
        """Specs: 'Label' | ('Label', weight) | ('Label', weight, align) where align
        is '<' (default) or '>'."""
        labels, weights, aligns = [], [], []
        for spec in specs:
            if isinstance(spec, str):
                label, weight, align = spec, 1, '<'
            else:
                label, weight = spec[0], spec[1]
                align = spec[2] if len(spec) > 2 else '<'
            if align not in ('<', '>'):
                raise ValueError(f"column {label!r}: align must be '<' or '>', "
                                 f"got {align!r}")
            labels.append(str(label))
            weights.append(weight)
            aligns.append(align)
        self._col_labels  = labels
        self._col_weights = weights
        self._col_aligns  = aligns

    def _col_widths(self, usable: int) -> List[int]:
        """Split `usable` columns across the declared weights (remainder → last)."""
        total = sum(self._col_weights) or 1
        widths = [max(1, usable * w // total) for w in self._col_weights]
        widths[-1] += usable - sum(widths)
        return widths

    # ── Rows (value-carrying, like Listbox items) ────────────────────────

    @property
    def rows(self):
        return self._cells

    @rows.setter
    def rows(self, entries) -> None:
        """Each entry: (cells_tuple, value) or a bare cells tuple (its own value).
        Cell count must match the declared columns. Re-clamps selection/scroll."""
        ncols = len(self._col_labels)
        cells, values = [], []
        for entry in entries:
            if (isinstance(entry, tuple) and len(entry) == 2
                    and isinstance(entry[0], (tuple, list))):
                row, val = entry
            else:
                row, val = entry, entry
            row = [str(c) for c in row]
            if ncols and len(row) != ncols:
                raise ValueError(
                    f'table row has {len(row)} cells but {ncols} columns are '
                    f'declared ({", ".join(self._col_labels)}): {row!r}')
            cells.append(row)
            values.append(val)
        self._cells  = cells
        self._values = values
        self._clamp()

    @property
    def selected(self):
        """The selected row's cells (list of strings), or None when empty."""
        return self._cells[self._sel] if self._cells else None

    @property
    def selected_value(self):
        return self._values[self._sel] if self._values else None

    @property
    def selected_index(self) -> int:
        return self._sel

    @selected_index.setter
    def selected_index(self, idx: int) -> None:
        self._sel = idx
        self._clamp()

    # ── Geometry / selection mechanics (mirrors Listbox) ─────────────────

    def _inner_h(self) -> int:
        return self.height - self.CHROME            # data rows only

    def _clamp(self) -> None:
        n  = len(self._cells)
        ih = self._inner_h()
        self._sel = 0 if n == 0 else max(0, min(self._sel, n - 1))
        if self._sel < self._scroll:
            self._scroll = self._sel
        elif self._sel >= self._scroll + ih:
            self._scroll = self._sel - ih + 1
        self._scroll = max(0, min(self._scroll, max(0, n - ih)))

    def _move(self, delta: int):
        self._sel += delta
        self._clamp()

    # ── Drawing ──────────────────────────────────────────────────────────

    def _fmt(self, row, widths) -> str:
        out = []
        for cell, w, align in zip(row, widths, self._col_aligns):
            cell = cell[:w]                          # clip at draw time
            out.append(cell.rjust(w) if align == '>' else cell.ljust(w))
        return (' ' * self.GAP).join(out)

    def draw(self, screen, theme):
        t      = theme
        ih     = self._inner_h()
        has_sb = len(self._cells) > ih
        inner  = self.width - 2 - (1 if has_sb else 0)
        usable = max(len(self._col_labels),
                     inner - self.GAP * max(0, len(self._col_labels) - 1))
        widths = self._col_widths(usable) if self._col_labels else []

        bg = t.chrome.frame(screen, theme, self.x, self.y, self.width, self.height,
                            focused=self.focused, title=self.title)

        # Header (bold) + thin separator
        header = self._fmt(self._col_labels, widths)[:inner].ljust(inner)
        screen.write(self.x + 1, self.y + 1, header, fg=t.text, bg=bg, bold=True)
        screen.write(self.x + 1, self.y + 2, t.h * inner, fg=t.border, bg=bg)

        # Data rows
        for i in range(ih):
            idx = self._scroll + i
            ry  = self.y + 3 + i
            if idx >= len(self._cells):
                screen.fill(self.x + 1, ry, inner, 1, bg=bg)
                continue
            line   = self._fmt(self._cells[idx], widths)[:inner].ljust(inner)
            is_sel = (idx == self._sel)
            if is_sel and self.focused:
                row_bg, row_fg = t.list_sel_bg, t.list_sel_fg
            elif is_sel:
                row_bg, row_fg = bg, t.accent
            else:
                row_bg, row_fg = bg, t.text
            screen.write(self.x + 1, ry, line, fg=row_fg, bg=row_bg)

        if has_sb:
            t.chrome.scrollbar(screen, theme, self.x + self.width - 2, self.y + 3,
                               ih, len(self._cells), self._scroll, bg=bg)

        if self.shadow:
            t.chrome.shadow(screen, theme, self.x, self.y, self.width, self.height)

    # ── Keys (identical to Listbox) ──────────────────────────────────────

    def handle_key(self, key: Key) -> bool:
        ih = self._inner_h()
        n  = len(self._cells)
        if n == 0:
            return False
        kt = key.type
        if kt == KeyType.UP:        self._move(-1);  return True
        if kt == KeyType.DOWN:      self._move(1);   return True
        if kt == KeyType.PAGE_UP:   self._move(-ih); return True
        if kt == KeyType.PAGE_DOWN: self._move(ih);  return True
        if kt == KeyType.HOME:
            self.selected_index = 0;     return True
        if kt == KeyType.END:
            self.selected_index = n - 1; return True
        if kt == KeyType.ENTER and self._on_select:
            self._on_select(self._sel, self.selected_value); return True
        return False

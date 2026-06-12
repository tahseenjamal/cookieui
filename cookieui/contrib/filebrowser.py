from pathlib import Path

from ..widgets.listbox import Listbox


class FileBrowser(Listbox):
    """A directory-navigating file browser, built on `Listbox`.

    Selecting a directory enters it (in place — no view rebuild); selecting a file calls
    `on_select(path)`. The current directory is shown as the listbox title; each row
    carries `(Path, is_dir)` as its listbox value, and `selected_path` returns just
    the Path (None on the go-up row) — the value host apps act on.

    Args:
        start_dir:     directory to open.
        on_select:     fn(Path) called when a file is chosen.
        on_dir_change: optional fn(Path) called after navigating into a directory.
        extensions:    iterable of lowercase suffixes to show (e.g. {'.html', '.htm'});
                       None shows all files.
        show_hidden:   include dotfiles (default False).
        dirs_only:     show directories only (no files).

    Extra keyword args (e.g. `shadow=False`) pass through to `Listbox`.
    """

    def __init__(self, x: int, y: int, width: int, height: int, start_dir,
                 on_select=None, on_dir_change=None,
                 extensions=None, show_hidden: bool = False, dirs_only: bool = False, **kw):
        super().__init__(x, y, width, height, on_select=self._handle_select, **kw)
        self._dir           = Path(start_dir)
        self._on_file       = on_select          # NOT _on_select — Listbox owns that name
        self._on_dir_change = on_dir_change
        self._exts          = {e.lower() for e in extensions} if extensions else None
        self._show_hidden   = show_hidden
        self._dirs_only     = dirs_only
        self._refresh()

    @property
    def current_dir(self) -> Path:
        return self._dir

    @property
    def selected_path(self):
        """The selected row's Path — or None on the go-up row, permission rows,
        and empty listings. The value host apps act on (copy/move/delete this)."""
        value = self.selected_value
        if value is None or value[0] is None:
            return None
        if self._items and self._items[self._sel].startswith('../'):
            return None                          # going up is navigation, not selection
        return value[0]

    def open_dir(self, path) -> None:
        """Navigate to `path` and refresh the listing (fires on_dir_change)."""
        self._dir = Path(path)
        self._refresh()
        if self._on_dir_change:
            self._on_dir_change(self._dir)

    @staticmethod
    def _is_dir(p: Path) -> bool:
        try:
            return p.is_dir()
        except OSError:
            return False

    def _refresh(self) -> None:
        # Current directory as the title (truncated to fit).
        max_title = max(8, self.width - 4)
        path = str(self._dir)
        self.title = ('…' + path[-(max_title - 1):]) if len(path) > max_title else path

        # Each row carries (path, is_dir) as its Listbox value.
        items = []
        if self._dir.parent != self._dir:
            items.append(('../  (go up)', (self._dir.parent, True)))
        try:
            children = sorted(self._dir.iterdir(),
                              key=lambda q: (not self._is_dir(q), q.name.lower()))
        except PermissionError:
            self.items = [('[Permission denied]', (None, False))]
            self.selected_index = 0
            return

        for q in children:
            if not self._show_hidden and q.name.startswith('.'):
                continue
            if self._is_dir(q):
                items.append((f'{q.name}/', (q, True)))
            elif not self._dirs_only and (self._exts is None or q.suffix.lower() in self._exts):
                items.append((q.name, (q, False)))

        self.items = items
        self.selected_index = 0

    def _handle_select(self, idx: int, _label: str) -> None:
        value = self.selected_value
        if value is None:
            return
        path, is_dir = value
        if is_dir and path is not None:
            self.open_dir(path)
        elif path is not None and path.is_file() and self._on_file:
            self._on_file(path)

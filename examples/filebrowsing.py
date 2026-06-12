#!/usr/bin/env python3
"""CookieUI File Browser — Navigate directories and read files in place.

OVERVIEW:
  A TUI file browser for exploring directory structure and reading files.
  Navigate directories recursively; opening a text file shows its contents in a
  scrollable viewer, binary files show an info dialog.

FEATURES:
  - Directory navigation: Browse up/down the directory tree
  - Sorted display: Directories first (sorted alphabetically), then files
  - File viewer: Text files open in a scrollable TextView (full content)
  - Binary detection: Non-text files show an info dialog instead
  - Parent directory: ".." entry to go up one level
  - Current directory shown as the browser's panel title (auto-truncates if long)
  - Permission handling: Gracefully handles permission-denied directories
  - Built on the cookieui.contrib FileBrowser widget (navigation happens in-place)

KEYBOARD CONTROLS:
  - Arrow Up/Down: Navigate the list (and scroll the file viewer)
  - Enter: Open directory (navigate into it) or open the file viewer
  - Tab: Move focus between the browser and buttons
  - Esc: Go to parent directory (browser) / back to the browser (viewer)
  - "Quit" button: Exit application

HOW TO USE:
  1. Run: python filebrowsing.py [optional_path]
     - If no path given, starts at home directory (~/)
     - Can pass directory path: python filebrowsing.py /some/path
  2. Use arrow keys to select a file or directory
  3. Press Enter to navigate into a directory or read a file
  4. In the viewer: Up/Down/PgUp/PgDn scroll, Esc comes back

DESIGN PATTERNS DEMONSTRATED:
  - Sizing model: page(0.7, 0.8) — fractions, FIXED height (the browser fills the window)
  - win.fill_with(FileBrowser, ...) — the window knows its own interior, so the
    caller passes only content arguments: created, sized, and added in one call
  - Composite contrib widget (FileBrowser) navigating in place — no view rebuilds
  - TextView for file contents (scrollable, word-wrapped)
  - push_view/pop_view drill-down (browser → file viewer → back)
  - Builder-based views with app-held state: the current directory lives on the app
    (via on_dir_change), so a terminal resize rebuilds the view *in the same place*
  - Custom Esc handler per view (up a directory vs. back)
"""

import pathlib

# Run from anywhere (e.g. `python filebrowsing.py`): put the repo root on the import path.
from cookieui import (TextView, TuiApp, FileBrowser,
                      bind_key, bind_quit)
from cookieui.core.event import KeyType


def read_text(path: pathlib.Path):
    """File contents as text, or None for binary/unreadable files."""
    try:
        with open(path, 'rb') as f:
            if b'\x00' in f.read(4096):
                return None  # Binary file
        return path.read_text(errors='ignore')
    except Exception:
        return None


class FileBrowsingApp(TuiApp):
    """File browser app built on the contrib `FileBrowser` widget.

    Navigation happens inside the widget (no view rebuilds) — entering a directory just
    refreshes the listing in place. Selecting a text file opens it in a TextView.
    """

    AUTO_QUIT = False   # Esc goes up a directory, not quit

    def __init__(self, path: pathlib.Path = None):
        self._dir = path or pathlib.Path.home()   # state first — build_view needs it;
        super().__init__()                        # auto-pushes build_view (AUTO_VIEW)

    def build_view(self):
        page = self.page(0.7, 0.8, title='File Browser')

        # fill_with: the window knows its own interior — created, sized, added in one call.
        # The widget shows the current directory as its title and navigates in place;
        # on_dir_change keeps self._dir current so a resize rebuild stays in place.
        self.browser = page.fill_with(FileBrowser, self._dir,
                                      on_select=self.open_file,
                                      on_dir_change=self._remember_dir)

        page.footer([('Up', self.go_up), ('Quit', self.quit)])
        bind_key(page.view, KeyType.ESCAPE, self.go_up)   # Esc = up a directory
        self.status_bar(page.view, 'Up/Down navigate  Enter open  Tab focus  Esc up')
        return page

    def build_viewer(self, path: pathlib.Path, text: str):
        """Pushed view: the file's contents in a scrollable, word-wrapped TextView."""
        page = self.page(0.8, 0.9, title=path.name)
        page.fill_with(TextView, text)       # created, sized, added — no geometry

        page.footer([('Back', self.pop_view), ('Quit', self.quit)])
        bind_quit(page.view, self.pop_view)  # Esc/q = back to the browser
        self.status_bar(page.view, 'Up/Down/PgUp/PgDn scroll  Esc back')
        return page

    def open_file(self, path: pathlib.Path):
        text = read_text(path)
        if text is None:
            size = path.stat().st_size
            self.show_message('File Info', f'  {path.name}\n\n  Binary file — {size:,} bytes')
            return
        self.push_view(lambda: self.build_viewer(path, text))

    def _remember_dir(self, d: pathlib.Path):
        self._dir = d

    def go_up(self):
        d = self.browser.current_dir
        if d.parent != d:
            self.browser.open_dir(d.parent)


if __name__ == '__main__':
    FileBrowsingApp().run()

#!/usr/bin/env python3
"""CookieUI Git Log Viewer — Explore git commit history and view commit details.

OVERVIEW:
  A TUI for browsing git repository history. View the last 100 commits with
  hashes and messages, and inspect detailed commit information including
  file changes and diffs.

FEATURES:
  - Commit list: Shows last 100 commits with shortened hash and message
  - Branch display: Shows current branch name and total commit count
  - Commit details: "Show"/Enter opens the full `git show --stat` output in a
    scrollable TextView — the whole diff stat, no truncation
  - Error handling: Gracefully handles missing git or invalid repositories

KEYBOARD CONTROLS:
  - Arrow Up/Down: Navigate commit list (and scroll the commit detail view)
  - Enter: Open detailed commit view
  - Tab: Move focus between listbox and buttons
  - Esc/q: Back from the detail view; quit from the log view

HOW TO USE:
  1. Run from a git repository: python gitlog.py
  2. Optionally pass repo path: python gitlog.py /path/to/repo
  3. Use arrow keys to navigate commit history
  4. Press Enter or click "Show" — the full commit detail opens in its own view;
     scroll with Up/Down/PgUp/PgDn, press Esc to come back

DESIGN PATTERNS DEMONSTRATED:
  - Sizing model: page(0.8, 0.75) — fractions, FIXED height (the commit list fills
    the window); lay.listbox() with no size fills down to the footer buttons
  - External command integration (subprocess.check_output for git)
  - win.fill_with(TextView, output, wrap=False) — the commit view's whole body in
    one call: the window supplies position/size, the caller supplies content
  - push_view/pop_view drill-down navigation (log → commit detail → back)
  - bind_quit(view, self.pop_view): Esc means "back" on the pushed view only
  - Listbox rows carrying values: (label, full_hash) pairs, read via selected_value
  - Builder-based views → automatic rebuild on terminal resize
"""

import pathlib
import subprocess

# Run from anywhere (e.g. `python gitlog.py`): put the repo root on the import path.
import sys, pathlib
from cookieui import TextView, TuiApp, bind_enter_action, bind_quit


def git_run(*args, cwd=None):
    try:
        out = subprocess.check_output(['git'] + list(args), cwd=cwd,
                                      text=True, stderr=subprocess.PIPE)
        return out, None
    except subprocess.CalledProcessError as e:
        return '', e.stderr
    except FileNotFoundError:
        return '', 'git not found'


def load_log(repo):
    out, err = git_run('log', '--oneline', '--no-color', '-100', cwd=repo)
    if err:
        return None, err
    commits = []
    for line in out.splitlines():
        parts = line.split(' ', 1)
        if len(parts) == 2:
            commits.append((parts[0], parts[1]))
    return commits, None


def load_show(hash_val, repo):
    out, err = git_run('show', '--stat', '--no-color', hash_val, cwd=repo)
    return out, err


def load_branch(repo):
    out, _ = git_run('rev-parse', '--abbrev-ref', 'HEAD', cwd=repo)
    return (out or '?').strip()


class GitLog(TuiApp):
    """Git log viewer application."""

    def __init__(self, repo: pathlib.Path = None):
        self.repo = repo or pathlib.Path.cwd()   # state first — build_view needs it
        super().__init__()                       # auto-pushes build_view (AUTO_VIEW)

    def build_view(self):
        repo = self.repo
        commits, err = load_log(repo)

        if err:
            # Error case — page.label clips at draw time, no [:iw - 4] eyeballing
            page = self.page(0.8, 0.75, title='Git Log', pad_x=0)
            page.label(f'Error: {err}')
            page.footer([('Quit', self.quit)])
            return page

        # Success case — fractional size; fixed height because the listbox fills it
        page = self.page(0.8, 0.75, title=f'Git Log — {repo.name}', pad_x=0)

        branch = load_branch(repo)
        page.label(f'Branch: {branch}  |  {len(commits)} commit(s)')

        lb = page.listbox()                 # no height: auto-fills down to the footer buttons
        lb.items = [(f'{h[:8]}  {s}', h) for h, s in commits]   # value = full hash

        def do_show():
            hash_val = lb.selected_value
            if hash_val is None:
                return
            out, err = load_show(hash_val, repo)
            if err:
                self.show_message('Error', err[:100])
                return
            # Full output in a scrollable TextView — no truncation needed
            self.push_view(lambda: self.build_commit_view(hash_val, out))

        # Footer buttons with inline callbacks (do_show defined above)
        page.footer([('Show', do_show), ('Quit', self.quit)])

        bind_enter_action(lb, do_show)

        # Status bar
        self.status_bar(page.view, 'Up/Down scroll  Enter show  Tab focus  Esc quit')
        return page

    def build_commit_view(self, hash_val: str, output: str):
        """Pushed view: the entire `git show --stat` output, scrollable."""
        page = self.page(0.85, 0.9, title=f'Commit {hash_val[:8]}')
        page.fill_with(TextView, output, wrap=False)  # created, sized, added — no geometry

        page.footer([('Back', self.pop_view), ('Quit', self.quit)])
        bind_quit(page.view, self.pop_view)  # Esc/q go back to the log, not quit
        self.status_bar(page.view, 'Up/Down/PgUp/PgDn scroll  Esc back')
        return page


if __name__ == '__main__':
    GitLog().run()

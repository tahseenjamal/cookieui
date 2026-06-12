#!/usr/bin/env python3
"""CookieUI System Information Dashboard — Display system metrics and configuration.

OVERVIEW:
  A real-time system information dashboard showing hardware, OS, Python details,
  and disk usage across key directories. Useful for quick system status checks.

FEATURES:
  - System info: Hostname, OS, architecture, Python version, CPU cores
  - User info: Current user, home directory, working directory
  - Disk usage: Visual progress bars for home directory and root filesystem
  - Live refresh: Press 'r' to update all information
  - Timestamp: Shows when information was last collected
  - Graceful degradation: Handles missing disk mount points

KEYBOARD CONTROLS:
  - r: Refresh all system information
  - q: Quit application
  - Tab: Move focus to buttons
  - Click "Refresh": Same as pressing 'r'
  - Click "Quit": Exit application

HOW TO USE:
  1. Run: python sysinfo.py
  2. See system information displayed instantly
  3. Press 'r' or click "Refresh" to update values
  4. Watch disk usage bars:
     - [████████░░░░░░░░░░] format
     - Shows percentage and GB used/total
  5. Press 'q' or click "Quit" to exit

INFORMATION DISPLAYED:
  - Hostname: Computer name
  - OS: Operating system and kernel version
  - Arch: CPU architecture (arm64, x86_64, etc.)
  - Python: Version of Python running the app
  - CPU cores: Number of CPU cores available
  - User: Current logged-in user
  - Home: User's home directory
  - Working dir: Current working directory
  - Disk Usage: Two bars (home directory and root filesystem)
  - Updated: Timestamp of last refresh

DESIGN PATTERNS DEMONSTRATED:
  - Content-fit window: page(0.65) with NO height — the window wraps however many
    info rows + disk bars the machine has; add a row and the window grows itself
  - In a content-fit window the buttons flow with the content (lay.buttons), since
    there is no fixed bottom edge to pin footer_buttons to
  - spacing=0 layout: labels stack in consecutive rows, no manual row += 1 walking
  - In-place refresh: refresh() just assigns lbl.text — the next tick redraws;
    lay.label() clips at draw time, so refresh never slices text to fit
  - bind_key(view, KeyType.CHAR, refresh, char='r') — a one-line keyboard shortcut
  - System information collection (socket, platform, shutil modules)
  - Error handling for inaccessible mount points
"""

import socket
import platform
import sys
import os
import pathlib
import getpass
import shutil
import datetime

import sys, pathlib
from cookieui import TuiApp, bind_key
from cookieui.core.event import KeyType


def collect_info():
    info = {
        'Hostname': socket.gethostname(),
        'OS': f'{platform.system()} {platform.release()}',
        'Arch': platform.machine(),
        'Python': sys.version.split()[0],
        'CPU cores': str(os.cpu_count() or '?'),
        'User': getpass.getuser(),
        'Home': str(pathlib.Path.home()),
        'Working dir': str(pathlib.Path.cwd()),
    }
    return info


def collect_disks():
    results = []
    for path in [pathlib.Path.home(), pathlib.Path('/')]:
        try:
            usage = shutil.disk_usage(path)
            pct = usage.used / usage.total
            free = usage.free / (1024 ** 3)
            total = usage.total / (1024 ** 3)
            results.append((str(path), pct, f'{free:.1f}/{total:.1f} GB'))
        except OSError:
            pass
    return results


class SysInfo(TuiApp):
    """System information dashboard application.

    No __init__ needed: TuiApp pushes build_view automatically (AUTO_VIEW).
    """

    def build_view(self):
        # No geometry numbers: width is a fraction, height wraps the content, and
        # spacing=0 stacks the labels in consecutive rows (no manual row += 1 walking).
        # lay.label() clips at draw time, so refresh() never slices text.
        page = self.page(0.65, title='System Info', pad_x=0, spacing=0)

        # Build the static structure once with empty value labels; refresh() fills them.
        self._info_labels = {key: page.label('') for key in collect_info()}

        page.gap()
        self._disk_labels = []
        disks = collect_disks()
        if disks:
            page.label('Disk Usage:', bold=True)
            self._disk_labels = [page.label('') for _ in disks]

        page.gap()
        self._updated = page.label('', dim=True)

        page.gap()
        # Content-fit window → buttons flow with the content (footer needs
        # a fixed height; page.buttons is the natural form-style row here)
        page.buttons([('Refresh', self.refresh), ('Quit', self.quit)])
        self.status_bar(page.view, 'r refresh  q quit  Tab focus')
        bind_key(page.view, KeyType.CHAR, self.refresh, char='r')

        self.refresh()       # populate values — no view rebuild
        return page

    def refresh(self):
        """Update label text in place; the run loop redraws on the next tick.
        Labels were built with max_width, so no manual slicing here."""
        for key, val in collect_info().items():
            if key in self._info_labels:
                self._info_labels[key].text = f'{key:12}: {val}'
        for lbl, (_path, pct, text) in zip(self._disk_labels, collect_disks()):
            filled = int(20 * pct)
            bar = '[' + '█' * filled + '░' * (20 - filled) + ']'
            lbl.text = f'{bar} {pct*100:.0f}%  {text}'
        self._updated.text = 'Updated: ' + datetime.datetime.now().strftime('%H:%M:%S')


if __name__ == '__main__':
    SysInfo().run()

import os
import sys
import tty
import termios
import signal
import select
from typing import Optional, Callable

from .event import Key, KeyType


class Terminal:
    def __init__(self):
        # Headless-safe: stdin may be a pseudofile with no fileno (pytest capture,
        # pipes). Construction must always succeed — only setup()/read_key() need a
        # real terminal, and they're only reached via run().
        try:
            self._fd = sys.stdin.fileno()
        except (ValueError, OSError):
            self._fd = -1
        self._saved_attrs = None
        self.width = 80
        self.height = 24
        self._on_resize: Optional[Callable[[int, int], None]] = None
        self._update_size()

    def _update_size(self):
        if self._fd < 0:
            return
        try:
            sz = os.get_terminal_size(self._fd)
            self.width = sz.columns
            self.height = sz.lines
        except OSError:
            pass

    def setup(self, on_resize: Optional[Callable[[int, int], None]] = None):
        self._on_resize = on_resize
        self._saved_attrs = termios.tcgetattr(self._fd)
        tty.setraw(self._fd)
        sys.stdout.write('\x1b[?1049h'   # alternate screen
                         '\x1b[?25l'     # hide cursor
                         '\x1b[2J')      # clear screen
        sys.stdout.flush()
        signal.signal(signal.SIGWINCH, self._sigwinch)

    def teardown(self):
        signal.signal(signal.SIGWINCH, signal.SIG_DFL)
        sys.stdout.write('\x1b[?25h'     # show cursor
                         '\x1b[?1049l')  # main screen
        sys.stdout.flush()
        if self._saved_attrs is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved_attrs)

    def _sigwinch(self, _signum, _frame):
        self._update_size()
        if self._on_resize:
            self._on_resize(self.width, self.height)

    def _readb(self, n: int = 1, timeout: float = 0.05) -> Optional[bytes]:
        r, _, _ = select.select([self._fd], [], [], timeout)
        if not r:
            return None
        return os.read(self._fd, n)

    def read_key(self, timeout: float = 0.05) -> Optional[Key]:
        data = self._readb(1, timeout)
        if data is None:
            return None

        b = data[0]

        if b == 0x1b:
            return self._parse_escape()
        if b in (0x0d, 0x0a):
            return Key(KeyType.ENTER)
        if b in (0x7f, 0x08):
            return Key(KeyType.BACKSPACE)
        if b == 0x09:
            return Key(KeyType.TAB)
        if b < 0x20:
            return Key(KeyType.UNKNOWN, chr(b))

        # ASCII
        if b < 0x80:
            return Key(KeyType.CHAR, chr(b))

        # Multi-byte UTF-8
        if   b & 0xE0 == 0xC0: n_more = 1
        elif b & 0xF0 == 0xE0: n_more = 2
        elif b & 0xF8 == 0xF0: n_more = 3
        else:                   return Key(KeyType.UNKNOWN)

        rest = b''
        for _ in range(n_more):
            more = self._readb(1, 0.1)
            if more is None:
                break
            rest += more

        try:
            return Key(KeyType.CHAR, (bytes([b]) + rest).decode('utf-8'))
        except UnicodeDecodeError:
            return Key(KeyType.UNKNOWN)

    def _parse_escape(self) -> Key:
        nxt = self._readb(1, 0.05)
        if nxt is None:
            return Key(KeyType.ESCAPE)
        if nxt == b'[':
            return self._parse_csi()
        if nxt == b'O':
            return self._parse_ss3()
        return Key(KeyType.ESCAPE)

    def _parse_csi(self) -> Key:
        buf = b''
        while True:
            ch = self._readb(1, 0.05)
            if ch is None:
                break
            buf += ch
            if 0x40 <= ch[0] <= 0x7E:
                break

        seq = buf.decode('ascii', errors='replace')
        _MAP = {
            'A': KeyType.UP,    'B': KeyType.DOWN,
            'C': KeyType.RIGHT, 'D': KeyType.LEFT,
            'H': KeyType.HOME,  'F': KeyType.END,
            'Z': KeyType.SHIFT_TAB,
        }
        if seq in _MAP:
            return Key(_MAP[seq])

        _TILDE = {
            '3~': KeyType.DELETE,
            '5~': KeyType.PAGE_UP,  '6~': KeyType.PAGE_DOWN,
            '1~': KeyType.HOME,     '4~': KeyType.END,
            '7~': KeyType.HOME,     '8~': KeyType.END,
        }
        if seq in _TILDE:
            return Key(_TILDE[seq])

        return Key(KeyType.UNKNOWN)

    def _parse_ss3(self) -> Key:
        ch = self._readb(1, 0.05)
        if ch is None:
            return Key(KeyType.UNKNOWN)
        _MAP = {
            ord('A'): KeyType.UP,    ord('B'): KeyType.DOWN,
            ord('C'): KeyType.RIGHT, ord('D'): KeyType.LEFT,
            ord('H'): KeyType.HOME,  ord('F'): KeyType.END,
        }
        return Key(_MAP.get(ch[0], KeyType.UNKNOWN))

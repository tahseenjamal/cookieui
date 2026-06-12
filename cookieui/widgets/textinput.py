import threading
import time

from .base import Widget
from ..core.event import Key, KeyType


class TextInput(Widget):
    """Newt-style entry field.

    Two-line layout when a label is given:
        line 0:  label text   (text_dim on window surface — inherits bg)
        line 1:  entry field  (entry_fg on input_bg, underscores fill empty space)

    One-line when no label.
    Password mode replaces visible chars with '*'.
    """
    focusable = True

    def __init__(self, x: int, y: int, width: int,
                 label: str = '',
                 password: bool = False,
                 placeholder: str = '',
                 on_enter=None,
                 on_change=None):
        height = 2 if label else 1
        super().__init__(x, y, width, height)
        self.label       = label
        self.password    = password
        self.placeholder = placeholder
        self.on_enter    = on_enter   # fn() called when Enter is pressed
        self.on_change   = on_change  # fn(value) after every user edit — live filtering
        self.value       = ''
        self._cursor     = 0
        self._scroll     = 0
        self._blink_visible = True  # Cursor blink state
        self._blink_thread = None   # Blink animation thread

    def set_value(self, value: str, cursor: int = None) -> None:
        """Set the text and place the cursor (at the end by default), syncing scroll —
        so callers never poke `value`/`_cursor`/`_scroll` separately."""
        self.value   = str(value)
        self._cursor = len(self.value) if cursor is None else max(0, min(cursor, len(self.value)))
        self._sync_scroll()

    def clear(self) -> None:
        """Reset the field — value, cursor, and scroll together."""
        self.set_value('')

    def _fire_change(self):
        """Run on_change with the new value. Fires only on *user edits* (typing,
        backspace, delete) — never on cursor moves or programmatic set_value/clear,
        so an on_change that calls set_value can't loop."""
        if self.on_change:
            self.on_change(self.value)

    def _sync_scroll(self):
        if self._cursor < self._scroll:
            self._scroll = self._cursor
        elif self._cursor >= self._scroll + self.width:
            self._scroll = self._cursor - self.width + 1

    def _start_blink(self):
        """Start cursor blink animation if not already running."""
        if self._blink_thread is None or not self._blink_thread.is_alive():
            self._blink_visible = True
            def blink_loop():
                while self.focused:
                    time.sleep(0.5)  # 500ms on, 500ms off = 1Hz blink rate
                    if self.focused:  # Check again before toggling
                        self._blink_visible = not self._blink_visible
            self._blink_thread = threading.Thread(target=blink_loop, daemon=True)
            self._blink_thread.start()

    def _stop_blink(self):
        """Stop cursor blink animation."""
        self._blink_visible = True  # Ensure cursor is visible when unfocused

    def draw(self, screen, theme):
        row = self.y
        t   = theme

        # Label row — plain text only, no Nerd Font icon prefix.
        # Icons are double-width in most terminals but counted as 1-char in
        # Python len(), which shifts the entry field below by one visual column.
        if self.label:
            lbl = f'{self.label}:'
            fg  = t.title_fg if self.focused else t.text_dim
            screen.write_over(self.x, row, lbl[:self.width], fg=fg, bold=self.focused)
            row += 1

        # Entry field
        visible = self.value[self._scroll: self._scroll + self.width]
        if self.password:
            display = '*' * len(visible)
        else:
            display = visible

        # Pad to full width with the theme's entry fill (Newt underscores)
        padded = display + t.entry_fill * (self.width - len(display))

        # Show placeholder when empty and unfocused
        if not self.value and not self.focused and self.placeholder:
            padded = (self.placeholder[:self.width]).ljust(self.width, t.entry_fill)

        screen.write(self.x, row, padded,
                     fg=t.entry_fg, bg=t.input_bg)

        # Blinking block cursor at current position
        if self.focused:
            self._start_blink()  # Ensure blink animation is running
            if self._blink_visible:  # Only show cursor during visible phase
                cx = self._cursor - self._scroll
                if 0 <= cx < self.width:
                    ch = padded[cx] if cx < len(padded) else t.entry_fill
                    screen.put(self.x + cx, row, ch,
                               fg=t.input_cursor_fg, bg=t.input_cursor_bg)
        else:
            self._stop_blink()  # Stop blinking when unfocused

    def handle_key(self, key: Key) -> bool:
        kt = key.type
        if kt == KeyType.CHAR and key.is_printable():
            self.value    = self.value[:self._cursor] + key.char + self.value[self._cursor:]
            self._cursor += 1
            self._sync_scroll()
            self._fire_change()
            return True
        if kt == KeyType.BACKSPACE:
            if self._cursor > 0:
                self.value    = self.value[:self._cursor - 1] + self.value[self._cursor:]
                self._cursor -= 1
                self._sync_scroll()
                self._fire_change()
            return True
        if kt == KeyType.DELETE:
            if self._cursor < len(self.value):
                self.value = self.value[:self._cursor] + self.value[self._cursor + 1:]
                self._fire_change()
            return True
        if kt == KeyType.LEFT:
            self._cursor = max(0, self._cursor - 1);  self._sync_scroll(); return True
        if kt == KeyType.RIGHT:
            self._cursor = min(len(self.value), self._cursor + 1); self._sync_scroll(); return True
        if kt == KeyType.HOME:
            self._cursor = 0; self._sync_scroll(); return True
        if kt == KeyType.END:
            self._cursor = len(self.value); self._sync_scroll(); return True
        if kt == KeyType.ENTER and self.on_enter:
            self.on_enter(); return True
        return False

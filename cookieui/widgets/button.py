from typing import Optional, Callable
import threading
import time

from .base import Widget
from ..core.event import Key, KeyType


class Button(Widget):
    """Newt-style button: 3-line tall with red border and background.

    When Enter is pressed, button shows pressed state (colors invert) for ~150ms
    before executing the callback, providing tactile visual feedback.
    """
    focusable = True

    def __init__(self, x: int, y: int, label: str,
                 icon: str = '',
                 on_click: Optional[Callable[[], None]] = None,
                 shadow: bool = True):
        self.label      = label
        self.icon       = icon
        self._on_click  = on_click
        self._pressed   = False  # Visual pressed state
        self.shadow     = shadow  # Draw shadow or not

        # Add spaces around label for padding
        self._content  = f' {label} '
        # width: '│' + content + padding + '│'
        content_width  = len(self._content)
        super().__init__(x, y, max(12, content_width + 4), 3)

    @property
    def on_click(self):
        return self._on_click

    @on_click.setter
    def on_click(self, fn):
        self._on_click = fn

    def draw(self, screen, theme):
        """Draw the button. The face (3 rows: borders + label, colors, focus
        treatment) comes from the theme's chrome; this method owns position
        shifting and the pressed-state offset."""
        # Adjust position to keep button and shadow within screen bounds
        draw_x = self.x
        draw_y = self.y

        # If button + shadow would exceed right edge, shift left
        if draw_x + self.width >= screen.width:
            draw_x = max(0, screen.width - self.width - 1)

        # If button + shadow would exceed bottom edge, shift up
        if draw_y + 3 >= screen.height:  # Button is 3 lines + 1 for shadow
            draw_y = max(0, screen.height - 3 - 1)

        # When pressed, shift button position down by 1 to cover shadow, emulating press
        if self._pressed:
            draw_y += 1

        theme.chrome.button_face(screen, theme, self.x, draw_y, self.width,
                                 self._content, focused=self.focused)

        # Drop shadow — disappears when pressed, creating the sunken effect
        # Only draw if shadow is enabled and won't exceed screen bounds
        if (self.shadow and not self._pressed and
            self.x + self.width < screen.width and
            self.y + 3 < screen.height):
            theme.chrome.shadow(screen, theme, self.x, self.y, self.width, 3)

    def handle_key(self, key: Key) -> bool:
        # Only Enter activates buttons (not Space)
        if key.type == KeyType.ENTER:
            # Show pressed state, then execute callback after brief delay
            self._pressed = True

            # Use daemon thread to handle the delay and callback without blocking
            def press_and_execute():
                time.sleep(0.15)  # 150ms pressed state
                self._pressed = False
                if self._on_click:
                    self._on_click()

            thread = threading.Thread(target=press_and_execute, daemon=True)
            thread.start()
            return True

        return False

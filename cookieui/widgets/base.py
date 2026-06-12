from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.screen import Screen
    from ..core.event  import Key
    from ..theme       import Theme


class Widget(ABC):
    focusable = True   # subclasses that are purely visual should set False

    def __init__(self, x: int, y: int, width: int, height: int):
        self.x       = x
        self.y       = y
        self.width   = width
        self.height  = height
        self.focused = False
        self.visible = True

    @abstractmethod
    def draw(self, screen: 'Screen', theme: 'Theme') -> None: ...

    def handle_key(self, key: 'Key') -> bool:
        """Return True if the key event was consumed."""
        return False

    def on_focus(self):
        self.focused = True

    def on_blur(self):
        self.focused = False

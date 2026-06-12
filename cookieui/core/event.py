from enum import Enum, auto


class KeyType(Enum):
    CHAR       = auto()
    UP         = auto()
    DOWN       = auto()
    LEFT       = auto()
    RIGHT      = auto()
    ENTER      = auto()
    BACKSPACE  = auto()
    DELETE     = auto()
    TAB        = auto()
    SHIFT_TAB  = auto()
    ESCAPE     = auto()
    HOME       = auto()
    END        = auto()
    PAGE_UP    = auto()
    PAGE_DOWN  = auto()
    UNKNOWN    = auto()


class Key:
    __slots__ = ('type', 'char')

    def __init__(self, key_type: KeyType, char: str = ''):
        self.type = key_type
        self.char = char

    def is_printable(self) -> bool:
        return self.type == KeyType.CHAR and bool(self.char) and self.char.isprintable()

    def __repr__(self):
        if self.type == KeyType.CHAR:
            return f'Key.CHAR({self.char!r})'
        return f'Key.{self.type.name}'

from enum import Enum, StrEnum, auto

class CmlTokenType(Enum):
    L_BRACKET = auto()
    R_BRACKET = auto()
    STRING = auto()
    BOOL = auto()
    NUMBER = auto()
    IDENTIFIER = auto()
    POINTER = auto()
    EQU = auto()
    VALUE = auto()
    COMMENT = auto()

class CmlTokenize():
    def __init__(self, token: dict, /) -> None:
        self.token = token

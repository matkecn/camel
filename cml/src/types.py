from enum import Enum, StrEnum, auto
from typing import Any

class CamelTokenTypes(Enum):
    NUMBER = auto()
    STRING = auto()
    BOOLEAN = auto()
    NULL = auto()
    UNDEFINED = auto()

class CamelTokenIdentifiers(Enum):
    GLOBAL = auto()
    POINTER = auto()
    VAR = auto()
    L_B = auto()
    R_B = auto()
    COMMA = auto()
    EQU = auto()
    COMMENT = auto()
    NL = auto()

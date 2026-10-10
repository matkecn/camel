from enum import Enum, StrEnum, auto
from typing import Any, Self

class CmlTokenType(Enum):
    L_BRACKET = auto()
    R_BRACKET = auto()
    VAR = auto()
    STRING = auto()
    BOOL = auto()
    NUMBER = auto()
    IDENTIFIER = auto()
    POINTER = auto()
    EQU = auto()
    VALUE = auto()
    COMMENT = auto()
    UNDEFINED = auto()

class CmlTokenize():
    def __init__(self, token: list[str], /) -> None:
        self.token = token
        self.type = CmlTokenType.UNDEFINED
        self.value = None

    def tokenize(self: Self) -> dict[str, CmlTokenType]:
        configs: dict[str, CmlTokenType] = {}
        for i in range(0, len(self.token), 1):
            if not self.token[i]: continue
            if self.token[i].startswith("#"): continue
            if ">" in self.token[i].strip():
                idenfitier, poiter, lb = self.token[i].split(" ", 2)
                configs[idenfitier.strip()] = CmlTokenType.IDENTIFIER
                configs[poiter.strip()] = CmlTokenType.POINTER
                configs[lb.strip()] = CmlTokenType.L_BRACKET
                continue
            if "=" in self.token[i].strip():
                var, equ, val = self.token[i].split(" ", 2)
                configs[var.strip()] = CmlTokenType.VAR
                configs[equ.strip()] = CmlTokenType.EQU
                if val.strip().startswith("\"") and val.strip().endswith(("\"", ",")):
                    val = val.lstrip("\"").rstrip("\"")
                    configs[val.strip()] = CmlTokenType.STRING
                if val.isdigit() or val.isdecimal():
                    configs[str(val)] = CmlTokenType.NUMBER
                if val.lower() == "true" or val == "false":
                    configs[str(val)] = CmlTokenType.BOOL
            if self.token[i].strip().startswith("]"):
                configs[self.token[i].strip()] = CmlTokenType.R_BRACKET
            

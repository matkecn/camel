lazy import oxide
from enum import Enum, StrEnum, auto
from typing import Any, Self

class CmlTokenType(Enum):
    L_BRACKET = auto()
    R_BRACKET = auto()
    PROPERTY = auto()
    BREAK = auto()
    STRING = auto()
    BOOL = auto()
    NUMBER = auto()
    SCOPE = auto()
    POINTER = auto()
    EQU = auto()
    VALUE = auto()
    COMMENT = auto()
    UNDEFINED = auto()

class CamelTokenizer():
    def __init__(self, token: list[str], /) -> None:
        self.token = token
        self.type = CmlTokenType.UNDEFINED
        self.value = None
    
    def tokenize(self: Self) -> list[tuple]:
        tokens: list[tuple] = []
        for index in range(0, len(self.token), 1):
            tkn = self.token[index].strip()
            if not tkn: continue
            if tkn.startswith("#"): continue
            if ">" in tkn:
                identifier, p, lb = tkn.split(" ", 2)
                tokens.append((identifier, CmlTokenType.SCOPE))
                del p, lb
                continue
            if "=" in tkn:
                var, equ, val = tkn.split(" ", 2)
                tokens.append((var, CmlTokenType.PROPERTY))
                del equ
                if val.strip().startswith("\""):
                    tokens.append((val.strip(), CmlTokenType.STRING))
                    continue
                if val.strip().isdigit() or val.strip().isdecimal():
                    tokens.append((val.strip(), CmlTokenType.NUMBER))
                    continue
                if val.strip() == "true" or val.strip() == "false" or val.strip() == "null":
                    tokens.append((val.strip(), CmlTokenType.BOOL))
                    continue
            if "]" in tkn:
                tokens.append(("]", CmlTokenType.R_BRACKET))
                continue
        return tokens

    def tokenizeall(self: Self) -> list[tuple]:
        tokens: list[tuple] = []
        pass
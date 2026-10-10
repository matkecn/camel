import oxide
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

class CamelTokenizer():
    def __init__(self, token: list[str], /) -> None:
        self.token = token
        self.type = CmlTokenType.UNDEFINED
        self.value = None

    def tokenizeall(self: Self) -> dict[str, CmlTokenType]:
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
                    val = val.lstrip("\"").rstrip("\"").rstrip("\",")
                    configs[val.strip()] = CmlTokenType.STRING
                if val.isdigit() or val.isdecimal():
                    configs[str(val)] = CmlTokenType.NUMBER
                if val.lower() == "true" or val == "false":
                    configs[str(val)] = CmlTokenType.BOOL
                continue
            if self.token[i].strip().startswith("]"):
                configs[self.token[i].strip()] = CmlTokenType.R_BRACKET
                continue
        return configs

    def tokenize(self: Self):
        configs: dict[str, CmlTokenType] = {}
        for i in range(0, len(self.token), 1):
            if not self.token[i]: continue
            if self.token[i].strip().startswith("#"): continue
            if ">" and "[" in self.token[i].strip():
                identifier, pointer, lb = self.token[i].strip().split(" ", 2)
                configs[identifier.strip()] = CmlTokenType.IDENTIFIER
                configs[lb.strip()] = CmlTokenType.L_BRACKET
                del pointer
                continue
            if "=" in self.token[i].strip():
                var, equ, val = self.token[i].strip().split(" ", 2)
                configs[var.strip()] = CmlTokenType.VAR
                if val.strip().startswith("\"") and val.endswith(("\"", ",")):
                    if val.endswith(","):
                        val = val.strip(",")
                    val = val.strip("\"")
                    configs[val.strip()] = CmlTokenType.STRING
                    continue
                if val.isdigit() or val.isdecimal():
                    configs[str(val).strip()] = CmlTokenType.NUMBER
                    continue
                if val == "true" or val == "false" or val == "null":
                    configs[val.strip()] = CmlTokenType.BOOL
                    continue
            if self.token[i].strip().startswith("]"):
                configs[self.token[i].strip()] = CmlTokenType.R_BRACKET
                continue
        return configs

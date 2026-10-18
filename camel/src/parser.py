from typing import Self, Any
from .ids import Ids

class CamelParser():
    def __init__(self: Self, register: list[str]) -> None:
        self.register = register
        self.parse_object: dict[str, dict[str, str]] = {}

    @classmethod
    def new(cls, register: str) -> "CamelParser":
        return cls(register)

    def parse(self: Self) -> dict[str, dict[str, str]]:
        parsed: dict[str, dict[str, str]] = {}
        current_single = ""
        current_global = ""
        for i in range(0, len(self.register), 1):
            p = self.register[i].strip()
            if not p: continue
            if p.startswith(Ids.COMMENT): continue
            if p.startswith(Ids.SPECIAL):
                special, var, equ, val = p.split(" ", 3)
                del equ
                current_single = str(special)
                parsed.setdefault(current_single, {})
                parsed[current_single][str(var).strip()] = str(val).rstrip("\"").lstrip("\"")
                continue
            if ">" in p:
                identifier, pointer, lb = p.split(" ", 2)
                del pointer, lb
                current_global = str(identifier)
                parsed[current_global] = {}
                continue
            if "=" in p:
                var, equ, val = p.split(" ", 2)
                del equ
                parsed[current_global].update({
                    str(var): val.rstrip(",").strip("\"")
                })
            if p.startswith("]"): continue
        del current_global
        return parsed

    def parse_var(self: Self, var: str) -> dict[str, str]:
        pvar = {}
        if "=" in var:
            name, equ, value = var.split(" ", 2)
            del equ
            pvar[name] = value
        return pvar
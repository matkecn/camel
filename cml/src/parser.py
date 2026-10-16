from typing import Self, Any

class CamelParser():
    def __init__(self: Self, register: list[str]) -> None:
        self.register = register
        self.parse_object: dict[str, dict[str, str]] = {}

    @classmethod
    def new(cls, register: str) -> "CamelParser":
        return cls(register)

    def parse(self: Self) -> dict[str, dict[str, str]]:
        parsed: dict[str, dict[str, str]] = {}
        current_global = ""
        for i in range(0, len(self.register), 1):
            p = self.register[i].strip()
            if not p: continue
            if p.startswith("#"): continue
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
        return parsed
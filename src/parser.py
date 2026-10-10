from typing import Self, Any

class CamelParser():
    def __init__(self: Self, register: str) -> None:
        self.register = register

    @classmethod
    def new(cls, register: str) -> "CamelParser":
        return cls(register)

    

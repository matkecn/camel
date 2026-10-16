from typing import (
    Self
)

class CamelReader():
    def __init__(self: Self, path: str) -> None:
        self._path = path

    @classmethod
    def new(cls, path: str) -> "CamelReader":
        return cls(path)

    def readall(self: Self) -> list[str]:
        content = []
        if not isinstance(self._path, str):
            return []
        try:
            with open(self._path, "r") as file:
                lines = file.readlines()
                for line in lines:
                    line = line.strip()
                    content.append(line)
                    continue
            return content
        except FileNotFoundError:
            return []

    def sread(self: Self) -> list[str]: pass


    def readline(self: Self, hint: int) -> str | None:
        if hint < 1:
            return None
        L: str | None = None
        try:
            with open(self._path, "r") as file:
                lines = file.readlines()
                L = lines[hint-1]
            return L
        except FileNotFoundError:
            return None
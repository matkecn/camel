from typing import (
    Self
)

from .exceptions import die

lazy import oxide

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

    def spaceread(self: Self) -> list[str] | None:
        content = []
        if not isinstance(self._path, str):
            return []
        try:
            with open(self._path, "r") as file:
                rawlines = file.readlines()
                for line in rawlines:
                    content.append(line.strip())
            return content
        except FileNotFoundError as e:
            die(str(e), 1)
            return None

    def readline(self: Self, hint: int) -> str | None:
        if hint < 1:
            return None
        L: str | None = None
        try:
            with open(self._path, "r") as file:
                lines = file.readlines()
                L = lines[hint-1].strip()
            return L
        except FileNotFoundError:
            return None

    def rawread(self: Self) -> list[str] | None:
        pass
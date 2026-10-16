from .tokenizer import CamelTokenizer, CmlTokenType
from .reader import CamelReader
from .parser import CamelParser
from .exceptions import die, rais
from .debug import console

lazy import oxide
lazy import typing

from typing import (
    Self, Unpack
)

from enum import Enum, auto

from oxide import (
    mastermethod,
    Vec,
    HashMap,
    HashSet,
    Some,
    Ok,
    Err,
    Error,
    println,
    Result,
    Option,
    None_
)

class CmlModes(Enum):
    READ = auto()
    MODIFY = auto()
    WRITE = auto()
    DELETE = auto()
    UNDEFINED = auto()

class Cml():
    __ver__ = "1.0.0"

    def __init__(
        self: Self,
        path: str,
        mode: CmlModes,
        /, *,
        exceptions: bool = False
    ) -> None:
        self._path = path
        self._mode = mode
        self._exceptions = exceptions
        self._connection = False
        self._data = []

    @mastermethod
    def get_version(cls, self: Self) -> str:
        return cls.__ver__

    @classmethod
    def new(cls, path: str, mode: CmlModes, /, *, exceptions: bool = False) -> "Cml":
        return cls(path, mode, exceptions)

    def is_connected(self: Self) -> bool:
        return self._connection

    def has_data(self: Self) -> bool:
        if len(self._data) > 0:
            return True
        else:
            return False

    def connect(self) -> bool:
        if not isinstance(self._path, str): return False
        if not self._data or len(self._data) == 0:
            try:
                with open(self._path, "r") as file:
                    content = file.readlines()
                    for c in content:
                        c = c.strip()
                        self._data.append(c)
                        continue
                self._connection = True
                return True
            except FileNotFoundError as _:
                return False
        else:
            return True

    def readall(self: Self) -> list[str] | None:
        if not self.is_connected(): return None
        try:
            reader = CamelReader(self._path)
        except (Exception, FileNotFoundError) as err:
            reader = None
            if not self._exceptions: return None
            else: raise Exception(str(err))
        content = reader.readall()
        return content

    def readline(self: Self, lid: int, /) -> str | None:
        if not self.has_data():
            return None
        if lid < 1:
            return None
        try:
            return self._data[lid-1]
        except IndexError as _:
            return None

    def get_global(self: Self, glob: str, /) -> dict[str, str] | None:
        if not self.is_connected():
            return None
        if not self.has_data():
            return None
        if not isinstance(glob, str):
            return None
        parser = CamelParser(self._data)
        pdata = parser.parse()
        components: dict[str, str] | None = None
        try:
            components = pdata[glob]
        except KeyError as _:
            return None

        if components is not None:
            return components
        else:
            return None

    def all_globals(self: Self) -> list[str] | None:
        if not self.is_connected(): return None
        if not self.has_data(): return None
        parser = CamelParser(self._data)
        pdata = parser.parse()
        _globals = []
        for k, _ in pdata.items():
            _globals.append(k)
        return _globals

    def group_all_keys(self: Self) -> dict[str, str]:

    # def find_section(self: Self, section: str) -> list[str]:
    #     # status = self.connect()
    #     # if not status: return []
    #     # tokenizer = CamelTokenizer(self._data)
    #     # tokens = tokenizer.tokenize()
    #     # sec = []
    #     # start = ""
    #     # for i in range(0, len(tokens), 1):
    #     #     if tokens[i][1] == CmlTokenType.IDENTIFIER:
    #     #         start = tokens[i][0]
    #     #         sec.append(self._data[i])
    #     #     if tokens[i][1] == CmlTokenType.R_BRACKET:
    #     #         sec.append(self._data[i])
    #     #         break
    #     # return sec
    #     status = self.connect()
    #     if not status:
    #         return None

    #     if not isinstance(section, str):
    #         console.log("Invalid type passed for \'section\'")
    #         return None

    #     tokenizer = CamelTokenizer(self._data)
    #     tokens = tokenizer.tokenize()
    #     found = False
    #     sectors = []
    #     i = 0

    #     while i <= len(tokens):
    #         if tokens[i][1] == CmlTokenType.IDENTIFIER:
    #             sectors.append()
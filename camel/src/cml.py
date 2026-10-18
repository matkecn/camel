from .tokenizer import CamelTokenizer, CmlTokenType
from .reader import CamelReader
from .parser import CamelParser
from .exceptions import die, rais
from .debug import console
from .ids import Ids

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
    __nam__ = "cml"
    __ext__ = ".cml"

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
        self._scopes = []
        self._data = []

    @mastermethod
    def get_version(cls, self: Self) -> str:
        return cls.__ver__

    def put_data(self: Self) -> list[str] | None:
        return self._data

    def put_scopes(self: Self) -> list[str]:
        return self._scopes

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
        if not self._path.endswith(".cml"): return False
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

    def spaceread(self: Self) -> list[str] | None:
        if not self.is_connected():
            return None
        try:
            reader = CamelReader(self._path)
        except (Exception, FileNotFoundError) as err:
            reader = None
            if not self._exceptions:
                return None
            else:
                raise Exception(str(err))
        content = reader.spaceread()
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

    def collectPropertiesFrom(self: Self, scope: str, /) -> dict[str, str] | None:
        if not self.is_connected():
            return None
        if not self.has_data():
            return None
        if not isinstance(scope, str):
            return None
        parser = CamelParser(self._data)
        pdata = parser.parse()
        components: dict[str, str] | None = None
        try:
            components = pdata[scope]
        except KeyError as _:
            return None

        if components is not None:
            return components
        else:
            return None

    def collectScopeNames(self: Self) -> bool:
        if not self.is_connected(): return False
        if not self.has_data(): return False
        parser = CamelParser(self._data)
        pdata = parser.parse()
        for k, _ in pdata.items():
            self._scopes.append(k)
        return True

    def getScopeNames(self: Self) -> list[str] | None:
        if not self.is_connected(): return False
        if not self.has_data(): return False
        parser = CamelParser(self.put_data())
        pdata = parser.parse()
        gs = []
        for k, _ in pdata.items():
            gs.append(k)
        return gs

    def collectPropertiesNamesFrom(self: Self, scope: str, /) -> list[str]:
        if not self.is_connected():
            return None
        parser = CamelParser(self.put_data())
        pdata = parser.parse()
        names = []
        prop = {}
        try:
            prop = pdata[scope]
        except KeyError as _:
            return None
        for k, _ in prop.items():
            names.append(k)
        return names

    def collectPropertiesValuesFrom(self: Self, scope: str, /) -> list[str]:
        if not self.is_connected():
            return None
        parser = CamelParser(self.put_data())
        pdata = parser.parse()
        names = []
        prop = {}
        try:
            prop = pdata[scope]
        except KeyError as _:
            return None
        for _, v in prop.items():
            names.append(v)
        return names

    def getPropertyFrom(self: Self, scope: str, prop: str, default: int = 1, /) -> str:
        if not self.is_connected():
            return None
        if not all(isinstance(argu, str) for argu in [scope, prop]):
            return None
        parser = CamelParser(self.put_data())
        pdata = parser.parse()
        target = {}
        try:
            target = pdata[scope]
        except KeyError as _:
            return default
        try:
            return target[prop]
        except KeyError as _:
            return default

    def findScope(self: Self, scope: str) -> int:
        if not self.is_connected():
            return -1
        if not isinstance(scope, str):
            return -1
        reader = CamelReader(self._path)
        data = reader.spaceread()
        if data is None: return None
        counter = 0
        while counter < len(data):
            if not data[counter].startswith(scope):
                counter += 1
            else: break
        counter = counter + 1
        return counter
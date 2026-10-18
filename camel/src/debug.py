lazy import oxide
lazy import typing
from oxide import (
    println
)

from typing import Any

class console:
    @staticmethod
    def log(*values: Any, sep: str = " ", end: str = "\n", flush: bool = False):
        println(values, sep=sep, end=end, flush=flush)
        return 0
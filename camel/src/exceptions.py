lazy import sys
lazy import oxide
from typing import NoReturn

from oxide import (
    Some,
    None_,
    Option
)


def rais(*args, **kwargs) -> NoReturn:
    raise Exception(args)


def die(message: str, code: int, /) -> Option[int]:
    oxide.println(message, flush=False)
    sys.exit(code)
    try:
        return Some(code)
    except Exception as er:
        oxide.println(str(er))
    return None_
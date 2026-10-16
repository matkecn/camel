import oxide
from enum import Enum, StrEnum, auto
from typing import Any, NoReturn

from oxide import (
    Result,
    Err,
    Error,
    Ok,
    Some,
    None_,
    Option,
    mastermethod
)

from oxide.decorators import (
    cache
)

@cache
def rais(*args, **kwargs) -> NoReturn:
    raise Exception(args)


def die(message: str, code: int, /) -> Option[int]:
    oxide.println(message, flush=False)
    try:
        return Some(code)
    except Exception as er:
        oxide.println(str(er))
    return None_
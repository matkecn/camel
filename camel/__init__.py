from __future__ import annotations

from .api import (
    Cml,
    append,
    change,
    dump,
    dumps,
    format_cml,
    from_dict,
    from_json,
    get,
    load,
    loads,
    merge,
    new,
    parse,
    parse_value,
    read,
    remove,
    sanitize,
    save,
    validate,
    write,
)
from .errors import (
    CmlError,
    CmlPathError,
    CmlRequiredError,
    CmlSyntaxError,
    CmlTypeError,
    CmlValidationError,
)
from .nodes import (
    Block,
    CmlDocument,
    CmlObject,
    CmlReference,
    Entry,
    Parent,
    Rule,
    RuleField,
    Scope,
)
from .sanitizer import Issue, SanitizeReport, check_type, coerce_value, infer_type, normalize_type
from .writer import dump as write_file
from .writer import dumps as format_text

__version__ = "1.0.0"
__author__ = "@matkecn"
__language__ = "CamelConfig"
__extension__ = ".cml"

__all__ = [
    "Block",
    "Cml",
    "CmlDocument",
    "CmlError",
    "CmlObject",
    "CmlPathError",
    "CmlReference",
    "CmlRequiredError",
    "CmlSyntaxError",
    "CmlTypeError",
    "CmlValidationError",
    "Entry",
    "Issue",
    "Parent",
    "Rule",
    "RuleField",
    "SanitizeReport",
    "Scope",
    "append",
    "change",
    "check_type",
    "coerce_value",
    "dump",
    "dumps",
    "format_cml",
    "format_text",
    "from_dict",
    "from_json",
    "get",
    "infer_type",
    "load",
    "loads",
    "merge",
    "new",
    "normalize_type",
    "parse",
    "parse_value",
    "read",
    "remove",
    "sanitize",
    "save",
    "validate",
    "write",
    "write_file",
]

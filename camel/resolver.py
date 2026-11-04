from __future__ import annotations

import os
from copy import deepcopy
from typing import Any

from .errors import CmlPathError, CmlReferenceError
from .nodes import Block, CmlDocument, CmlReference
from .sanitizer import coerce_value, infer_type


def _fail(message: str, strict: bool, reference: CmlReference) -> Any:
    if strict:
        raise CmlReferenceError(message)
    return reference


def _resolve_value(
    value: Any,
    document: CmlDocument,
    env: dict[str, Any],
    strict: bool,
    stack: set[str],
) -> Any:
    if isinstance(value, CmlReference):
        return _resolve_reference(value, document, env, strict, stack)
    if isinstance(value, dict):
        for key in list(value):
            value[key] = _resolve_value(value[key], document, env, strict, stack)
        return value
    if isinstance(value, (list, tuple)):
        return [_resolve_value(item, document, env, strict, stack) for item in value]
    return value


def _resolve_reference(
    reference: CmlReference,
    document: CmlDocument,
    env: dict[str, Any],
    strict: bool,
    stack: set[str],
) -> Any:
    name = reference.name
    args = reference.args
    if name == "env":
        if not args:
            return _fail("$env expects a variable name", strict, reference)
        variable = str(args[0])
        if variable not in env:
            if len(args) >= 2:
                return args[1]
            return _fail(f"environment variable {variable!r} is not set", strict, reference)
        raw = env[variable]
        if len(args) < 2:
            return raw
        fallback = args[1]
        type_name = infer_type(fallback)
        if type_name in (None, "any", "null"):
            return raw
        ok, coerced, message = coerce_value(raw, type_name)
        if not ok:
            return _fail(
                f"cannot convert environment variable {variable!r} to %{type_name}: {message}",
                strict,
                reference,
            )
        return coerced
    if name == "ref":
        if len(args) != 1:
            return _fail("$ref expects exactly one path", strict, reference)
        path = str(args[0])
        if path in stack:
            return _fail(f"reference cycle at {path!r}", strict, reference)
        try:
            target = document.get_path(path)
        except (KeyError, CmlPathError):
            return _fail(f"reference path {path!r} does not exist", strict, reference)
        if isinstance(target, Block):
            target = target.to_dict()
        return _resolve_value(target, document, env, strict, stack | {path})
    return _fail(f"unknown reference ${name}", strict, reference)


def resolve_refs(
    document: CmlDocument,
    *,
    env: dict[str, Any] | None = None,
    strict: bool = True,
    in_place: bool = False,
) -> CmlDocument:
    if not isinstance(document, CmlDocument):
        raise TypeError("resolve_refs expects a CmlDocument")
    result = document if in_place else deepcopy(document)
    environment = dict(os.environ) if env is None else {str(key): value for key, value in env.items()}
    for _, entry in list(result.walk()):
        entry.value = _resolve_value(entry.value, result, environment, strict, set())
    for rule in result.rules.values():
        for field in rule.fields.values():
            if field.has_default:
                field.default = _resolve_value(
                    field.default,
                    result,
                    environment,
                    strict,
                    set(),
                )
    return result

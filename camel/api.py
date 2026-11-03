from __future__ import annotations

import json
from typing import Any

from .nodes import CmlDocument, CmlObject, Entry, Parent, Rule, RuleField, Scope
from .parser import parse as _parse
from .sanitizer import SanitizeReport
from .sanitizer import infer_type
from .sanitizer import sanitize as _sanitize
from .writer import dump as _dump
from .writer import dumps as _dumps


def parse(text: str, filename: str = "<string>") -> CmlDocument:
    return _parse(text, filename=filename)


def parse_value(text: str) -> Any:
    document = _parse(f"@single __cml_value = {text};", filename="<value>")
    return document.singles["__cml_value"].value


def new(init: str | None = None, required: list[str] | None = None) -> CmlDocument:
    return CmlDocument(init=init, required=required)


def _convert_value(value: Any, *, infer_types: bool) -> Any:
    if isinstance(value, dict):
        result = CmlObject()
        for key, item in value.items():
            result[key] = _convert_value(item, infer_types=infer_types)
            if infer_types:
                type_name = infer_type(item)
                if type_name:
                    result.types[str(key)] = type_name
        return result
    if isinstance(value, (list, tuple)):
        return [_convert_value(item, infer_types=infer_types) for item in value]
    return value


def _populate_block(block: Parent | Scope, values: dict[str, Any], *, infer_types: bool) -> None:
    for name, value in values.items():
        converted = _convert_value(value, infer_types=infer_types)
        type_name = infer_type(value) if infer_types else None
        block.entries[str(name)] = Entry(str(name), converted, type=type_name, has_value=True)


def _populate_singles(document: CmlDocument, values: dict[str, Any], *, infer_types: bool) -> None:
    for name, value in values.items():
        converted = _convert_value(value, infer_types=infer_types)
        type_name = infer_type(value) if infer_types else None
        document.singles[str(name)] = Entry(str(name), converted, type=type_name, has_value=True)


def _populate_rules(document: CmlDocument, values: dict[str, Any]) -> None:
    for rule_name, fields in values.items():
        rule = Rule(str(rule_name))
        if isinstance(fields, dict):
            for field_name, info in fields.items():
                if isinstance(info, dict):
                    rule.fields[str(field_name)] = RuleField(
                        str(field_name),
                        type=info.get("type"),
                        optional=bool(info.get("optional", False)),
                        default=info.get("default"),
                        has_default=bool(info.get("has_default", "default" in info)),
                    )
                else:
                    rule.fields[str(field_name)] = RuleField(
                        str(field_name),
                        type=str(info) if info is not None else None,
                    )
        document.rules[str(rule_name)] = rule


def from_dict(
    data: dict[str, Any],
    *,
    init: str | None = None,
    infer_types: bool = True,
) -> CmlDocument:
    if not isinstance(data, dict):
        raise TypeError("from_dict expects a mapping")
    meta_keys = {"init", "required", "single", "parents", "scopes", "aliases", "rules", "decorators"}
    structured = any(key in data for key in meta_keys)
    document = CmlDocument(
        init=init if init is not None else (data.get("init") if structured else None)
    )
    if not structured:
        for key, value in data.items():
            if isinstance(value, dict):
                block = document.add_parent(str(key))
                _populate_block(block, value, infer_types=infer_types)
            else:
                converted = _convert_value(value, infer_types=infer_types)
                type_name = infer_type(value) if infer_types else None
                document.singles[str(key)] = Entry(
                    str(key), converted, type=type_name, has_value=True
                )
        return document
    if "required" in data:
        document.required = list(data["required"])
    if "decorators" in data:
        document.decorators = list(data["decorators"])
    if isinstance(data.get("single"), dict):
        _populate_singles(document, data["single"], infer_types=infer_types)
    if isinstance(data.get("parents"), dict):
        for name, values in data["parents"].items():
            if isinstance(values, dict):
                block = document.add_parent(str(name))
                _populate_block(block, values, infer_types=infer_types)
    if isinstance(data.get("scopes"), dict):
        for name, values in data["scopes"].items():
            if isinstance(values, dict):
                block = document.add_scope(str(name))
                _populate_block(block, values, infer_types=infer_types)
    if isinstance(data.get("aliases"), dict):
        document.aliases = {str(alias): str(target) for alias, target in data["aliases"].items()}
    if isinstance(data.get("rules"), dict):
        _populate_rules(document, data["rules"])
    for key, value in data.items():
        if key in meta_keys:
            continue
        if isinstance(value, dict):
            block = document.add_parent(str(key))
            _populate_block(block, value, infer_types=infer_types)
        else:
            converted = _convert_value(value, infer_types=infer_types)
            type_name = infer_type(value) if infer_types else None
            document.singles[str(key)] = Entry(
                str(key), converted, type=type_name, has_value=True
            )
    return document


def from_json(
    text: str,
    *,
    init: str | None = None,
    infer_types: bool = True,
) -> CmlDocument:
    return from_dict(json.loads(text), init=init, infer_types=infer_types)


def loads(text: str, *, as_dict: bool = False, filename: str = "<string>") -> CmlDocument | dict[str, Any]:
    document = _parse(text, filename=filename)
    if as_dict:
        return document.to_dict()
    return document


def load(path: str, *, as_dict: bool = False, encoding: str = "utf-8") -> CmlDocument | dict[str, Any]:
    with open(path, "r", encoding=encoding) as handle:
        text = handle.read()
    return loads(text, as_dict=as_dict, filename=str(path))


def dumps(document: CmlDocument, *, indent: int | str = 4) -> str:
    return _dumps(document, indent=indent)


def dump(
    document: CmlDocument,
    path: str,
    *,
    indent: int | str = 4,
    encoding: str = "utf-8",
) -> None:
    _dump(document, path, indent=indent, encoding=encoding)


write = dump


def append(
    source: CmlDocument | str,
    target: Any,
    name: str,
    value: Any = None,
    *,
    save: bool = True,
    encoding: str = "utf-8",
    **kwargs: Any,
) -> Entry:
    if isinstance(source, CmlDocument):
        return source.append(target, name, value, **kwargs)
    document = load(source, encoding=encoding)
    assert isinstance(document, CmlDocument)
    entry = document.append(target, name, value, **kwargs)
    if save:
        dump(document, source, encoding=encoding)
    return entry


def change(
    source: CmlDocument | str,
    path: str,
    value: Any,
    *,
    save: bool = True,
    encoding: str = "utf-8",
    force: bool = False,
) -> Any:
    if isinstance(source, CmlDocument):
        source.set(path, value, force=force)
        return value
    document = load(source, encoding=encoding)
    assert isinstance(document, CmlDocument)
    document.set(path, value, force=force)
    if save:
        dump(document, source, encoding=encoding)
    return value


def sanitize(
    source: CmlDocument | str,
    *,
    save: bool = False,
    encoding: str = "utf-8",
    coerce: bool = False,
    strict: bool = True,
    check_required: bool = True,
    check_aliases: bool = True,
    check_rules: bool = True,
) -> SanitizeReport:
    if isinstance(source, CmlDocument):
        return _sanitize(
            source,
            coerce=coerce,
            strict=strict,
            check_required=check_required,
            check_aliases=check_aliases,
            check_rules=check_rules,
        )
    document = load(source, encoding=encoding)
    assert isinstance(document, CmlDocument)
    report = _sanitize(
        document,
        coerce=coerce,
        strict=strict,
        check_required=check_required,
        check_aliases=check_aliases,
        check_rules=check_rules,
    )
    if save:
        dump(document, source, encoding=encoding)
    return report


read = load
save = dump
validate = sanitize
format_cml = dumps


def get(source: CmlDocument | str, path: str, default: Any = None) -> Any:
    if isinstance(source, CmlDocument):
        return source.get_path(path, default)
    document = load(source)
    assert isinstance(document, CmlDocument)
    return document.get_path(path, default)


def remove(
    source: CmlDocument | str,
    path: str,
    *,
    save: bool = True,
    encoding: str = "utf-8",
    force: bool = False,
) -> Any:
    if isinstance(source, CmlDocument):
        return source.remove_path(path, force=force)
    document = load(source, encoding=encoding)
    assert isinstance(document, CmlDocument)
    value = document.remove_path(path, force=force)
    if save:
        dump(document, source, encoding=encoding)
    return value


def merge(
    source: CmlDocument | str,
    other: CmlDocument | str | dict[str, Any],
    *,
    save: bool = True,
    encoding: str = "utf-8",
    **kwargs: Any,
) -> CmlDocument:
    if isinstance(source, CmlDocument):
        target_document = source
    else:
        target_document = load(source, encoding=encoding)
        assert isinstance(target_document, CmlDocument)
    if isinstance(other, CmlDocument):
        other_document = other
    elif isinstance(other, dict):
        other_document = from_dict(other)
    else:
        other_document = load(other, encoding=encoding)
        assert isinstance(other_document, CmlDocument)
    target_document.merge(other_document, **kwargs)
    if save and not isinstance(source, CmlDocument):
        dump(target_document, source, encoding=encoding)
    return target_document


class Cml:
    parse = staticmethod(parse)
    parse_value = staticmethod(parse_value)
    new = staticmethod(new)
    from_dict = staticmethod(from_dict)
    from_json = staticmethod(from_json)
    loads = staticmethod(loads)
    load = staticmethod(load)
    read = staticmethod(load)
    dumps = staticmethod(dumps)
    dump = staticmethod(dump)
    write = staticmethod(dump)
    save = staticmethod(dump)
    format_cml = staticmethod(dumps)
    append = staticmethod(append)
    change = staticmethod(change)
    get = staticmethod(get)
    remove = staticmethod(remove)
    merge = staticmethod(merge)
    sanitize = staticmethod(sanitize)
    validate = staticmethod(sanitize)

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .diff import Change, diff_documents
from .errors import CmlIncludeError
from .nodes import CmlDocument, CmlObject, Entry, Include, Parent, Rule, RuleField, Scope
from .parser import parse as _parse
from .resolver import resolve_refs as _resolve_refs
from .sanitizer import SanitizeReport, infer_type
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
    meta_keys = {
        "init",
        "required",
        "single",
        "parents",
        "scopes",
        "aliases",
        "rules",
        "decorators",
        "includes",
        "uses",
    }
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
    if isinstance(data.get("includes"), list):
        document.includes = [Include(str(path), 0) for path in data["includes"]]
    if isinstance(data.get("uses"), dict):
        for name, rules in data["uses"].items():
            block = document.parents.get(str(name)) or document.scopes.get(str(name))
            if block is not None and isinstance(rules, list):
                block.uses = [str(rule) for rule in rules]
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


def _resolve_include_path(path: str, base_dir: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def _merge_includes(
    document: CmlDocument,
    base_dir: Path | None,
    *,
    encoding: str,
    stack: set[str],
) -> CmlDocument:
    if not document.includes:
        return document
    if base_dir is None:
        raise CmlIncludeError("base_dir is required to resolve includes")
    merged = CmlDocument(filename=document.filename)
    for include in document.includes:
        include_path = _resolve_include_path(include.path, base_dir)
        key = str(include_path)
        if key in stack:
            raise CmlIncludeError(f"include cycle at {key}")
        try:
            included = _load_file(
                include_path,
                encoding=encoding,
                resolve_includes=True,
                resolve_refs=False,
                env=None,
                strict_refs=True,
                stack=stack | {key},
            )
        except FileNotFoundError as exc:
            raise CmlIncludeError(f"include not found: {include_path}") from exc
        merged.merge(included, overwrite=True)
    root_init = document.init
    root_decorators = document.decorators
    document.includes = []
    merged.merge(document, overwrite=True)
    if root_init is not None:
        merged.init = root_init
    if root_decorators:
        merged.decorators = list(root_decorators)
    return merged


def _load_file(
    path: Path,
    *,
    encoding: str,
    resolve_includes: bool,
    resolve_refs: bool,
    env: dict[str, Any] | None,
    strict_refs: bool,
    stack: set[str],
) -> CmlDocument:
    text = path.read_text(encoding=encoding)
    document = _parse(text, filename=str(path))
    if resolve_includes:
        document = _merge_includes(
            document,
            path.parent,
            encoding=encoding,
            stack=stack,
        )
    if resolve_refs:
        document = _resolve_refs(
            document,
            env=env,
            strict=strict_refs,
            in_place=True,
        )
    return document


def _load_text(
    text: str,
    *,
    filename: str,
    base_dir: Path | None,
    encoding: str,
    resolve_includes: bool,
    resolve_refs: bool,
    env: dict[str, Any] | None,
    strict_refs: bool,
) -> CmlDocument:
    document = _parse(text, filename=filename)
    if resolve_includes:
        document = _merge_includes(
            document,
            base_dir,
            encoding=encoding,
            stack=set(),
        )
    if resolve_refs:
        document = _resolve_refs(
            document,
            env=env,
            strict=strict_refs,
            in_place=True,
        )
    return document


def loads(
    text: str,
    *,
    as_dict: bool = False,
    filename: str = "<string>",
    base_dir: str | Path | None = None,
    resolve_includes: bool = False,
    resolve_refs: bool = False,
    env: dict[str, Any] | None = None,
    strict_refs: bool = True,
) -> CmlDocument | dict[str, Any]:
    document = _load_text(
        text,
        filename=filename,
        base_dir=Path(base_dir) if base_dir is not None else None,
        encoding="utf-8",
        resolve_includes=resolve_includes,
        resolve_refs=resolve_refs,
        env=env,
        strict_refs=strict_refs,
    )
    if as_dict:
        return document.to_dict()
    return document


def load(
    path: str | Path,
    *,
    as_dict: bool = False,
    encoding: str = "utf-8",
    resolve_includes: bool = True,
    resolve_refs: bool = False,
    env: dict[str, Any] | None = None,
    strict_refs: bool = True,
) -> CmlDocument | dict[str, Any]:
    path_obj = Path(path)
    document = _load_file(
        path_obj,
        encoding=encoding,
        resolve_includes=resolve_includes,
        resolve_refs=resolve_refs,
        env=env,
        strict_refs=strict_refs,
        stack={str(path_obj.resolve())},
    )
    if as_dict:
        return document.to_dict()
    return document


def dumps(document: CmlDocument, *, indent: int | str = 4) -> str:
    return _dumps(document, indent=indent)


def dump(
    document: CmlDocument,
    path: str | Path,
    *,
    indent: int | str = 4,
    encoding: str = "utf-8",
    atomic: bool = True,
    backup: bool = False,
) -> None:
    _dump(
        document,
        str(path),
        indent=indent,
        encoding=encoding,
        atomic=atomic,
        backup=backup,
    )


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
    fill_defaults: bool = False,
) -> SanitizeReport:
    if isinstance(source, CmlDocument):
        return _sanitize(
            source,
            coerce=coerce,
            strict=strict,
            check_required=check_required,
            check_aliases=check_aliases,
            check_rules=check_rules,
            fill_defaults=fill_defaults,
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
        fill_defaults=fill_defaults,
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


def resolve_refs(
    source: CmlDocument | str,
    *,
    env: dict[str, Any] | None = None,
    strict: bool = True,
    in_place: bool = False,
) -> CmlDocument:
    if isinstance(source, CmlDocument):
        return _resolve_refs(
            source,
            env=env,
            strict=strict,
            in_place=in_place,
        )
    document = load(source)
    assert isinstance(document, CmlDocument)
    return _resolve_refs(document, env=env, strict=strict, in_place=True)


def diff(
    left: CmlDocument | str,
    right: CmlDocument | str,
    *,
    include_meta: bool = False,
) -> list[Change]:
    left_document = left if isinstance(left, CmlDocument) else load(left)
    right_document = right if isinstance(right, CmlDocument) else load(right)
    assert isinstance(left_document, CmlDocument)
    assert isinstance(right_document, CmlDocument)
    return diff_documents(
        left_document,
        right_document,
        include_meta=include_meta,
    )


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
    resolve_refs = staticmethod(resolve_refs)
    diff = staticmethod(diff)

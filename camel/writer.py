from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .nodes import Block, CmlDocument, CmlReference, Entry, Rule

BARE_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


def _unit(indent: int | str) -> str:
    return " " * indent if isinstance(indent, int) else indent


def _format_key(key: Any) -> str:
    text = str(key)
    if BARE_KEY.match(text):
        return text
    return json.dumps(text, ensure_ascii=False)


def _format_reference(value: CmlReference, unit: str) -> str:
    if not value.args:
        return f"${value.name}"
    args = ", ".join(_format_value(arg, 0, unit) for arg in value.args)
    return f"${value.name}({args})"


def _format_value(value: Any, level: int, unit: str) -> str:
    if isinstance(value, CmlReference):
        return _format_reference(value, unit)
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        if not value:
            return "()"
        if any(isinstance(item, (dict, list, tuple)) for item in value):
            inner = unit * (level + 1)
            closing = unit * level
            lines = ["("]
            for item in value:
                lines.append(f"{inner}{_format_value(item, level + 1, unit)},")
            lines.append(f"{closing})")
            return "\n".join(lines)
        return "(" + ", ".join(_format_value(item, level, unit) for item in value) + ")"
    if isinstance(value, dict):
        if not value:
            return "{}"
        inner = unit * (level + 1)
        closing = unit * level
        types = getattr(value, "types", {})
        lines = ["{"]
        for key, item in value.items():
            type_name = types.get(key)
            type_part = f": %{type_name}" if type_name else ""
            lines.append(
                f"{inner}{_format_key(key)}{type_part} = {_format_value(item, level + 1, unit)};"
            )
        lines.append(f"{closing}}}")
        return "\n".join(lines)
    return json.dumps(str(value), ensure_ascii=False)


def _format_entry(entry: Entry, level: int, unit: str) -> str:
    prefix = unit * level
    modifiers = []
    if entry.const:
        modifiers.append("@const")
    if entry.child:
        modifiers.append("@child")
    if entry.optional:
        modifiers.append("@optional")
    modifier_text = (" ".join(modifiers) + " ") if modifiers else ""
    if not entry.has_value:
        return f"{prefix}{modifier_text}{entry.name};"
    type_part = f": %{entry.type}" if entry.type else ""
    return (
        f"{prefix}{modifier_text}{entry.name}{type_part} = "
        f"{_format_value(entry.value, level, unit)};"
    )


def _format_block(block: Block, keyword: str, unit: str) -> str:
    lines: list[str] = []
    for decorator in block.decorators:
        lines.append(f"@{decorator}")
    lines.append(f"@{keyword} {block.name} {{")
    for rule_name in block.uses:
        lines.append(f"{unit}@use {rule_name};")
    for entry in block.entries.values():
        lines.append(_format_entry(entry, 1, unit))
    lines.append("};")
    return "\n".join(lines)


def _format_rule(rule: Rule, unit: str) -> str:
    lines: list[str] = []
    for decorator in rule.decorators:
        lines.append(f"@{decorator}")
    lines.append(f"@rule {rule.name} {{")
    for field in rule.fields.values():
        modifier = "@optional " if field.optional else ""
        type_part = f": %{field.type}" if field.type else ""
        default_part = f" = {_format_value(field.default, 1, unit)}" if field.has_default else ""
        lines.append(f"{unit}{modifier}${field.name}{type_part}{default_part};")
    lines.append("};")
    return "\n".join(lines)


def dumps(document: CmlDocument, *, indent: int | str = 4) -> str:
    unit = _unit(indent)
    chunks: list[str] = []
    if document.decorators:
        chunks.append("\n".join(f"@{decorator}" for decorator in document.decorators))
    if document.includes:
        chunks.append(
            "\n".join(
                f"@include {json.dumps(include.path, ensure_ascii=False)};"
                for include in document.includes
            )
        )
    if document.init is not None:
        chunks.append(f"@init <{document.init}>")
    if document.required:
        chunks.append("@required " + " | ".join(document.required) + ";")
    for entry in document.singles.values():
        chunks.append("@single " + _format_entry(entry, 0, unit))
    for parent in document.parents.values():
        chunks.append(_format_block(parent, "parent", unit))
    for scope in document.scopes.values():
        chunks.append(_format_block(scope, "scope", unit))
    for alias, target in document.aliases.items():
        chunks.append(f"@alias {target} {alias};")
    for rule in document.rules.values():
        chunks.append(_format_rule(rule, unit))
    return "\n\n".join(chunks) + ("\n" if chunks else "")


def dump(
    document: CmlDocument,
    path: str,
    *,
    indent: int | str = 4,
    encoding: str = "utf-8",
    atomic: bool = True,
    backup: bool = False,
) -> None:
    text = dumps(document, indent=indent)
    target = Path(path)
    if not atomic:
        with open(target, "w", encoding=encoding, newline="\n") as handle:
            handle.write(text)
        return
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if backup and target.exists():
            shutil.copy2(target, target.with_name(f"{target.name}.bak"))
        os.replace(temp_name, target)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


write = dump

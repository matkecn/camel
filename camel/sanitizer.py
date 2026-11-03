from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import CmlValidationError
from .nodes import Block, CmlDocument, CmlObject, CmlReference, Entry

TYPE_ALIASES = {
    "bool": "bool",
    "boolean": "bool",
    "int": "int",
    "integer": "int",
    "float": "float",
    "double": "float",
    "decimal": "float",
    "number": "number",
    "num": "number",
    "str": "string",
    "string": "string",
    "text": "string",
    "list": "list",
    "array": "list",
    "tuple": "list",
    "obj": "object",
    "object": "object",
    "dict": "object",
    "map": "object",
    "null": "null",
    "none": "null",
    "nil": "null",
    "any": "any",
    "auto": "any",
}


def normalize_type(type_name: str | None) -> str:
    if not type_name:
        return "any"
    name = str(type_name).lstrip("%").strip().lower()
    return TYPE_ALIASES.get(name, name)


def infer_type(value: Any) -> str | None:
    if isinstance(value, CmlReference):
        return None
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        return "list"
    if isinstance(value, dict):
        return "object"
    return "any"


def check_type(value: Any, type_name: str | None) -> bool:
    if isinstance(value, CmlReference):
        return True
    kind = normalize_type(type_name)
    if kind in ("any", "auto"):
        return True
    if kind == "null":
        return value is None
    if value is None:
        return False
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "float":
        return isinstance(value, float) or (isinstance(value, int) and not isinstance(value, bool))
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "string":
        return isinstance(value, str)
    if kind == "list":
        return isinstance(value, (list, tuple))
    if kind == "object":
        return isinstance(value, dict)
    return True


def coerce_value(value: Any, type_name: str | None) -> tuple[bool, Any, str | None]:
    if isinstance(value, CmlReference):
        return True, value, None
    kind = normalize_type(type_name)
    if kind in ("any", "auto"):
        return True, value, None
    if kind == "null":
        if value is None or (isinstance(value, str) and value.lower() in ("null", "none", "nil")):
            return True, None, None
        return False, value, "expected null"
    if kind == "int":
        if isinstance(value, bool):
            return False, value, "booleans are not integers"
        if isinstance(value, int):
            return True, value, None
        if isinstance(value, float) and value.is_integer():
            return True, int(value), None
        if isinstance(value, str):
            try:
                return True, int(value.strip(), 10), None
            except ValueError:
                return False, value, "not an integer"
        return False, value, "not an integer"
    if kind == "float":
        if isinstance(value, bool):
            return False, value, "booleans are not floats"
        if isinstance(value, (int, float)):
            return True, float(value), None
        if isinstance(value, str):
            try:
                return True, float(value.strip()), None
            except ValueError:
                return False, value, "not a float"
        return False, value, "not a float"
    if kind == "bool":
        if isinstance(value, bool):
            return True, value, None
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("true", "yes", "on", "1"):
                return True, True, None
            if lowered in ("false", "no", "off", "0"):
                return True, False, None
            return False, value, "not a boolean"
        if isinstance(value, int) and value in (0, 1):
            return True, bool(value), None
        return False, value, "not a boolean"
    if kind == "string":
        if isinstance(value, str):
            return True, value, None
        if isinstance(value, bool):
            return True, "true" if value else "false", None
        if isinstance(value, (int, float)):
            return True, str(value), None
        return False, value, "not a string"
    if kind == "list":
        if isinstance(value, (list, tuple)):
            return True, list(value), None
        return False, value, "not a list"
    if kind == "object":
        if isinstance(value, dict):
            return True, value, None
        return False, value, "not an object"
    return True, value, None


@dataclass
class Issue:
    level: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.level}: {self.path}: {self.message}"


@dataclass
class SanitizeReport:
    issues: list[Issue] = field(default_factory=list)
    changed: bool = False

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, path: str, message: str) -> None:
        self.issues.append(Issue("error", path, message))

    def add_warning(self, path: str, message: str) -> None:
        self.issues.append(Issue("warning", path, message))

    def __str__(self) -> str:
        if not self.issues:
            return "CamelConfig is valid"
        return "\n".join(str(issue) for issue in self.issues)


def _validate_object(
    value: dict[str, Any],
    path: str,
    report: SanitizeReport,
    *,
    coerce: bool,
) -> None:
    types = getattr(value, "types", {})
    for key, type_name in types.items():
        if key not in value:
            continue
        item = value[key]
        item_path = f"{path}.{key}"
        if isinstance(item, CmlReference):
            continue
        if not check_type(item, type_name):
            if coerce:
                ok, new_value, message = coerce_value(item, type_name)
                if ok:
                    value[key] = new_value
                    report.changed = True
                    item = new_value
                else:
                    report.add_error(
                        item_path,
                        f"expected %{type_name}, got {type(item).__name__}: {message}",
                    )
                    continue
            else:
                report.add_error(
                    item_path,
                    f"expected %{type_name}, got {type(item).__name__}",
                )
                continue
        if isinstance(item, dict):
            _validate_object(item, item_path, report, coerce=coerce)


def _validate_entry(
    entry: Entry,
    path: str,
    report: SanitizeReport,
    *,
    coerce: bool,
) -> None:
    if not entry.has_value:
        if not entry.optional:
            report.add_error(path, "entry has no value")
        return
    if entry.value is None:
        if entry.type and normalize_type(entry.type) not in ("null", "any", "auto") and not entry.optional:
            report.add_error(path, f"expected %{entry.type}, got null")
        return
    if entry.type and not check_type(entry.value, entry.type):
        if coerce:
            ok, new_value, message = coerce_value(entry.value, entry.type)
            if ok:
                entry.value = new_value
                report.changed = True
            else:
                report.add_error(
                    path,
                    f"expected %{entry.type}, got {type(entry.value).__name__}: {message}",
                )
                return
        else:
            report.add_error(
                path,
                f"expected %{entry.type}, got {type(entry.value).__name__}",
            )
            return
    if isinstance(entry.value, dict):
        _validate_object(entry.value, path, report, coerce=coerce)


def _iter_entries(document: CmlDocument):
    for name, entry in document.singles.items():
        yield f"single.{name}", entry
    for name, block in document.parents.items():
        for field_name, entry in block.entries.items():
            yield f"parent.{name}.{field_name}", entry
    for name, block in document.scopes.items():
        for field_name, entry in block.entries.items():
            yield f"scope.{name}.{field_name}", entry


def sanitize(
    document: CmlDocument,
    *,
    coerce: bool = False,
    strict: bool = True,
    check_required: bool = True,
    check_aliases: bool = True,
    check_rules: bool = True,
) -> SanitizeReport:
    report = SanitizeReport()
    seen: set[str] = set()
    required: list[str] = []
    for name in document.required:
        if name in seen:
            report.add_warning(f"required.{name}", "duplicate required key")
            report.changed = True
            continue
        seen.add(name)
        required.append(name)
    if required != document.required:
        document.required = required
        report.changed = True
    for path, entry in _iter_entries(document):
        _validate_entry(entry, path, report, coerce=coerce)
    if check_required:
        for name in document.required:
            target = document.resolve_alias(name) if name in document.aliases else name
            if not document.has_key_anywhere(target):
                report.add_error(f"required.{name}", "required key is missing")
    if check_aliases:
        for alias in document.aliases:
            try:
                target = document.resolve_alias(alias)
            except Exception as exc:
                report.add_error(f"alias.{alias}", str(exc))
                continue
            if (
                target not in document.parents
                and target not in document.scopes
                and target not in document.singles
            ):
                report.add_error(f"alias.{alias}", f"alias target {target!r} does not exist")
    if check_rules:
        for rule_name, rule in document.rules.items():
            block: Block | None = document.parents.get(rule_name) or document.scopes.get(rule_name)
            if block is None:
                continue
            for field_name, rule_field in rule.fields.items():
                path = f"rule.{rule_name}.{field_name}"
                entry = block.entries.get(field_name)
                if entry is None:
                    if not rule_field.optional:
                        report.add_error(path, "rule field is missing")
                    continue
                if entry.value is None or isinstance(entry.value, CmlReference):
                    continue
                if rule_field.type and not check_type(entry.value, rule_field.type):
                    report.add_error(
                        path,
                        f"expected %{rule_field.type}, got {type(entry.value).__name__}",
                    )
    if strict and report.errors:
        raise CmlValidationError(report)
    return report

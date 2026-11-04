from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .nodes import CmlDocument, CmlReference


def _jsonable(value: Any) -> Any:
    if isinstance(value, CmlReference):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _flatten_mapping(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(item, dict):
            result.update(_flatten_mapping(item, path))
        else:
            result[path] = item
    return result


@dataclass(frozen=True)
class Change:
    kind: str
    path: str
    old: Any = None
    new: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "old": _jsonable(self.old),
            "new": _jsonable(self.new),
        }


def diff_documents(
    left: CmlDocument,
    right: CmlDocument,
    *,
    include_meta: bool = False,
) -> list[Change]:
    if not isinstance(left, CmlDocument) or not isinstance(right, CmlDocument):
        raise TypeError("diff_documents expects CmlDocument values")
    if include_meta:
        left_values = _flatten_mapping(left.to_dict(include_meta=True))
        right_values = _flatten_mapping(right.to_dict(include_meta=True))
    else:
        left_values = left.flatten()
        right_values = right.flatten()
    changes: list[Change] = []
    for path in sorted(set(left_values) | set(right_values)):
        if path not in left_values:
            changes.append(Change("added", path, new=right_values[path]))
            continue
        if path not in right_values:
            changes.append(Change("removed", path, old=left_values[path]))
            continue
        if left_values[path] != right_values[path]:
            changes.append(
                Change(
                    "changed",
                    path,
                    old=left_values[path],
                    new=right_values[path],
                )
            )
    return changes

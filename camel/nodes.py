from __future__ import annotations

import json
from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass, field
from typing import Any

from .errors import CmlPathError, CmlTypeError


def to_python(value: Any) -> Any:
    if isinstance(value, CmlReference):
        return value
    if isinstance(value, dict):
        return {key: to_python(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_python(item) for item in value]
    return value


@dataclass(frozen=True)
class CmlReference:
    name: str
    args: tuple[Any, ...] = ()

    def __str__(self) -> str:
        if not self.args:
            return f"${self.name}"
        args = ", ".join(str(arg) for arg in self.args)
        return f"${self.name}({args})"


class CmlObject(dict):
    def __init__(self, *args: Any, types: dict[str, str] | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.types: dict[str, str] = dict(types or {})

    def copy(self) -> CmlObject:
        return CmlObject(self, types=self.types)


@dataclass
class Entry:
    name: str
    value: Any = None
    type: str | None = None
    const: bool = False
    child: bool = False
    optional: bool = False
    has_value: bool = False
    line: int = 0
    column: int = 0

    def to_python(self) -> Any:
        return to_python(self.value)

    def __repr__(self) -> str:
        modifiers = []
        if self.const:
            modifiers.append("const")
        if self.child:
            modifiers.append("child")
        if self.optional:
            modifiers.append("optional")
        suffix = f" modifiers={modifiers}" if modifiers else ""
        type_name = f": %{self.type}" if self.type else ""
        return f"Entry({self.name!r}{type_name}={self.value!r}{suffix})"


class Block(MutableMapping[str, Any]):
    kind = "block"

    def __init__(
        self,
        name: str,
        entries: dict[str, Entry] | None = None,
        *,
        decorators: list[str] | None = None,
        line: int = 0,
    ) -> None:
        self.name = name
        self.entries: dict[str, Entry] = dict(entries or {})
        self.decorators = list(decorators or [])
        self.line = line

    def __getitem__(self, key: str) -> Any:
        return self.entries[key].value

    def __setitem__(self, key: str, value: Any) -> None:
        entry = self.entries.get(key)
        if entry is None:
            self.entries[key] = Entry(key, value, has_value=True)
            return
        if entry.const:
            raise CmlTypeError(f"{self.name}.{key} is constant")
        entry.value = value
        entry.has_value = True

    def __delitem__(self, key: str) -> None:
        self.remove(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r}, {len(self.entries)} entries)"

    def get_entry(self, key: str, default: Any = None) -> Entry | Any:
        return self.entries.get(key, default)

    def append(
        self,
        name: str,
        value: Any = None,
        *,
        type: str | None = None,
        const: bool = False,
        child: bool = False,
        optional: bool = False,
        has_value: bool = True,
    ) -> Entry:
        entry = Entry(
            name,
            value,
            type=type,
            const=const,
            child=child,
            optional=optional,
            has_value=has_value,
        )
        self.entries[name] = entry
        return entry

    def remove(self, name: str, *, force: bool = False) -> Entry:
        entry = self.entries.get(name)
        if entry is None:
            raise KeyError(name)
        if entry.const and not force:
            raise CmlTypeError(f"{self.name}.{name} is constant")
        return self.entries.pop(name)

    def to_dict(self) -> dict[str, Any]:
        return {key: entry.to_python() for key, entry in self.entries.items()}

    def copy(self) -> Block:
        return type(self)(
            self.name,
            {key: Entry(**vars(entry)) for key, entry in self.entries.items()},
            decorators=list(self.decorators),
            line=self.line,
        )


class Parent(Block):
    kind = "parent"


class Scope(Block):
    kind = "scope"


@dataclass
class RuleField:
    name: str
    type: str | None = None
    optional: bool = False
    default: Any = None
    has_default: bool = False


@dataclass
class Rule:
    name: str
    fields: dict[str, RuleField] = field(default_factory=dict)
    decorators: list[str] = field(default_factory=list)
    line: int = 0

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "type": field.type,
                "optional": field.optional,
                "default": to_python(field.default) if field.has_default else None,
                "has_default": field.has_default,
            }
            for name, field in self.fields.items()
        }

    def __getitem__(self, key: str) -> RuleField:
        return self.fields[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.fields)

    def __len__(self) -> int:
        return len(self.fields)

    def copy(self) -> Rule:
        return Rule(
            self.name,
            {name: RuleField(**vars(field)) for name, field in self.fields.items()},
            decorators=list(self.decorators),
            line=self.line,
        )


_MISSING = object()


class CmlDocument(MutableMapping[str, Any]):
    def __init__(
        self,
        *,
        init: str | None = None,
        required: list[str] | None = None,
        singles: dict[str, Entry] | None = None,
        parents: dict[str, Parent] | None = None,
        scopes: dict[str, Scope] | None = None,
        aliases: dict[str, str] | None = None,
        rules: dict[str, Rule] | None = None,
        decorators: list[str] | None = None,
        filename: str = "<string>",
    ) -> None:
        self.init = init
        self.required = list(required or [])
        self.singles: dict[str, Entry] = dict(singles or {})
        self.parents: dict[str, Parent] = dict(parents or {})
        self.scopes: dict[str, Scope] = dict(scopes or {})
        self.aliases: dict[str, str] = dict(aliases or {})
        self.rules: dict[str, Rule] = dict(rules or {})
        self.decorators = list(decorators or [])
        self.filename = filename

    def __getitem__(self, key: str) -> Any:
        if key in self.parents:
            return self.parents[key]
        if key in self.scopes:
            return self.scopes[key]
        if key in self.singles:
            return self.singles[key].value
        if key in self.aliases:
            return self[self.aliases[key]]
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self.singles:
            entry = self.singles[key]
            if entry.const:
                raise CmlTypeError(f"{key} is constant")
            entry.value = value
            entry.has_value = True
            return
        if key in self.parents or key in self.scopes:
            raise CmlTypeError(f"{key} is a block, use a path such as {key}.field")
        self.singles[key] = Entry(key, value, has_value=True)

    def __delitem__(self, key: str) -> None:
        if key in self.singles:
            entry = self.singles[key]
            if entry.const:
                raise CmlTypeError(f"{key} is constant")
            del self.singles[key]
            return
        if key in self.parents:
            del self.parents[key]
            return
        if key in self.scopes:
            del self.scopes[key]
            return
        if key in self.aliases:
            del self.aliases[key]
            return
        if key in self.rules:
            del self.rules[key]
            return
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        seen: set[str] = set()
        for key in self.singles:
            seen.add(key)
            yield key
        for key in self.parents:
            if key not in seen:
                seen.add(key)
                yield key
        for key in self.scopes:
            if key not in seen:
                seen.add(key)
                yield key

    def __len__(self) -> int:
        return len(set(self.singles) | set(self.parents) | set(self.scopes))

    def __repr__(self) -> str:
        return (
            f"CmlDocument(init={self.init!r}, singles={len(self.singles)}, "
            f"parents={len(self.parents)}, scopes={len(self.scopes)}, "
            f"rules={len(self.rules)})"
        )

    def add_parent(
        self,
        name: str,
        *,
        decorators: list[str] | None = None,
        line: int = 0,
    ) -> Parent:
        parent = Parent(name, decorators=decorators, line=line)
        self.parents[name] = parent
        return parent

    def add_scope(
        self,
        name: str,
        *,
        decorators: list[str] | None = None,
        line: int = 0,
    ) -> Scope:
        scope = Scope(name, decorators=decorators, line=line)
        self.scopes[name] = scope
        return scope

    def add_rule(
        self,
        name: str,
        *,
        decorators: list[str] | None = None,
        line: int = 0,
    ) -> Rule:
        rule = Rule(name, decorators=decorators, line=line)
        self.rules[name] = rule
        return rule

    def add_alias(self, target: str, alias: str) -> None:
        if target not in self.parents and target not in self.scopes and target not in self.singles:
            raise CmlPathError(f"cannot alias missing target {target!r}")
        self.aliases[alias] = target

    def resolve_alias(self, name: str) -> str:
        seen: set[str] = set()
        current = name
        while current in self.aliases:
            if current in seen:
                raise CmlPathError(f"alias cycle at {current!r}")
            seen.add(current)
            current = self.aliases[current]
        return current

    def _resolve_block(self, target: Any, *, create: bool = False) -> Block:
        if isinstance(target, Block):
            return target
        if target in (None, "single", "@single"):
            raise CmlPathError("single values are not blocks")
        if not isinstance(target, str):
            raise CmlPathError(f"invalid block target {target!r}")
        if target.startswith("parent:"):
            name = target.split(":", 1)[1]
            if name in self.parents:
                return self.parents[name]
            if create:
                return self.add_parent(name)
            raise CmlPathError(f"missing parent {name!r}")
        if target.startswith("scope:"):
            name = target.split(":", 1)[1]
            if name in self.scopes:
                return self.scopes[name]
            if create:
                return self.add_scope(name)
            raise CmlPathError(f"missing scope {name!r}")
        if target in self.parents:
            return self.parents[target]
        if target in self.scopes:
            return self.scopes[target]
        if target in self.aliases:
            return self._resolve_block(self.resolve_alias(target), create=create)
        if create:
            return self.add_parent(target)
        raise CmlPathError(f"missing parent or scope {target!r}")

    def append(
        self,
        target: Any,
        name: str,
        value: Any = None,
        *,
        type: str | None = None,
        const: bool = False,
        child: bool = False,
        optional: bool = False,
        has_value: bool = True,
        create: bool = False,
    ) -> Entry:
        if target in (None, "single", "@single"):
            entry = Entry(
                name,
                value,
                type=type,
                const=const,
                child=child,
                optional=optional,
                has_value=has_value,
            )
            self.singles[name] = entry
            return entry
        block = self._resolve_block(target, create=create)
        return block.append(
            name,
            value,
            type=type,
            const=const,
            child=child,
            optional=optional,
            has_value=has_value,
        )

    def get_path(self, path: str, default: Any = _MISSING) -> Any:
        try:
            return self._get_path(path)
        except (KeyError, CmlPathError):
            if default is not _MISSING:
                return default
            raise

    def _get_path(self, path: str) -> Any:
        if path in self.singles:
            return self.singles[path].value
        if path in self.parents:
            return self.parents[path]
        if path in self.scopes:
            return self.scopes[path]
        if path in self.aliases:
            return self[self.aliases[path]]
        if path.startswith("single."):
            return self.singles[path[7:]].value
        if path.startswith("parent."):
            block_name, _, field_name = path[7:].partition(".")
            return self._resolve_block(block_name)[field_name]
        if path.startswith("scope."):
            block_name, _, field_name = path[6:].partition(".")
            return self._resolve_block(block_name)[field_name]
        if path.startswith("rule."):
            rule_name, _, field_name = path[5:].partition(".")
            return self.rules[rule_name].fields[field_name]
        block_name, dot, field_name = path.partition(".")
        if dot:
            block = self._resolve_block(block_name)
            return block[field_name]
        raise KeyError(path)

    def set(self, path: str, value: Any, *, force: bool = False) -> None:
        if path.startswith("single."):
            self._set_single(path[7:], value, force=force)
            return
        if path.startswith("parent."):
            block_name, _, field_name = path[7:].partition(".")
            self._set_block_field(block_name, field_name, value, force=force)
            return
        if path.startswith("scope."):
            block_name, _, field_name = path[6:].partition(".")
            self._set_block_field(block_name, field_name, value, force=force)
            return
        if path.startswith("rule."):
            raise CmlPathError("rules define schemas and cannot be assigned values")
        if path in self.singles:
            self._set_single(path, value, force=force)
            return
        if path in self.parents or path in self.scopes:
            raise CmlPathError(f"{path} is a block, use a path such as {path}.field")
        block_name, dot, field_name = path.partition(".")
        if dot and (block_name in self.parents or block_name in self.scopes or block_name in self.aliases):
            self._set_block_field(block_name, field_name, value, force=force)
            return
        self._set_single(path, value, force=force)

    def change(self, path: str, value: Any, *, force: bool = False) -> None:
        self.set(path, value, force=force)

    def _set_single(self, name: str, value: Any, *, force: bool = False) -> None:
        entry = self.singles.get(name)
        if entry is None:
            self.singles[name] = Entry(name, value, has_value=True)
            return
        if entry.const and not force:
            raise CmlTypeError(f"{name} is constant")
        entry.value = value
        entry.has_value = True

    def _set_block_field(self, block_name: str, field_name: str, value: Any, *, force: bool = False) -> None:
        block = self._resolve_block(block_name)
        entry = block.entries.get(field_name)
        if entry is None:
            block.append(field_name, value)
            return
        if entry.const and not force:
            raise CmlTypeError(f"{block.name}.{field_name} is constant")
        entry.value = value
        entry.has_value = True

    def remove_path(self, path: str, *, force: bool = False) -> Any:
        if path.startswith("single."):
            name = path[7:]
            entry = self.singles.get(name)
            if entry is None:
                raise KeyError(path)
            if entry.const and not force:
                raise CmlTypeError(f"{name} is constant")
            return self.singles.pop(name).value
        if path.startswith("parent."):
            block_name, _, field_name = path[7:].partition(".")
            return self._resolve_block(block_name).remove(field_name, force=force).value
        if path.startswith("scope."):
            block_name, _, field_name = path[6:].partition(".")
            return self._resolve_block(block_name).remove(field_name, force=force).value
        if path in self.singles:
            entry = self.singles[path]
            if entry.const and not force:
                raise CmlTypeError(f"{path} is constant")
            return self.singles.pop(path).value
        block_name, dot, field_name = path.partition(".")
        if dot:
            return self._resolve_block(block_name).remove(field_name, force=force).value
        raise KeyError(path)

    def has_key_anywhere(self, name: str) -> bool:
        if name in self.singles:
            return True
        for block in (*self.parents.values(), *self.scopes.values()):
            if name in block.entries:
                return True
        return False

    def has_path(self, path: str) -> bool:
        try:
            self._get_path(path)
            return True
        except (KeyError, CmlPathError):
            return False

    def setdefault_path(self, path: str, value: Any) -> Any:
        if self.has_path(path):
            return self.get_path(path)
        self.set(path, value)
        return value

    def walk(self) -> Iterator[tuple[str, Entry]]:
        for name, entry in self.singles.items():
            yield f"single.{name}", entry
        for name, block in self.parents.items():
            for field_name, entry in block.entries.items():
                yield f"parent.{name}.{field_name}", entry
        for name, block in self.scopes.items():
            for field_name, entry in block.entries.items():
                yield f"scope.{name}.{field_name}", entry

    def flatten(self) -> dict[str, Any]:
        return {path: entry.to_python() for path, entry in self.walk()}

    def update_paths(self, values: dict[str, Any], *, force: bool = False) -> CmlDocument:
        for path, value in values.items():
            self.set(path, value, force=force)
        return self

    def _merge_block(self, target: Block, source: Block, overwrite: bool) -> None:
        for name, entry in source.entries.items():
            if name not in target.entries or overwrite:
                target.entries[name] = Entry(**vars(entry))
        if not target.decorators:
            target.decorators = list(source.decorators)

    def merge(
        self,
        other: CmlDocument,
        *,
        overwrite: bool = True,
        add_missing_blocks: bool = True,
        merge_required: bool = True,
        merge_rules: bool = True,
    ) -> CmlDocument:
        if not isinstance(other, CmlDocument):
            raise TypeError("merge expects a CmlDocument")
        if self.init is None:
            self.init = other.init
        for name, entry in other.singles.items():
            if name not in self.singles or overwrite:
                self.singles[name] = Entry(**vars(entry))
        for target_map, source_map in (
            (self.parents, other.parents),
            (self.scopes, other.scopes),
        ):
            for name, source_block in source_map.items():
                if name not in target_map:
                    if add_missing_blocks:
                        target_map[name] = source_block.copy()
                    continue
                self._merge_block(target_map[name], source_block, overwrite)
        for alias, target in other.aliases.items():
            if alias not in self.aliases or overwrite:
                self.aliases[alias] = target
        if merge_required:
            for name in other.required:
                if name not in self.required:
                    self.required.append(name)
        if merge_rules:
            for name, rule in other.rules.items():
                if name not in self.rules or overwrite:
                    self.rules[name] = rule.copy()
        return self

    def to_json(
        self,
        *,
        include_meta: bool = False,
        indent: int | None = None,
        ensure_ascii: bool = False,
        **kwargs: Any,
    ) -> str:
        return json.dumps(
            self.to_dict(include_meta=include_meta),
            indent=indent,
            ensure_ascii=ensure_ascii,
            **kwargs,
        )

    def save(self, path: str, **kwargs: Any) -> None:
        from .writer import dump

        dump(self, path, **kwargs)

    def validate(self, **kwargs: Any) -> Any:
        from .sanitizer import sanitize

        return sanitize(self, **kwargs)

    def to_dict(self, *, include_meta: bool = False) -> dict[str, Any]:
        values: dict[str, Any] = {"single": {key: entry.to_python() for key, entry in self.singles.items()}}
        values.update({name: block.to_dict() for name, block in self.parents.items()})
        values.update({name: block.to_dict() for name, block in self.scopes.items()})
        if not include_meta:
            return values
        return {
            "init": self.init,
            "required": list(self.required),
            "single": values["single"],
            "parents": {name: block.to_dict() for name, block in self.parents.items()},
            "scopes": {name: block.to_dict() for name, block in self.scopes.items()},
            "aliases": dict(self.aliases),
            "rules": {name: rule.to_dict() for name, rule in self.rules.items()},
            "decorators": list(self.decorators),
        }

    @property
    def data(self) -> dict[str, Any]:
        return self.to_dict()

    def copy(self) -> CmlDocument:
        return CmlDocument(
            init=self.init,
            required=list(self.required),
            singles={key: Entry(**vars(entry)) for key, entry in self.singles.items()},
            parents={name: block.copy() for name, block in self.parents.items()},
            scopes={name: block.copy() for name, block in self.scopes.items()},
            aliases=dict(self.aliases),
            rules={
                name: Rule(
                    rule.name,
                    {
                        field_name: RuleField(**vars(field))
                        for field_name, field in rule.fields.items()
                    },
                    decorators=list(rule.decorators),
                    line=rule.line,
                )
                for name, rule in self.rules.items()
            },
            decorators=list(self.decorators),
            filename=self.filename,
        )

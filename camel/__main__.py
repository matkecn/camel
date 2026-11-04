from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .api import diff, dump, dumps, load, parse_value, sanitize
from .errors import CmlPathError
from .nodes import CmlDocument
from .sanitizer import coerce_value


def _display(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _print_value(value: object, as_json: bool) -> None:
    if as_json or not isinstance(value, str):
        print(_display(value))
    else:
        print(value)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    commands = {
        "read",
        "validate",
        "format",
        "get",
        "set",
        "remove",
        "merge",
        "diff",
    }
    if args and args[0] not in commands and not args[0].startswith("-"):
        args.insert(0, "read")
    parser = argparse.ArgumentParser(prog="camel", description="CamelConfig (Cml) toolkit")
    subparsers = parser.add_subparsers(dest="command")

    read_parser = subparsers.add_parser("read", help="print a CML file as JSON")
    read_parser.add_argument("file")
    read_parser.add_argument("--meta", action="store_true", help="include init, required, aliases and rules")

    validate_parser = subparsers.add_parser("validate", help="validate and sanitize a CML file")
    validate_parser.add_argument("file")
    validate_parser.add_argument("--coerce", action="store_true", help="coerce values into declared types")
    validate_parser.add_argument("--fix", action="store_true", help="write coerced values back")
    validate_parser.add_argument(
        "--fill-defaults",
        action="store_true",
        help="fill missing rule fields from defaults",
    )

    format_parser = subparsers.add_parser("format", help="print canonical CML")
    format_parser.add_argument("file")
    format_parser.add_argument("--indent", type=int, default=4)

    get_parser = subparsers.add_parser("get", help="read a value by path")
    get_parser.add_argument("file")
    get_parser.add_argument("path")
    get_parser.add_argument("--json", action="store_true", help="print JSON")
    get_parser.add_argument("--default", help="value to print when the path is missing")

    set_parser = subparsers.add_parser("set", help="set a value by path")
    set_parser.add_argument("file")
    set_parser.add_argument("path")
    set_parser.add_argument("value")
    set_parser.add_argument("--type", dest="type_name", help="coerce the value to this type")
    set_parser.add_argument("--force", action="store_true", help="overwrite const values")
    set_parser.add_argument("--dry-run", action="store_true", help="print the result without saving")

    remove_parser = subparsers.add_parser("remove", help="remove a value by path")
    remove_parser.add_argument("file")
    remove_parser.add_argument("path")
    remove_parser.add_argument("--force", action="store_true", help="remove const values")
    remove_parser.add_argument("--dry-run", action="store_true", help="print the result without saving")

    merge_parser = subparsers.add_parser("merge", help="merge another CML file")
    merge_parser.add_argument("file")
    merge_parser.add_argument("other")
    merge_parser.add_argument("--output", help="write the merged result to this path")
    merge_parser.add_argument("--no-overwrite", action="store_true", help="keep existing values")

    diff_parser = subparsers.add_parser("diff", help="show differences between two CML files")
    diff_parser.add_argument("left")
    diff_parser.add_argument("right")
    diff_parser.add_argument("--json", action="store_true", help="print JSON")

    parsed = parser.parse_args(args)
    if parsed.command is None:
        parser.print_help()
        return 0

    if parsed.command == "read":
        document = load(parsed.file)
        assert isinstance(document, CmlDocument)
        print(json.dumps(document.to_dict(include_meta=parsed.meta), indent=2, ensure_ascii=False))
        return 0

    if parsed.command == "validate":
        report = sanitize(
            parsed.file,
            coerce=parsed.coerce,
            fill_defaults=parsed.fill_defaults,
            save=parsed.fix,
            strict=False,
        )
        print(report)
        return 0 if report.ok else 1

    if parsed.command == "format":
        document = load(parsed.file, resolve_includes=False)
        assert isinstance(document, CmlDocument)
        sys.stdout.write(dumps(document, indent=parsed.indent))
        return 0

    if parsed.command == "get":
        document = load(parsed.file)
        assert isinstance(document, CmlDocument)
        try:
            value = document.get_path(parsed.path)
        except (KeyError, CmlPathError):
            if parsed.default is None:
                print(f"missing path: {parsed.path}", file=sys.stderr)
                return 1
            value = parse_value(parsed.default)
        _print_value(value, parsed.json)
        return 0

    if parsed.command == "set":
        document = load(parsed.file)
        assert isinstance(document, CmlDocument)
        value = parse_value(parsed.value)
        if parsed.type_name:
            ok, value, message = coerce_value(value, parsed.type_name)
            if not ok:
                print(f"invalid value for %{parsed.type_name}: {message}", file=sys.stderr)
                return 1
        document.set(parsed.path, value, force=parsed.force)
        if parsed.dry_run:
            sys.stdout.write(dumps(document))
        else:
            document.save(parsed.file)
        return 0

    if parsed.command == "remove":
        document = load(parsed.file)
        assert isinstance(document, CmlDocument)
        try:
            document.remove_path(parsed.path, force=parsed.force)
        except KeyError:
            print(f"missing path: {parsed.path}", file=sys.stderr)
            return 1
        if parsed.dry_run:
            sys.stdout.write(dumps(document))
        else:
            document.save(parsed.file)
        return 0

    if parsed.command == "merge":
        target = load(parsed.file)
        other = load(parsed.other)
        assert isinstance(target, CmlDocument)
        assert isinstance(other, CmlDocument)
        target.merge(other, overwrite=not parsed.no_overwrite)
        dump(target, parsed.output or parsed.file)
        return 0

    if parsed.command == "diff":
        changes = diff(parsed.left, parsed.right)
        if parsed.json:
            print(
                json.dumps(
                    [change.to_dict() for change in changes],
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0
        for change in changes:
            data = change.to_dict()
            if change.kind == "added":
                print(f"+ {change.path} = {_display(data['new'])}")
            elif change.kind == "removed":
                print(f"- {change.path} = {_display(data['old'])}")
            else:
                print(f"~ {change.path}: {_display(data['old'])} -> {_display(data['new'])}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

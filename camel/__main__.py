from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .api import dumps, load, sanitize
from .nodes import CmlDocument


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    commands = {"read", "validate", "format"}
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
    format_parser = subparsers.add_parser("format", help="print canonical CML")
    format_parser.add_argument("file")
    format_parser.add_argument("--indent", type=int, default=4)
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
            save=parsed.fix,
            strict=False,
        )
        print(report)
        return 0 if report.ok else 1
    if parsed.command == "format":
        document = load(parsed.file)
        assert isinstance(document, CmlDocument)
        sys.stdout.write(dumps(document, indent=parsed.indent))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

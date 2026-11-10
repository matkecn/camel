<p align="center">
  <img src="assets/logo.svg" alt="CamelConfig logo" width="560" />
</p>

<!--<h1 align="center">CamelConfig</h1>-->

<p align="center">
  <strong>CML</strong> — a typed, human-friendly configuration language for Python.
</p>

<p align="center">
  <a href="https://github.com/matkecn/camel"><img src="https://img.shields.io/badge/version-1.1.0-F59E0B?style=flat-square&logo=semanticrelease&logoColor=white" alt="Version 1.1.0"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="tests/test_camel.py"><img src="https://img.shields.io/badge/tests-43%20passing-16A34A?style=flat-square&logo=checkmarx&logoColor=white" alt="43 tests passing"></a>
  <a href="https://github.com/matkecn/camel/actions/workflows/ci.yml"><img src="https://github.com/matkecn/camel/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-22C55E?style=flat-square&logo=opensourceinitiative&logoColor=white" alt="MIT license"></a>
  <a href="vscode-cml/"><img src="https://img.shields.io/badge/VS%20Code-CML-007ACC?style=flat-square&logo=visualstudiocode&logoColor=white" alt="VS Code extension"></a>
</p>

CamelConfig is a compact configuration language with a Pythonic feel. It gives you
structured parents and scopes, typed values, required keys, aliases, rules, comments,
includes, references, and a clean canonical format. The Python package turns `.cml`
files into native Python objects and gives you safe tools for reading, writing, editing,
validating, diffing, and merging configuration.

## Highlights

- **Read and write** `.cml` files with a full parser and canonical writer.
- **Includes** — compose files with `@include "defaults.cml";` and cycle detection.
- **References** — resolve `$env("PORT", 8080)` and `$ref("server.host")` values.
- **Native Python values** — strings, ints, floats, booleans, `None`, lists, dicts, and references.
- **Typed entries** with `%string`, `%int`, `%float`, `%bool`, `%list`, `%object`, `%null`, and `%any`.
- **Safe mutation** — append, change, remove, and merge values by path.
- **Validation and sanitization** — check required keys, types, aliases, and rules, with optional coercion.
- **Schema support** — reusable `@rule` blocks, `@use Rule;`, and default values.
- **Atomic saves** — safe writes with optional `.bak` backups.
- **Typed access** — `get_int`, `get_str`, `require`, and `ensure` helpers.
- **Diffing** — compare documents or files by flattened path.
- **Dict and JSON interop** — build documents from Python mappings or JSON.
- **CLI included** — inspect, validate, format, get, set, remove, merge, and diff files.
- **VS Code syntax highlighting** included in `vscode-cml/`.

## What's new in 1.1

- `@include "file.cml";` with relative paths, merge precedence, and cycle detection.
- `$env("NAME", fallback)` and `$ref("path")` resolution.
- `@use Rule;` plus `fill_defaults=True` for schema-driven defaults.
- Atomic saves with optional `.bak` backups.
- Typed document access with `require`, `get_int`, `get_str`, `ensure`, and friends.
- `camel.diff()` and new CLI commands for editing and comparing files.
- CI coverage on Python 3.10–3.13.

## Installation

Install from the repository:

```bash
git clone https://github.com/matkecn/camel.git
cd camel
python3 -m pip install -e .
```

The library has no third-party runtime dependencies.

## Quick start

```python
import camel

document = camel.load("SHOWCASE.cml")

print(document.init)                    # SHOWCASE
print(document.required)                # ['var1', 'var2']
print(document["Preson"]["name"])       # matija
print(document["Something"]["var2"])    # 18
print(document["Something"]["var3"])    # ['somevar', 10]
print(document["Something"]["var4"])    # {'some_var': 10}

data = document.to_dict()
print(data["Preson"]["age"])            # 18
```

Read straight into a plain Python mapping:

```python
data = camel.load("SHOWCASE.cml", as_dict=True)
```

## CML at a glance

```cml
@init <SHOWCASE>

@required var1 | var2;

@single var1 = "this_is_single_var"

@parent Preson {
    @use Person;
    @const @child name = "matija";
    @child age = 18;
    @child height = 187.0;
    @child var = null;
};

@deprecated
@scope Something {
    var1 = "matija";
    var2: %int = 18;
    var3: %list = ('somevar', 10);
    var4: %object = {
        some_var: %int = 10;
    };
    @optional var5;
};

@alias Preson P;

@rule Person {
    $name: %string;
    $age: %int;
    $height: %float;
};
```

## Syntax

| Construct | Meaning |
| --- | --- |
| `@init <NAME>` | Declares the document name. |
| `@include "path.cml";` | Merges another CML file into this document. |
| `@required a \| b;` | Requires keys to exist somewhere in the document. |
| `@single name = value` | A top-level value without a parent block. |
| `@parent Name { ... }` | A named parent block. |
| `@scope Name { ... }` | A named scope block. |
| `@use Rule;` | Applies a rule inside a parent or scope. |
| `@const` | Prevents a value from being changed. |
| `@child` | Marks an entry as a child entry. |
| `@optional` | Marks an entry as optional. |
| `@deprecated` | Adds block metadata. |
| `@alias Target Alias;` | Gives a parent/scope/single another name. |
| `@rule Name { ... }` | Defines a schema for validation. |
| `# comment` | A line comment. |

Values support strings, integers, floats, booleans, `null`, lists written as
`(...)` or `[...]`, objects written as `{ ... }`, and references such as
`$env("PORT", 8080)` or `$ref("server.host")`.

## Includes and references

Included files are loaded relative to the file that contains the `@include`.
Included values are merged first, so the current file wins on conflicts.

```cml
@include "defaults.cml";
@include "secrets.cml";

@single port = $env("PORT", 8080);
@single host = $ref("server.host");
```

```python
document = camel.load("config.cml", resolve_refs=True)
print(document["port"])   # 8080 unless PORT is set
```

Use `camel.load(path, resolve_includes=False)` when you want to inspect or format
the include statements instead of flattening them. `$env` casts values to the type
of the fallback, so `$env("PORT", 8080)` returns an integer.

## Python API

| Function | Purpose |
| --- | --- |
| `camel.load(path)` | Parse a file into a `CmlDocument`, resolving includes. |
| `camel.loads(text)` | Parse a string into a `CmlDocument`. |
| `camel.load(path, as_dict=True)` | Parse directly into a plain Python dict. |
| `camel.parse(text)` | Parse a string (same as `loads`). |
| `camel.parse_value(text)` | Parse one standalone CML value. |
| `camel.dump(doc, path, backup=True)` | Write a document atomically. |
| `camel.dumps(doc)` | Format a document as a string. |
| `camel.resolve_refs(doc, env=...)` | Resolve `$env` and `$ref` values. |
| `camel.diff(left, right)` | Compare documents or files by path. |
| `camel.new(init, required)` | Create a new empty document. |
| `camel.from_dict(data)` | Build a document from a Python mapping. |
| `camel.from_json(text)` | Build a document from JSON. |
| `camel.get(source, path)` | Read a value by path. |
| `camel.append(source, target, name, value)` | Append an entry. |
| `camel.change(source, path, value)` | Change a value by path. |
| `camel.remove(source, path)` | Remove a value by path. |
| `camel.merge(source, other)` | Merge documents or files. |
| `camel.sanitize(source)` | Validate and optionally coerce values. |
| `camel.validate(source)` | Alias for `sanitize`. |

All file helpers accept either a path or an already-loaded `CmlDocument`. The
`camel.Cml` facade exposes the same API as class methods.

## Document model

```python
document = camel.load("SHOWCASE.cml")

document.init                            # document name
document.required                        # list of required keys
document.singles["var1"].value           # single value
document.parents["Preson"]["name"]       # parent entry
document.scopes["Something"]["var3"]     # scope entry
document.aliases["P"]                    # "Preson"
document.rules["Person"].fields["age"]   # RuleField(type="int")

document.has_path("Preson.age")          # True
document.get_path("Preson.age")          # 18
document.require("Preson.age")           # 18 or CmlPathError
document.get_int("Preson.age")           # 18 or CmlTypeError
document.ensure("Preson.active", True)   # add only when missing
document.flatten()                       # {"parent.Preson.age": 18, ...}
dict(document.walk())                    # path -> Entry metadata
document.to_dict()                       # plain Python data
document.to_json(indent=2)               # JSON text
```

Typed helpers are available for `int`, `float`, `bool`, `str`, `list`, and `dict`:
`get_int`, `get_float`, `get_bool`, `get_str`, `get_list`, and `get_dict`.

## Editing

```python
document = camel.load("SHOWCASE.cml")

document.append("Preson", "job", "developer")
document.append("single", "enabled", True, type="bool")
document.set("Preson.age", 19)
document.change("Something.var2", 20)
document.remove_path("Preson.job")

document.save("updated.cml")
document.save("updated.cml", backup=True)  # writes updated.cml.bak
```

Saves are atomic by default. Pass `atomic=False` to `camel.dump` for direct writes.

File-based helpers save automatically:

```python
camel.append("config.cml", "Preson", "job", "developer")
camel.change("config.cml", "Preson.age", 19)
camel.remove("config.cml", "Preson.job")
print(camel.get("config.cml", "Preson.age"))
```

## Merging and defaults

```python
base = camel.from_dict({
    "parents": {"server": {"host": "localhost", "port": 8080}},
})

override = camel.from_dict({
    "parents": {"server": {"port": 9090, "debug": True}},
})

base.merge(override)
print(base["server"]["port"])   # 9090
print(base["server"]["debug"])  # True

base.merge(camel.from_dict({"parents": {"server": {"host": "example.com"}}}), overwrite=False)
print(base["server"]["host"])   # localhost
```

## Diffing

```python
changes = camel.diff("before.cml", "after.cml")
for change in changes:
    print(change.kind, change.path, change.old, change.new)
```

## Validation

```python
document = camel.load("SHOWCASE.cml")

report = camel.sanitize(document, coerce=True, strict=False)
if report.ok:
    print("CamelConfig is valid")
else:
    print(report)
```

`strict=True` raises `CmlValidationError` on the first invalid document.
`coerce=True` converts compatible values into their declared types.
`fill_defaults=True` fills missing rule fields from their defaults.

```python
report = camel.sanitize(document, fill_defaults=True, strict=False)
```

## Rules and defaults

```cml
@rule Person {
    $name: %string;
    $age: %int = 18;
    @optional $nick: %string;
};

@parent User {
    @use Person;
    @child name = "Ada";
};
```

```python
document = camel.load("config.cml")
report = camel.sanitize(document, fill_defaults=True, strict=False)
print(document["User"]["age"])   # 18
```

Rules can be applied explicitly with `@use` or by naming a parent/scope after the
rule. Missing non-optional fields are reported as validation errors.

## Dict and JSON interop

```python
document = camel.from_dict({
    "single": {"app": "demo"},
    "parents": {"server": {"host": "localhost", "port": 8080}},
    "required": ["app"],
}, init="Demo")

print(camel.dumps(document))

json_text = document.to_json(indent=2)
same = camel.from_json(json_text)
```

## CLI

```bash
cml read SHOWCASE.cml --meta
cml validate SHOWCASE.cml
cml validate SHOWCASE.cml --coerce --fix
cml validate SHOWCASE.cml --fill-defaults --fix
cml format SHOWCASE.cml
cml get SHOWCASE.cml Preson.age
cml set SHOWCASE.cml Preson.age 19
cml set SHOWCASE.cml Preson.age 19 --type int --dry-run
cml remove SHOWCASE.cml Preson.job
cml merge base.cml override.cml --output merged.cml
cml diff before.cml after.cml --json
```

The same commands work through the module:

```bash
python3 -m camel SHOWCASE.cml
python3 -m camel validate SHOWCASE.cml
python3 -m camel get SHOWCASE.cml Preson.age
```

## VS Code extension

The `vscode-cml/` folder contains a standalone syntax-highlighting extension for
`.cml` files.

```bash
cd vscode-cml
npm install -g @vscode/vsce
vsce package
code --install-extension cml-language-1.1.0.vsix
```

For development, open the `vscode-cml/` folder in VS Code and press `F5` to launch
an Extension Development Host.

## Project structure

```text
camel/
├── camel/              Python package
│   ├── parser.py       CML parser
│   ├── writer.py       canonical writer and atomic saves
│   ├── sanitizer.py    validation, coercion and defaults
│   ├── resolver.py     environment and path references
│   ├── diff.py         document comparison
│   ├── nodes.py        document model
│   ├── lexer.py        tokenizer
│   └── api.py          public API
├── tests/              unit tests
├── vscode-cml/         VS Code syntax extension
├── assets/             logo and branding
├── .github/            CI workflow
├── SHOWCASE.cml        language showcase
├── pyproject.toml
└── LICENSE
```

## Development

```bash
python3 -m pip install -e ".[dev]"
python3 -m unittest discover -s tests -v
python3 -m camel validate SHOWCASE.cml
python3 -m compileall -q camel
ruff check camel tests
```

## Contributing

Issues and pull requests are welcome. Keep changes focused, add tests for new
behavior, and run the test suite before opening a pull request.

## License

MIT © [matkecn](https://github.com/matkecn)

<p align="center">
  <img src="assets/logo.svg" alt="CamelConfig logo" width="560" />
</p>

<h1 align="center">CamelConfig</h1>

<p align="center">
  <strong>CML</strong> — a typed, human-friendly configuration language for Python.
</p>

<p align="center">
  <a href="https://github.com/matkecn/camel"><img src="https://img.shields.io/badge/version-1.0.0-F59E0B?style=flat-square&logo=semanticrelease&logoColor=white" alt="Version 1.0.0"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="tests/test_camel.py"><img src="https://img.shields.io/badge/tests-24%20passing-16A34A?style=flat-square&logo=checkmarx&logoColor=white" alt="24 tests passing"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-22C55E?style=flat-square&logo=opensourceinitiative&logoColor=white" alt="MIT license"></a>
  <a href="vscode-cml/"><img src="https://img.shields.io/badge/VS%20Code-CML-007ACC?style=flat-square&logo=visualstudiocode&logoColor=white" alt="VS Code extension"></a>
</p>

CamelConfig is a compact configuration language with a Pythonic feel. It gives you
structured parents and scopes, typed values, required keys, aliases, rules, comments,
and a clean canonical format. The Python package turns `.cml` files into native Python
objects and gives you safe tools for reading, writing, editing, validating, and merging
configuration.

## Highlights

- **Read and write** `.cml` files with a full parser and canonical writer.
- **Native Python values** — strings, ints, floats, booleans, `None`, lists, dicts, and references.
- **Typed entries** with `%string`, `%int`, `%float`, `%bool`, `%list`, `%object`, `%null`, and `%any`.
- **Safe mutation** — append, change, remove, and merge values by path.
- **Validation and sanitization** — check required keys, types, aliases, and rules, with optional coercion.
- **Schema support** — define reusable `@rule` blocks and validate matching parents/scopes.
- **Dict and JSON interop** — build documents from Python mappings or JSON.
- **CLI included** — inspect, validate, and format files from the terminal.
- **VS Code syntax highlighting** included in `vscode-cml/`.

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
| `@required a \| b;` | Requires keys to exist somewhere in the document. |
| `@single name = value` | A top-level value without a parent block. |
| `@parent Name { ... }` | A named parent block. |
| `@scope Name { ... }` | A named scope block. |
| `@const` | Prevents a value from being changed. |
| `@child` | Marks an entry as a child entry. |
| `@optional` | Marks an entry as optional. |
| `@deprecated` | Adds block metadata. |
| `@alias Target Alias;` | Gives a parent/scope/single another name. |
| `@rule Name { ... }` | Defines a schema for validation. |
| `# comment` | A line comment. |

Values support strings, integers, floats, booleans, `null`, lists written as
`(...)` or `[...]`, objects written as `{ ... }`, and references such as `$name`
or `$hash()`.

## Python API

| Function | Purpose |
| --- | --- |
| `camel.load(path)` | Parse a file into a `CmlDocument`. |
| `camel.loads(text)` | Parse a string into a `CmlDocument`. |
| `camel.load(path, as_dict=True)` | Parse directly into a plain Python dict. |
| `camel.parse(text)` | Parse a string (same as `loads`). |
| `camel.parse_value(text)` | Parse one standalone CML value. |
| `camel.dump(doc, path)` | Write a document to a file. |
| `camel.dumps(doc)` | Format a document as a string. |
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
document.flatten()                       # {"parent.Preson.age": 18, ...}
dict(document.walk())                    # path -> Entry metadata
document.to_dict()                       # plain Python data
document.to_json(indent=2)               # JSON text
```

## Editing

```python
document = camel.load("SHOWCASE.cml")

document.append("Preson", "job", "developer")
document.append("single", "enabled", True, type="bool")
document.set("Preson.age", 19)
document.change("Something.var2", 20)
document.remove_path("Preson.job")

document.save("updated.cml")
```

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
cml format SHOWCASE.cml
```

The same commands work through the module:

```bash
python3 -m camel SHOWCASE.cml
python3 -m camel validate SHOWCASE.cml
```

## VS Code extension

The `vscode-cml/` folder contains a standalone syntax-highlighting extension for
`.cml` files.

```bash
cd vscode-cml
npm install -g @vscode/vsce
vsce package
code --install-extension cml-language-1.0.0.vsix
```

For development, open the `vscode-cml/` folder in VS Code and press `F5` to launch
an Extension Development Host.

## Project structure

```text
camel/
├── camel/              Python package
│   ├── parser.py       CML parser
│   ├── writer.py       canonical writer
│   ├── sanitizer.py    validation and coercion
│   ├── nodes.py        document model
│   ├── lexer.py        tokenizer
│   └── api.py          public API
├── tests/              unit tests
├── vscode-cml/         VS Code syntax extension
├── assets/             logo and branding
├── SHOWCASE.cml        language showcase
├── pyproject.toml
└── LICENSE
```

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m camel validate SHOWCASE.cml
python3 -m compileall -q camel
```

## Contributing

Issues and pull requests are welcome. Keep changes focused, add tests for new
behavior, and run the test suite before opening a pull request.

## License

MIT © [matkecn](https://github.com/matkecn)

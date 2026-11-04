from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import camel
from camel.__main__ import main as cli_main

SHOWCASE = Path(__file__).resolve().parents[1] / "SHOWCASE.cml"


class ShowcaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = SHOWCASE.read_text(encoding="utf-8")
        self.document = camel.loads(self.text)

    def test_document_structure(self) -> None:
        document = self.document
        self.assertEqual(document.init, "SHOWCASE")
        self.assertEqual(document.required, ["var1", "var2"])
        self.assertEqual(document.singles["var1"].value, "this_is_single_var")
        self.assertIn("Preson", document.parents)
        self.assertIn("Something", document.scopes)
        self.assertEqual(document.aliases, {"P": "Preson"})
        self.assertIn("Person", document.rules)

    def test_parent_values(self) -> None:
        person = self.document.parents["Preson"]
        self.assertEqual(person["name"], "matija")
        self.assertEqual(person["age"], 18)
        self.assertEqual(person["height"], 187.0)
        self.assertIsNone(person["var"])
        self.assertTrue(person.entries["name"].const)
        self.assertTrue(person.entries["name"].child)

    def test_scope_values(self) -> None:
        scope = self.document.scopes["Something"]
        self.assertEqual(scope["var1"], "matija")
        self.assertEqual(scope["var2"], 18)
        self.assertEqual(scope["var3"], ["somevar", 10])
        self.assertEqual(scope["var4"]["some_var"], 10)
        self.assertEqual(scope["var4"].types["some_var"], "int")
        self.assertTrue(scope.entries["var5"].optional)
        self.assertFalse(scope.entries["var5"].has_value)
        self.assertEqual(scope.decorators, ["deprecated"])

    def test_rule_values(self) -> None:
        rule = self.document.rules["Person"]
        self.assertEqual(rule.fields["name"].type, "string")
        self.assertEqual(rule.fields["age"].type, "int")
        self.assertEqual(rule.fields["height"].type, "float")

    def test_to_dict_returns_native_objects(self) -> None:
        data = self.document.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["single"]["var1"], "this_is_single_var")
        self.assertEqual(data["Preson"]["name"], "matija")
        self.assertIsInstance(data["Preson"]["age"], int)
        self.assertIsInstance(data["Preson"]["height"], float)
        self.assertIsInstance(data["Something"]["var3"], list)
        self.assertIsInstance(data["Something"]["var4"], dict)

    def test_as_dict_load(self) -> None:
        data = camel.loads(self.text, as_dict=True)
        self.assertEqual(data["Something"]["var2"], 18)

    def test_path_access(self) -> None:
        self.assertEqual(self.document.get_path("Preson.age"), 18)
        self.assertEqual(self.document.get_path("Something.var3"), ["somevar", 10])
        self.assertEqual(self.document.get_path("single.var1"), "this_is_single_var")
        self.assertIs(self.document.get_path("P"), self.document.parents["Preson"])

    def test_roundtrip(self) -> None:
        formatted = camel.dumps(self.document)
        self.assertIn("@single var1", formatted)
        reparsed = camel.loads(formatted)
        self.assertEqual(
            reparsed.to_dict(include_meta=True),
            self.document.to_dict(include_meta=True),
        )


class MutationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = camel.loads(SHOWCASE.read_text(encoding="utf-8"))

    def test_append_and_change(self) -> None:
        self.document.append("Preson", "job", "developer")
        self.document.append("single", "enabled", True, type="bool")
        self.document.set("Preson.age", 19)
        self.document.set("Something.var2", 20)
        self.document.change("single.var1", "changed")
        self.assertEqual(self.document.parents["Preson"]["job"], "developer")
        self.assertTrue(self.document.singles["enabled"].value)
        self.assertEqual(self.document.parents["Preson"]["age"], 19)
        self.assertEqual(self.document.scopes["Something"]["var2"], 20)
        self.assertEqual(self.document.singles["var1"].value, "changed")

    def test_const_is_protected(self) -> None:
        with self.assertRaises(camel.CmlTypeError):
            self.document.set("Preson.name", "someone")
        with self.assertRaises(camel.CmlTypeError):
            self.document.remove_path("Preson.name")

    def test_remove(self) -> None:
        self.document.append("Preson", "temporary", 1)
        self.assertEqual(self.document.remove_path("Preson.temporary"), 1)
        self.assertNotIn("temporary", self.document.parents["Preson"])

    def test_file_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.cml"
            path.write_text(camel.dumps(self.document), encoding="utf-8")
            camel.append(str(path), "Preson", "job", "developer")
            camel.change(str(path), "Preson.age", 21)
            loaded = camel.load(str(path))
            self.assertEqual(loaded.parents["Preson"]["job"], "developer")
            self.assertEqual(loaded.parents["Preson"]["age"], 21)


class SanitizeTests(unittest.TestCase):
    def test_valid_showcase(self) -> None:
        document = camel.loads(SHOWCASE.read_text(encoding="utf-8"))
        report = camel.sanitize(document, strict=False)
        self.assertTrue(report.ok)
        self.assertEqual(report.errors, [])

    def test_missing_required(self) -> None:
        document = camel.loads("@init <bad>\n@required missing;\n")
        report = camel.sanitize(document, strict=False)
        self.assertFalse(report.ok)
        self.assertTrue(any(issue.path == "required.missing" for issue in report.errors))

    def test_type_error(self) -> None:
        document = camel.loads('@init <bad>\n@parent P {\n    @child x: %int = "nope";\n};\n')
        report = camel.sanitize(document, strict=False)
        self.assertFalse(report.ok)
        self.assertTrue(any(issue.path == "parent.P.x" for issue in report.errors))

    def test_coerce(self) -> None:
        document = camel.loads('@init <bad>\n@parent P {\n    @child x: %int = "10";\n};\n')
        report = camel.sanitize(document, coerce=True, strict=False)
        self.assertTrue(report.ok)
        self.assertEqual(document.parents["P"]["x"], 10)
        self.assertTrue(report.changed)

    def test_strict_raises(self) -> None:
        document = camel.loads("@init <bad>\n@required missing;\n")
        with self.assertRaises(camel.CmlValidationError):
            camel.sanitize(document)


class AdvancedApiTests(unittest.TestCase):
    def test_new_and_from_dict(self) -> None:
        document = camel.from_dict(
            {
                "single": {"app": "demo"},
                "parents": {"server": {"host": "localhost", "port": 8080}},
                "required": ["app"],
            },
            init="Demo",
        )
        self.assertEqual(document.init, "Demo")
        self.assertEqual(document["server"]["port"], 8080)
        self.assertEqual(document.parents["server"].entries["port"].type, "int")
        formatted = camel.dumps(document)
        self.assertIn("@init <Demo>", formatted)
        self.assertIn("%int", formatted)

    def test_flat_dict(self) -> None:
        document = camel.from_dict({"name": "demo", "server": {"port": 8080}})
        self.assertIsInstance(document.parents["server"], camel.Parent)
        self.assertEqual(document.singles["name"].value, "demo")
        self.assertEqual(document.flatten()["parent.server.port"], 8080)

    def test_walk_has_path_setdefault(self) -> None:
        document = camel.from_dict({"server": {"port": 8080}})
        self.assertTrue(document.has_path("server.port"))
        self.assertFalse(document.has_path("server.host"))
        self.assertEqual(document.setdefault_path("server.host", "localhost"), "localhost")
        self.assertEqual(document.setdefault_path("server.host", "other"), "localhost")
        paths = dict(document.walk())
        self.assertIn("parent.server.port", paths)

    def test_merge(self) -> None:
        base = camel.from_dict({"single": {"a": 1}, "parents": {"p": {"x": 1, "y": 2}}})
        override = camel.from_dict(
            {"single": {"a": 9, "b": 3}, "parents": {"p": {"y": 20}, "q": {"z": 4}}}
        )
        base.merge(override)
        self.assertEqual(base.singles["a"].value, 9)
        self.assertEqual(base.singles["b"].value, 3)
        self.assertEqual(base.parents["p"]["y"], 20)
        self.assertEqual(base.parents["q"]["z"], 4)
        base.merge(camel.from_dict({"single": {"a": 100}}), overwrite=False)
        self.assertEqual(base.singles["a"].value, 9)

    def test_json(self) -> None:
        document = camel.from_dict({"single": {"a": 1}, "parents": {"p": {"x": True}}})
        text = document.to_json()
        other = camel.from_json(text)
        self.assertEqual(other.to_dict(), document.to_dict())

    def test_parse_value(self) -> None:
        self.assertEqual(camel.parse_value("(1, 'two', true, null)"), [1, "two", True, None])

    def test_file_get_remove_merge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.cml"
            path.write_text('@init <test>\n@parent P {\n    x = 1;\n};\n', encoding="utf-8")
            self.assertEqual(camel.get(str(path), "P.x"), 1)
            camel.change(str(path), "P.y", 2)
            camel.remove(str(path), "P.x")
            document = camel.load(str(path))
            self.assertFalse(document.has_path("P.x"))
            self.assertEqual(document.get_path("P.y"), 2)
            camel.merge(str(path), {"parents": {"P": {"z": 3}}})
            self.assertEqual(camel.get(str(path), "P.z"), 3)


class IncludeTests(unittest.TestCase):
    def test_load_includes_and_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            defaults = root / "defaults.cml"
            defaults.write_text(
                '@init <Defaults>\n@single host = "localhost";\n'
                "@parent server {\n    port = 80;\n};\n",
                encoding="utf-8",
            )
            app = root / "app.cml"
            app.write_text(
                '@include "defaults.cml";\n@init <App>\n'
                '@single host = "example.com";\n'
                "@parent server {\n    port = 8080;\n};\n",
                encoding="utf-8",
            )
            document = camel.load(app)
            self.assertEqual(document.init, "App")
            self.assertEqual(document.singles["host"].value, "example.com")
            self.assertEqual(document.parents["server"]["port"], 8080)
            self.assertEqual(document.includes, [])

    def test_load_preserves_includes_when_not_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "defaults.cml").write_text("@single a = 1;\n", encoding="utf-8")
            app = root / "app.cml"
            app.write_text('@include "defaults.cml";\n@single b = 2;\n', encoding="utf-8")
            document = camel.load(app, resolve_includes=False)
            self.assertEqual([include.path for include in document.includes], ["defaults.cml"])
            self.assertIn('@include "defaults.cml";', camel.dumps(document))

    def test_include_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.cml"
            second = root / "second.cml"
            first.write_text('@include "second.cml";\n', encoding="utf-8")
            second.write_text('@include "first.cml";\n', encoding="utf-8")
            with self.assertRaises(camel.CmlIncludeError):
                camel.load(first)

    def test_missing_include(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.cml"
            path.write_text('@include "missing.cml";\n', encoding="utf-8")
            with self.assertRaises(camel.CmlIncludeError):
                camel.load(path)

    def test_loads_requires_base_dir_for_includes(self) -> None:
        with self.assertRaises(camel.CmlIncludeError):
            camel.loads('@include "defaults.cml";\n', resolve_includes=True)


class ResolverTests(unittest.TestCase):
    def test_env_and_ref(self) -> None:
        document = camel.loads(
            '@single host = $env("HOST", "localhost");\n'
            '@single port = $env("PORT", 8080);\n'
            '@single url = $ref("host");\n'
        )
        resolved = camel.resolve_refs(document, env={"PORT": "9090"})
        self.assertEqual(resolved.singles["host"].value, "localhost")
        self.assertEqual(resolved.singles["port"].value, 9090)
        self.assertEqual(resolved.singles["url"].value, "localhost")
        self.assertIsInstance(document.singles["host"].value, camel.CmlReference)

    def test_missing_env_strict(self) -> None:
        document = camel.loads('@single value = $env("MISSING");\n')
        with self.assertRaises(camel.CmlReferenceError):
            camel.resolve_refs(document, env={})

    def test_ref_cycle(self) -> None:
        document = camel.loads(
            '@single a = $ref("b");\n@single b = $ref("a");\n'
        )
        with self.assertRaises(camel.CmlReferenceError):
            camel.resolve_refs(document)

    def test_load_resolve_refs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.cml"
            path.write_text('@single value = $env("VALUE");\n', encoding="utf-8")
            document = camel.load(path, resolve_refs=True, env={"VALUE": "ready"})
            self.assertEqual(document.singles["value"].value, "ready")

    def test_resolve_refs_does_not_mutate_nested_original(self) -> None:
        document = camel.loads(
            '@single config: %object = { value = $env("VALUE"); };\n'
        )
        resolved = camel.resolve_refs(document, env={"VALUE": "ready"})
        self.assertEqual(resolved.singles["config"].value["value"], "ready")
        self.assertIsInstance(
            document.singles["config"].value["value"],
            camel.CmlReference,
        )


class RuleUseTests(unittest.TestCase):
    def test_use_rule_and_fill_defaults(self) -> None:
        document = camel.loads(
            "@rule Person {\n"
            "    $name: %string;\n"
            "    $age: %int = 18;\n"
            "    @optional $nick: %string;\n"
            "};\n"
            "@parent P {\n"
            "    @use Person;\n"
            '    @child name = "Ada";\n'
            "};\n"
        )
        report = camel.sanitize(document, fill_defaults=True, strict=False)
        self.assertTrue(report.ok, str(report))
        self.assertEqual(document.parents["P"]["age"], 18)
        formatted = camel.dumps(document)
        self.assertIn("@use Person;", formatted)
        self.assertEqual(camel.loads(formatted).parents["P"].uses, ["Person"])

    def test_use_rule_missing_required(self) -> None:
        document = camel.loads(
            "@rule Person {\n    $name: %string;\n};\n"
            "@parent P {\n    @use Person;\n};\n"
        )
        report = camel.sanitize(document, strict=False)
        self.assertFalse(report.ok)
        self.assertTrue(any(issue.path == "parent.P.name" for issue in report.errors))

    def test_unknown_use(self) -> None:
        document = camel.loads("@parent P {\n    @use Missing;\n};\n")
        report = camel.sanitize(document, strict=False)
        self.assertFalse(report.ok)
        self.assertTrue(any(issue.path == "parent.P.use.Missing" for issue in report.errors))


class AtomicSaveTests(unittest.TestCase):
    def test_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.cml"
            path.write_text("@single value = 1;\n", encoding="utf-8")
            document = camel.load(path)
            document.set("single.value", 2)
            camel.dump(document, path, backup=True)
            self.assertEqual(path.read_text(encoding="utf-8"), "@single value = 2;\n")
            backup = path.with_name("config.cml.bak")
            self.assertEqual(backup.read_text(encoding="utf-8"), "@single value = 1;\n")

    def test_non_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.cml"
            camel.dump(camel.from_dict({"value": 1}), path, atomic=False)
            self.assertEqual(camel.load(path).singles["value"].value, 1)


class TypedAccessTests(unittest.TestCase):
    def test_typed_getters_and_ensure(self) -> None:
        document = camel.from_dict(
            {
                "single": {
                    "count": 3,
                    "ratio": 1.5,
                    "enabled": True,
                    "name": "demo",
                    "items": [1, 2],
                    "meta": {"a": 1},
                }
            }
        )
        self.assertEqual(document.get_int("count"), 3)
        self.assertEqual(document.get_float("ratio"), 1.5)
        self.assertTrue(document.get_bool("enabled"))
        self.assertEqual(document.get_str("name"), "demo")
        self.assertEqual(document.get_list("items"), [1, 2])
        self.assertEqual(document.get_dict("meta"), {"a": 1})
        self.assertEqual(document.get_int("missing", 7), 7)
        self.assertEqual(document.ensure("count", 9), 3)
        self.assertEqual(document.ensure("new", 5, "int"), 5)
        with self.assertRaises(camel.CmlPathError):
            document.require("missing")
        with self.assertRaises(camel.CmlPathError):
            document.get_int("missing")
        with self.assertRaises(camel.CmlTypeError):
            document.get_int("name")


class DiffTests(unittest.TestCase):
    def test_diff_documents(self) -> None:
        left = camel.from_dict({"single": {"a": 1, "b": 2}, "parents": {"p": {"x": 1}}})
        right = camel.from_dict(
            {"single": {"a": 1, "b": 3, "c": 4}, "parents": {"p": {"x": 1}}}
        )
        changes = camel.diff(left, right)
        self.assertEqual(
            [(change.kind, change.path) for change in changes],
            [("changed", "single.b"), ("added", "single.c")],
        )
        self.assertEqual(changes[0].to_dict()["old"], 2)


class CliTests(unittest.TestCase):
    def test_get_set_remove_merge_diff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "config.cml"
            path.write_text(
                '@init <Test>\n@single a = 1;\n@parent P {\n    x = 2;\n};\n',
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli_main(["get", str(path), "P.x"]), 0)
            self.assertEqual(output.getvalue().strip(), "2")

            self.assertEqual(cli_main(["set", str(path), "P.y", "3"]), 0)
            self.assertEqual(camel.load(path).parents["P"]["y"], 3)

            self.assertEqual(cli_main(["set", str(path), "P.z", "4", "--type", "int"]), 0)
            self.assertEqual(camel.load(path).parents["P"]["z"], 4)

            self.assertEqual(cli_main(["remove", str(path), "P.x"]), 0)
            self.assertFalse(camel.load(path).has_path("P.x"))

            other = root / "other.cml"
            other.write_text("@parent Q {\n    z = 9;\n};\n", encoding="utf-8")
            self.assertEqual(cli_main(["merge", str(path), str(other)]), 0)
            self.assertEqual(camel.load(path).parents["Q"]["z"], 9)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli_main(["diff", str(path), str(other), "--json"]), 0)
            self.assertIn('"path"', output.getvalue())

    def test_validate_fill_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.cml"
            path.write_text(
                "@rule Person {\n    $age: %int = 18;\n};\n"
                "@parent P {\n    @use Person;\n};\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli_main(["validate", str(path), "--fill-defaults", "--fix"]), 0)
            self.assertEqual(camel.load(path).parents["P"]["age"], 18)


if __name__ == "__main__":
    unittest.main()

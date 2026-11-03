from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import camel

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


if __name__ == "__main__":
    unittest.main()

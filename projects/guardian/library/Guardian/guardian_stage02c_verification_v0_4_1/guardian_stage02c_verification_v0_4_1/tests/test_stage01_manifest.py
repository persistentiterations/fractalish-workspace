import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from guardian import ManifestParser


BODY = "\ndef add(a, b):\n    return a + b\n"


def manifest(
    name="Strict Test",
    version="1.0.0",
    purpose="Exercise strict manifest validation",
    dependencies="stdlib",
):
    return (
        "# --- MANIFEST BEGIN ---\n"
        f"# name: {name}\n"
        f"# version: {version}\n"
        f"# purpose: {purpose}\n"
        f"# dependencies: {dependencies}\n"
        "# --- MANIFEST END ---\n"
        + BODY
    )


class Stage01ManifestTests(unittest.TestCase):
    def parse(self, content):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "case.py"
            path.write_text(content, encoding="utf-8")
            return ManifestParser.parse(path)

    def codes(self, content):
        return [issue.code for issue in self.parse(content)[1]]

    def test_valid(self):
        parsed, issues = self.parse(manifest())
        self.assertEqual(issues, [])
        self.assertEqual(parsed["dependencies"], "stdlib")

    def test_missing(self):
        _, issues = self.parse(BODY)
        self.assertEqual(issues[0].code, "manifest_missing")
        self.assertEqual(issues[0].severity, "hold")

    def test_duplicate_begin(self):
        content = manifest().replace(
            "# --- MANIFEST BEGIN ---",
            "# --- MANIFEST BEGIN ---\n# --- MANIFEST BEGIN ---",
            1,
        )
        self.assertIn("manifest_begin_count", self.codes(content))

    def test_duplicate_end(self):
        self.assertIn(
            "manifest_end_count",
            self.codes(manifest() + "\n# --- MANIFEST END ---\n"),
        )

    def test_end_before_begin(self):
        codes = self.codes("# --- MANIFEST END ---\n" + manifest())
        self.assertTrue(
            "manifest_end_count" in codes or "manifest_marker_order" in codes
        )

    def test_duplicate_field(self):
        content = manifest().replace(
            "# purpose: Exercise strict manifest validation",
            "# purpose: Exercise strict manifest validation\n# purpose: duplicate",
        )
        self.assertIn("manifest_duplicate_field", self.codes(content))

    def test_unknown_field(self):
        content = manifest().replace(
            "# dependencies: stdlib",
            "# dependencies: stdlib\n# surprise: value",
        )
        self.assertIn("manifest_unknown_field", self.codes(content))

    def test_missing_required(self):
        content = manifest().replace(
            "# purpose: Exercise strict manifest validation\n", ""
        )
        self.assertIn("manifest_missing_fields", self.codes(content))

    def test_empty_value(self):
        self.assertIn("manifest_empty_value", self.codes(manifest(purpose="")))

    def test_malformed_line(self):
        content = manifest().replace(
            "# purpose: Exercise strict manifest validation",
            "# line without separator",
        )
        self.assertIn("manifest_malformed_line", self.codes(content))

    def test_uncommented_line(self):
        content = manifest().replace(
            "# purpose: Exercise strict manifest validation",
            "purpose: not commented",
        )
        self.assertIn("manifest_uncommented_line", self.codes(content))

    def test_blank_line(self):
        content = manifest().replace(
            "# purpose: Exercise strict manifest validation",
            "# purpose: Exercise strict manifest validation\n",
        )
        self.assertIn("manifest_blank_line", self.codes(content))

    def test_invalid_version(self):
        self.assertIn(
            "manifest_invalid_version",
            self.codes(manifest(version="one")),
        )

    def test_invalid_dependency_syntax(self):
        self.assertIn(
            "manifest_invalid_dependencies",
            self.codes(manifest(dependencies="requests, ")),
        )

    def test_none_alone(self):
        self.assertEqual(self.parse(manifest(dependencies="none"))[1], [])

    def test_stdlib_alone(self):
        self.assertEqual(self.parse(manifest(dependencies="stdlib"))[1], [])

    def test_standard_library_alone(self):
        self.assertEqual(
            self.parse(manifest(dependencies="standard library"))[1], []
        )

    def test_package_list(self):
        self.assertEqual(
            self.parse(manifest(dependencies="requests, numpy"))[1], []
        )

    def test_none_mixed(self):
        self.assertIn(
            "manifest_reserved_dependency_mixed",
            self.codes(manifest(dependencies="none, requests")),
        )

    def test_stdlib_mixed(self):
        self.assertIn(
            "manifest_reserved_dependency_mixed",
            self.codes(manifest(dependencies="stdlib, pandas")),
        )

    def test_standard_library_mixed(self):
        self.assertIn(
            "manifest_reserved_dependency_mixed",
            self.codes(manifest(dependencies="standard library, requests")),
        )

    def test_reserved_after_package(self):
        self.assertIn(
            "manifest_reserved_dependency_mixed",
            self.codes(manifest(dependencies="requests, none")),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

import json
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SCHEMAS = BASE / "config" / "schemas"

class Stage0ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = {
            path.name: path.read_text(encoding="utf-8")
            for path in BASE.glob("*.md")
        }
        cls.schema_objects = {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(SCHEMAS.glob("*.json"))
        }
        cls.config = json.loads(
            (BASE / "config" / "product.example.json").read_text(encoding="utf-8")
        )

    def test_01_required_documents_exist(self):
        required = {
            "README.md",
            "PRODUCT_CONTRACT.md",
            "SUPPORTED_ENVIRONMENT.md",
            "AUTHORITY_BOUNDARY.md",
            "CLAIM_BOUNDARY.md",
            "STAGE_0_GATES.md",
        }
        self.assertTrue(required.issubset(self.docs))

    def test_02_four_schemas_exist(self):
        self.assertEqual(
            set(self.schema_objects),
            {
                "action_request.schema.json",
                "evidence.schema.json",
                "gateway_decision.schema.json",
                "receipt.schema.json",
            },
        )

    def test_03_schema_ids_unique(self):
        ids = [schema["$id"] for schema in self.schema_objects.values()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_04_action_pair_exact(self):
        request = self.schema_objects["action_request.schema.json"]
        self.assertEqual(
            request["properties"]["requested_action"]["enum"],
            ["HOLD", "RELEASE"],
        )

    def test_05_request_disallows_extra_properties(self):
        self.assertFalse(
            self.schema_objects["action_request.schema.json"]["additionalProperties"]
        )

    def test_06_gateway_disallows_extra_properties(self):
        self.assertFalse(
            self.schema_objects["gateway_decision.schema.json"]["additionalProperties"]
        )

    def test_07_request_requires_container_id(self):
        required = self.schema_objects["action_request.schema.json"]["required"]
        self.assertIn("container_id", required)
        self.assertNotIn("container_name", required)

    def test_08_no_command_fields_in_request(self):
        properties = self.schema_objects["action_request.schema.json"]["properties"]
        forbidden = {
            "command",
            "shell",
            "args",
            "docker_socket",
            "executable",
            "target_pattern",
        }
        self.assertTrue(forbidden.isdisjoint(properties))

    def test_09_projection_disabled_by_default(self):
        self.assertIs(self.config["actions"]["projection_enabled"], False)

    def test_10_supported_scope_is_one_linux_container(self):
        text = self.docs["SUPPORTED_ENVIRONMENT.md"]
        self.assertIn("one configured Linux Docker container", text)
        self.assertIn("multiple monitored containers", text)

    def test_11_frozen_commit_bound(self):
        self.assertIn(
            "0d6de321ccac75bf8d634663396a0a4279b72261",
            self.docs["README.md"],
        )

    def test_12_later_stage_source_requires_advancement_record(self):
        forbidden_top_level = {"gateway", "installer", "service"}
        existing = {path.name for path in BASE.iterdir() if path.is_dir()}
        self.assertTrue(forbidden_top_level.isdisjoint(existing))

        if (BASE / "src").exists():
            self.assertTrue((BASE / "README_STAGE_1.md").is_file())

if __name__ == "__main__":
    unittest.main()

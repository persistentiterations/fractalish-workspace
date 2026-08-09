from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PRODUCT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bolt_on_continuity_v0_2 import ALLOWED_ACTIONS, PRODUCT_VERSION, STAGE
from bolt_on_continuity_v0_2.engine_boundary import (
    BoundaryValidationError,
    load_boundary,
)


class Stage1ScaffoldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest_path = PRODUCT_ROOT / "config" / "frozen_engine_boundary.json"
        self.payload = load_boundary(self.manifest_path)

    def write_payload(self, payload: dict) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json", delete=False
        )
        with handle:
            json.dump(payload, handle, sort_keys=True)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return Path(handle.name)

    def test_product_identity(self) -> None:
        self.assertEqual(PRODUCT_VERSION, "0.2")
        self.assertEqual(STAGE, 1)
        self.assertEqual(ALLOWED_ACTIONS, ("NO_ACTION", "HOLD", "RELEASE"))

    def test_boundary_loads(self) -> None:
        self.assertEqual(self.payload["schema_version"], 1)
        self.assertEqual(self.payload["stage"], 1)
        self.assertEqual(len(self.payload["components"]), 7)

    def test_all_components_are_candidate_only(self) -> None:
        self.assertTrue(
            all(item["disposition"] == "candidate_only" for item in self.payload["components"])
        )

    def test_duplicate_component_is_rejected(self) -> None:
        altered = copy.deepcopy(self.payload)
        altered["components"].append(copy.deepcopy(altered["components"][0]))
        with self.assertRaises(BoundaryValidationError):
            load_boundary(self.write_payload(altered))

    def test_path_escape_is_rejected(self) -> None:
        altered = copy.deepcopy(self.payload)
        altered["components"][0]["source_path"] = "../outside.py"
        with self.assertRaises(BoundaryValidationError):
            load_boundary(self.write_payload(altered))

    def test_action_expansion_is_rejected(self) -> None:
        altered = copy.deepcopy(self.payload)
        altered["allowed_actions"].append("RESTART")
        with self.assertRaises(BoundaryValidationError):
            load_boundary(self.write_payload(altered))

    def test_extra_top_level_field_is_rejected(self) -> None:
        altered = copy.deepcopy(self.payload)
        altered["unexpected"] = True
        with self.assertRaises(BoundaryValidationError):
            load_boundary(self.write_payload(altered))


if __name__ == "__main__":
    unittest.main()

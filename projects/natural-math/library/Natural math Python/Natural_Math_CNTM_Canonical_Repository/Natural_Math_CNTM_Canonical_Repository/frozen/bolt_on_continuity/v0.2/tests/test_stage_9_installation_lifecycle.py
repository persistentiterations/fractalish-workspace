from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on_continuity_v0_2.installation_lifecycle import (
    DELETE_CONFIRMATION,
    LifecycleError,
    plan_install,
    plan_uninstall,
    validate_plan,
)
from bolt_on_continuity_v0_2.product_configuration import build_configuration


class Stage9InstallationLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        enrollment = {
            "container_id": "a" * 64,
            "display_name": "demo",
            "image": "demo:latest",
            "observation_only": True,
            "gateway_enabled": False,
        }
        self.configuration = build_configuration(enrollment)

    def test_clean_install_plan(self) -> None:
        result = plan_install(self.configuration, "ABSENT").payload
        self.assertEqual(result["outcome"], "PLAN_INSTALL")
        self.assertEqual(len(result["operations"]), 3)
        self.assertEqual(validate_plan(result), result)

    def test_repeat_install_has_no_duplicate_work(self) -> None:
        result = plan_install(self.configuration, "INSTALLED").payload
        self.assertEqual(result["outcome"], "ALREADY_INSTALLED")
        self.assertEqual(result["operations"], [])

    def test_partial_install_fails_closed(self) -> None:
        result = plan_install(self.configuration, "PARTIAL").payload
        self.assertEqual(result["outcome"], "FAIL_CLOSED_PARTIAL")
        self.assertEqual(result["operations"], [])

    def test_conflicting_install_fails_closed(self) -> None:
        result = plan_install(self.configuration, "CONFLICT").payload
        self.assertEqual(result["outcome"], "FAIL_CLOSED_CONFLICT")

    def test_unknown_state_rejected(self) -> None:
        with self.assertRaises(LifecycleError):
            plan_install(self.configuration, "UNKNOWN")

    def test_uninstall_defaults_to_retain_data(self) -> None:
        result = plan_uninstall(self.configuration, "INSTALLED").payload
        self.assertEqual(result["outcome"], "PLAN_UNINSTALL_RETAIN_DATA")
        self.assertEqual(result["data_choice"], "RETAIN_DATA")
        self.assertNotIn("DELETE_PRODUCT_DATA", [item["operation"] for item in result["operations"]])

    def test_confirmed_delete_data_plan(self) -> None:
        result = plan_uninstall(
            self.configuration,
            "INSTALLED",
            data_choice="DELETE_DATA",
            confirmation=DELETE_CONFIRMATION,
        ).payload
        self.assertEqual(result["outcome"], "PLAN_UNINSTALL_DELETE_DATA")
        self.assertIn("DELETE_PRODUCT_DATA", [item["operation"] for item in result["operations"]])

    def test_delete_without_exact_confirmation_fails_closed(self) -> None:
        result = plan_uninstall(self.configuration, "INSTALLED", data_choice="DELETE_DATA", confirmation="delete receipt data").payload
        self.assertEqual(result["outcome"], "FAIL_CLOSED_CONFIRMATION")
        self.assertEqual(result["operations"], [])

    def test_already_absent_uninstall(self) -> None:
        result = plan_uninstall(self.configuration, "ABSENT").payload
        self.assertEqual(result["outcome"], "ALREADY_ABSENT")
        self.assertEqual(result["operations"], [])

    def test_protected_container_never_operation_target(self) -> None:
        result = plan_install(self.configuration, "ABSENT").payload
        protected = result["protected_subject"]
        self.assertTrue(all(protected not in item["target"] for item in result["operations"]))

    def test_safe_defaults_are_fixed(self) -> None:
        result = plan_install(self.configuration, "ABSENT").payload
        self.assertEqual(result["safe_defaults"], {
            "container_mutation_authorized": False,
            "gateway_enabled": False,
            "native_execution_authorized": False,
            "observation_only": True,
        })

    def test_canonical_serialization_is_stable(self) -> None:
        first = plan_install(self.configuration, "ABSENT")
        second = plan_install(copy.deepcopy(self.configuration), "ABSENT")
        self.assertEqual(first.canonical_bytes(), second.canonical_bytes())
        self.assertEqual(first.payload["plan_digest"], second.payload["plan_digest"])

    def test_digest_tampering_rejected(self) -> None:
        result = plan_install(self.configuration, "ABSENT").payload
        result["plan_digest"] = "sha256:" + "0" * 64
        with self.assertRaises(LifecycleError):
            validate_plan(result)

    def test_no_side_effect_imports(self) -> None:
        source = (SRC / "bolt_on_continuity_v0_2/installation_lifecycle.py").read_text(encoding="utf-8")
        for token in ("subprocess", "os.system", "Popen(", "open(", "write_text(", "write_bytes(", "mkdir(", "docker "):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()

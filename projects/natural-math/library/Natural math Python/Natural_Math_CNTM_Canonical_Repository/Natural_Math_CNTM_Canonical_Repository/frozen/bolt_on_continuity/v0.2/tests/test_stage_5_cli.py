from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bolt_on_continuity_v0_2.local_cli import ALLOWED_COMMANDS, ALLOWED_STATES, run_command
from bolt_on_continuity_v0_2.product_configuration import build_configuration, serialize_configuration


CONTAINER_ID = "a" * 64


def config_bytes() -> bytes:
    enrollment = {
        "container_id": CONTAINER_ID,
        "display_name": "example",
        "gateway_enabled": False,
        "image": "example:1",
        "observation_only": True,
    }
    return serialize_configuration(build_configuration(enrollment))


class Stage5CliTests(unittest.TestCase):
    def test_exact_command_set(self) -> None:
        self.assertEqual(ALLOWED_COMMANDS, {"version", "config-check", "status", "start", "stop"})

    def test_exact_state_set(self) -> None:
        self.assertEqual(ALLOWED_STATES, {"NOT_STARTED", "OBSERVATION_PLAN_READY", "STOP_PLAN_READY"})

    def test_version_requires_no_configuration(self) -> None:
        result = run_command("version")
        self.assertTrue(result.payload["accepted"])
        self.assertEqual(result.payload["reason_code"], "VERSION_REPORTED")

    def test_unknown_command_rejected(self) -> None:
        result = run_command("restart", config_bytes())
        self.assertFalse(result.payload["accepted"])
        self.assertEqual(result.payload["reason_code"], "UNKNOWN_COMMAND")

    def test_configuration_required(self) -> None:
        result = run_command("status")
        self.assertFalse(result.payload["accepted"])
        self.assertEqual(result.payload["reason_code"], "CONFIGURATION_REQUIRED")

    def test_config_check_accepts_valid_configuration(self) -> None:
        result = run_command("config-check", config_bytes())
        self.assertTrue(result.payload["accepted"])
        self.assertEqual(result.payload["subject_container_id"], CONTAINER_ID)

    def test_tampered_configuration_rejected(self) -> None:
        value = json.loads(config_bytes())
        value["mode"]["gateway_enabled"] = True
        tampered = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        result = run_command("config-check", tampered)
        self.assertFalse(result.payload["accepted"])
        self.assertEqual(result.payload["reason_code"], "CONFIGURATION_REJECTED")

    def test_malformed_configuration_rejected(self) -> None:
        result = run_command("status", b"not-json")
        self.assertFalse(result.payload["accepted"])
        self.assertEqual(result.payload["reason_code"], "CONFIGURATION_REJECTED")

    def test_status_reports_no_runtime_store(self) -> None:
        result = run_command("status", config_bytes())
        self.assertEqual(result.payload["lifecycle_state"], "NOT_STARTED")
        self.assertEqual(result.payload["reason_code"], "NO_RUNTIME_STATE_STORE")

    def test_start_is_plan_only(self) -> None:
        result = run_command("start", config_bytes())
        self.assertEqual(result.payload["lifecycle_state"], "OBSERVATION_PLAN_READY")
        self.assertFalse(result.payload["plan"]["execution_performed"])
        self.assertFalse(result.payload["plan"]["native_action_requested"])

    def test_stop_does_not_mutate_container(self) -> None:
        result = run_command("stop", config_bytes())
        self.assertEqual(result.payload["lifecycle_state"], "STOP_PLAN_READY")
        self.assertFalse(result.payload["plan"]["container_mutation_requested"])
        self.assertTrue(result.payload["plan"]["monitored_container_remains_independently_operable"])

    def test_safety_invariants_on_all_commands(self) -> None:
        for command in sorted(ALLOWED_COMMANDS):
            result = run_command(command, None if command == "version" else config_bytes())
            safety = result.payload["safety"]
            self.assertTrue(safety["observation_only"])
            self.assertFalse(safety["gateway_enabled"])
            self.assertFalse(safety["autonomous_actions"])
            self.assertFalse(safety["native_execution_authorized"])

    def test_canonical_output_is_stable(self) -> None:
        first = run_command("start", config_bytes()).canonical_bytes()
        second = run_command("start", config_bytes()).canonical_bytes()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

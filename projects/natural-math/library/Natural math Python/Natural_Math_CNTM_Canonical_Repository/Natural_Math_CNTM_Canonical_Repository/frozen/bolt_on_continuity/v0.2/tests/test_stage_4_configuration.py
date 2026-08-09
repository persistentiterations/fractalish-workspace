from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on_continuity_v0_2.product_configuration import (  # noqa: E402
    ConfigurationError,
    ConfigurationOptions,
    build_configuration,
    serialize_configuration,
    validate_configuration,
)

CID = "a" * 64


def enrollment() -> dict[str, object]:
    return {
        "schema_version": "1",
        "container_id": CID,
        "display_name": "demo",
        "image": "example:1",
        "observation_only": True,
        "gateway_enabled": False,
    }


class Stage4ConfigurationTests(unittest.TestCase):
    def test_deterministic_configuration_and_bytes(self) -> None:
        first = build_configuration(enrollment())
        second = build_configuration(enrollment())
        self.assertEqual(first, second)
        self.assertEqual(serialize_configuration(first), serialize_configuration(second))

    def test_safe_defaults(self) -> None:
        config = build_configuration(enrollment())
        self.assertEqual(config["mode"], {
            "approval_required": True,
            "autonomous_actions": False,
            "gateway_enabled": False,
            "observation_only": True,
        })
        self.assertFalse(config["authority"]["native_execution_authorized"])

    def test_digest_tampering_rejected(self) -> None:
        config = build_configuration(enrollment())
        config["subject"]["display_name"] = "changed"
        with self.assertRaises(ConfigurationError):
            validate_configuration(config)

    def test_extra_field_rejected(self) -> None:
        config = build_configuration(enrollment())
        config["command"] = "docker pause"
        with self.assertRaises(ConfigurationError):
            validate_configuration(config)

    def test_missing_field_rejected(self) -> None:
        config = build_configuration(enrollment())
        del config["storage"]
        with self.assertRaises(ConfigurationError):
            validate_configuration(config)

    def test_short_or_uppercase_id_rejected(self) -> None:
        for bad in ("a" * 12, "A" * 64):
            item = enrollment()
            item["container_id"] = bad
            with self.assertRaises(ConfigurationError):
                build_configuration(item)

    def test_authority_expansion_rejected(self) -> None:
        config = build_configuration(enrollment())
        config["authority"]["decision_vocabulary"].append("RESTART")
        with self.assertRaises(ConfigurationError):
            validate_configuration(config)

    def test_unsafe_paths_rejected(self) -> None:
        for value in ("../data", "/tmp/data", "C:/data", "\\\\server\\share", "~/data", "$HOME/data", "%TEMP%/data"):
            with self.subTest(value=value):
                with self.assertRaises(ConfigurationError):
                    build_configuration(enrollment(), ConfigurationOptions(data_directory=value))

    def test_invalid_bounds_rejected(self) -> None:
        for value in (0, -1, True, 100001):
            with self.subTest(value=value):
                with self.assertRaises(ConfigurationError):
                    build_configuration(enrollment(), ConfigurationOptions(max_incident_count=value))

    def test_unsafe_enrollment_defaults_rejected(self) -> None:
        item = enrollment()
        item["gateway_enabled"] = True
        with self.assertRaises(ConfigurationError):
            build_configuration(item)

    def test_custom_bounded_options_validate(self) -> None:
        config = build_configuration(
            enrollment(),
            ConfigurationOptions(
                data_directory="local/data",
                retention_mode="retain_until_operator_deletes",
                max_incident_count=10,
                max_receipt_bytes_per_incident=1024,
            ),
        )
        self.assertEqual(validate_configuration(config), config)

    def test_source_has_no_operational_dependency(self) -> None:
        source = (SRC / "bolt_on_continuity_v0_2/product_configuration.py").read_text(encoding="utf-8")
        for token in ("import docker", "import subprocess", "os.system", "Popen(", "docker pause", "docker unpause"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()

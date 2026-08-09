from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src/bolt_on_continuity_v0_2/container_enrollment.py"
SPEC = importlib.util.spec_from_file_location("stage3_enrollment", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

A = "a" * 64
B = "b" * 64


def line(container_id: str, name: str = "svc", state: str = "running") -> str:
    return json.dumps({"ID": container_id, "Names": name, "Image": "example:1", "State": state, "Status": "Up"})


def inspect(container_id: str, name: str = "svc") -> str:
    return json.dumps([{"Id": container_id, "Name": "/" + name, "Platform": "linux", "Config": {"Image": "example:1"}, "State": {"Status": "running"}}])


class FakeRunner:
    def __init__(self, discovery: str = "", inspection: str = "") -> None:
        self.discovery = discovery
        self.inspection = inspection
        self.calls: list[tuple[tuple[str, ...], int]] = []

    def __call__(self, args, timeout):
        args = tuple(args)
        self.calls.append((args, timeout))
        if args == module.DISCOVERY_ARGS:
            return module.CommandResult(0, self.discovery)
        if args == ("inspect", A):
            return module.CommandResult(0, self.inspection)
        return module.CommandResult(9, "", "unexpected")


class Stage3EnrollmentTests(unittest.TestCase):
    def test_discovery_sorted_by_full_id(self):
        candidates = module.parse_discovery_jsonl(line(B, "two") + "\n" + line(A, "one"))
        self.assertEqual([A, B], [item.container_id for item in candidates])

    def test_canonical_discovery_stable(self):
        left = module.parse_discovery_jsonl(line(B) + "\n" + line(A))
        right = module.parse_discovery_jsonl(line(A) + "\n" + line(B))
        self.assertEqual(module.canonical_discovery(left), module.canonical_discovery(right))

    def test_short_id_rejected(self):
        with self.assertRaisesRegex(module.EnrollmentError, "INVALID_DISCOVERY_CONTAINER_ID"):
            module.parse_discovery_jsonl(line("a" * 12))

    def test_duplicate_id_rejected(self):
        with self.assertRaisesRegex(module.EnrollmentError, "DUPLICATE_DISCOVERY_CONTAINER_ID"):
            module.parse_discovery_jsonl(line(A) + "\n" + line(A))

    def test_malformed_discovery_rejected(self):
        with self.assertRaisesRegex(module.EnrollmentError, "MALFORMED_DISCOVERY_JSON"):
            module.parse_discovery_jsonl("not-json")

    def test_name_only_selection_rejected(self):
        candidates = module.parse_discovery_jsonl(line(A, "svc"))
        with self.assertRaisesRegex(module.EnrollmentError, "INVALID_SELECTION_FULL_ID"):
            module.select_candidate(candidates, "svc")

    def test_prefix_selection_rejected(self):
        candidates = module.parse_discovery_jsonl(line(A))
        with self.assertRaisesRegex(module.EnrollmentError, "INVALID_SELECTION_FULL_ID"):
            module.select_candidate(candidates, A[:12])

    def test_confirmation_mismatch_prevents_inspect(self):
        candidates = module.parse_discovery_jsonl(line(A))
        runner = FakeRunner(inspection=inspect(A))
        with self.assertRaisesRegex(module.EnrollmentError, "CONFIRMATION_MISMATCH"):
            module.enroll_container(candidates, A, B, runner)
        self.assertEqual([], runner.calls)

    def test_inspection_id_mismatch_rejected(self):
        candidates = module.parse_discovery_jsonl(line(A))
        runner = FakeRunner(inspection=inspect(B))
        with self.assertRaisesRegex(module.EnrollmentError, "INSPECTION_ID_MISMATCH"):
            module.enroll_container(candidates, A, A, runner)

    def test_same_name_replacement_does_not_inherit(self):
        old = module.parse_discovery_jsonl(line(A, "svc"))
        replacement = module.parse_discovery_jsonl(line(B, "svc"))
        with self.assertRaisesRegex(module.EnrollmentError, "SELECTION_NOT_DISCOVERED"):
            module.select_candidate(replacement, old[0].container_id)

    def test_enrollment_digest_stable_and_safe_defaults(self):
        candidates = module.parse_discovery_jsonl(line(A))
        first = module.enroll_container(candidates, A, A, FakeRunner(inspection=inspect(A)))
        second = module.enroll_container(candidates, A, A, FakeRunner(inspection=inspect(A)))
        self.assertEqual(first, second)
        self.assertTrue(first["observation_only"])
        self.assertFalse(first["gateway_enabled"])
        digest = first["enrollment_digest"]
        self.assertRegex(digest, r"^sha256:[0-9a-f]{64}$")

    def test_only_exact_allowlisted_commands_used(self):
        runner = FakeRunner(discovery=line(A), inspection=inspect(A))
        candidates = module.discover_containers(runner)
        module.enroll_container(candidates, A, A, runner)
        self.assertEqual(module.DISCOVERY_ARGS, runner.calls[0][0])
        self.assertEqual(("inspect", A), runner.calls[1][0])


if __name__ == "__main__":
    unittest.main()

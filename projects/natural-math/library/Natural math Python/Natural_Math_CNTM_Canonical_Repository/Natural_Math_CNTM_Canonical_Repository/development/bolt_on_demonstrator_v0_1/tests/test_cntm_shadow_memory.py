#!/usr/bin/env python3
"""Stage 4 tests for CNTM bounded shadow memory."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
MEMORY_PATH = PROJECT_DIR / "memory" / "cntm_shadow_memory.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


memory = load_module("stage4_test_cntm_shadow_memory", MEMORY_PATH)
governance = memory.governance
ordinary_host = memory.ordinary_host
Job = ordinary_host.Job

EXPECTED_HOST_DIGEST = "04d2438f1dbff0b0ddfe5e5eb6382f6623fbe1d18e92078bde8b8dc95bba1c8e"
EXPECTED_OBSERVER_DIGEST = "7943e8e6422a0b3beef771649327be0ecacbcdc59f63d2c18b1bc0b2c158f42d"
EXPECTED_GOVERNANCE_DIGEST = "71e72e0608272f485c6872ec7efb31f467f9bdc0d603373a95f443722b4a5075"
EXPECTED_MEMORY_DIGEST = "581b40271800046fe28519c290193b3c7209b697ee92ba1c7418a1116c70e2a7"
EXPECTED_CNTM_HASH = "b65f5b88054b3a897d0ce0f577daf803c5f2f296349d7614be547e5d3e72287d"
EXPECTED_RECORDS = 10


class CNTMBoundedShadowMemoryTests(unittest.TestCase):
    def test_baseline_qualification_passes(self) -> None:
        result = memory.qualify_shadow_memory(ordinary_host.baseline_jobs())
        self.assertTrue(result.passed)
        self.assertEqual(result.intervention_attempts, 0)
        self.assertEqual(result.record_count, EXPECTED_RECORDS)
        self.assertEqual(result.session_count, 1)
        self.assertEqual(result.host_digest, EXPECTED_HOST_DIGEST)
        self.assertEqual(result.observer_digest, EXPECTED_OBSERVER_DIGEST)
        self.assertEqual(result.governance_digest, EXPECTED_GOVERNANCE_DIGEST)
        self.assertEqual(result.memory_digest, EXPECTED_MEMORY_DIGEST)
        self.assertEqual(result.cntm_v3_0f_hash, EXPECTED_CNTM_HASH)

    def test_baseline_memory_is_deterministic(self) -> None:
        first = memory.run_shadow_memory(ordinary_host.baseline_jobs())
        second = memory.run_shadow_memory(ordinary_host.baseline_jobs())
        self.assertEqual(first, second)
        self.assertEqual(first.memory_image.final_digest, EXPECTED_MEMORY_DIGEST)

    def test_memory_replay_validates_full_chain(self) -> None:
        report = memory.run_shadow_memory(ordinary_host.baseline_jobs())
        replay = memory.replay_memory(report.memory_image.records)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.final_digest, EXPECTED_MEMORY_DIGEST)
        self.assertEqual(replay.checked_records, EXPECTED_RECORDS)
        self.assertEqual(replay.session_count, 1)

    def test_tampered_memory_record_is_rejected(self) -> None:
        report = memory.run_shadow_memory(ordinary_host.baseline_jobs())
        altered = memory.tamper_memory_record(report.memory_image.records, 2, "TAMPERED")
        replay = memory.replay_memory(altered)
        self.assertFalse(replay.passed)
        self.assertEqual(replay.first_error, "RECORD_HASH_MISMATCH:3")

    def test_missing_memory_record_is_rejected(self) -> None:
        report = memory.run_shadow_memory(ordinary_host.baseline_jobs())
        missing = report.memory_image.records[:2] + report.memory_image.records[3:]
        replay = memory.replay_memory(missing)
        self.assertFalse(replay.passed)
        self.assertTrue(
            replay.first_error.startswith("RECORD_ID_MISMATCH")
            or replay.first_error.startswith("PRIOR_HASH_MISMATCH")
        )

    def test_duplicate_session_is_rejected_atomically(self) -> None:
        governance_report = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        store = memory.BoundedCNTMShadowMemory(64)
        first = store.append_report(governance_report)
        before = store.snapshot()
        duplicate = store.append_report(governance_report)
        after = store.snapshot()
        self.assertTrue(first.accepted)
        self.assertFalse(duplicate.accepted)
        self.assertEqual(duplicate.reason_code, "DUPLICATE_SESSION")
        self.assertEqual(before, after)

    def test_capacity_overflow_is_rejected_atomically(self) -> None:
        governance_report = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        store = memory.BoundedCNTMShadowMemory(9)
        before = store.snapshot()
        result = store.append_report(governance_report)
        after = store.snapshot()
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "MEMORY_CAPACITY_EXCEEDED")
        self.assertEqual(before, after)
        self.assertEqual(len(after.records), 0)

    def test_multiple_distinct_runs_are_preserved(self) -> None:
        store = memory.BoundedCNTMShadowMemory(32)
        first_report = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        second_report = governance.run_shadow_governance(tuple(reversed(ordinary_host.baseline_jobs())))
        first = store.append_report(first_report)
        second = store.append_report(second_report)
        image = store.snapshot()
        replay = memory.replay_memory(image.records)
        self.assertTrue(first.accepted)
        self.assertTrue(second.accepted)
        self.assertEqual(len(image.session_ids), 2)
        self.assertEqual(len(image.records), 20)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.session_count, 2)

    def test_contradictory_evidence_is_preserved(self) -> None:
        base = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        synthetic = memory._synthetic_contradiction_report(base)
        store = memory.BoundedCNTMShadowMemory(8)
        result = store.append_report(synthetic)
        records = tuple(item for item in store.snapshot().records if item.kind == "JOB_EVIDENCE")
        self.assertTrue(result.accepted)
        self.assertEqual(len(records), 1)
        self.assertIn("observed=COMPLETED,REJECTED", records[0].payload)
        self.assertIn("CONTRADICTORY_TERMINAL_EVIDENCE", records[0].payload)

    def test_unknown_is_not_forced(self) -> None:
        base = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        synthetic = memory._synthetic_contradiction_report(base)
        store = memory.BoundedCNTMShadowMemory(8)
        store.append_report(synthetic)
        record = next(item for item in store.snapshot().records if item.kind == "JOB_EVIDENCE")
        self.assertEqual(record.ternary, 0)
        self.assertIn("decision=UNKNOWN", record.payload)

    def test_all_memory_ternary_values_are_exact(self) -> None:
        report = memory.run_shadow_memory(ordinary_host.baseline_jobs())
        self.assertTrue(all(item.ternary in (-1, 0, 1) for item in report.memory_image.records))
        memory.assert_no_float(report)

    def test_host_output_is_unchanged(self) -> None:
        jobs = ordinary_host.baseline_jobs()
        direct = ordinary_host.run_jobs(jobs)
        report = memory.run_shadow_memory(jobs)
        observed = report.governance_report.observation_report.host_run
        self.assertEqual(direct, observed)
        self.assertEqual(direct.run_digest, EXPECTED_HOST_DIGEST)
        self.assertEqual(report.intervention_attempts, 0)

    def test_input_objects_are_not_mutated(self) -> None:
        jobs = ordinary_host.baseline_jobs()
        before = repr(jobs)
        memory.run_shadow_memory(jobs)
        self.assertEqual(repr(jobs), before)

    def test_sources_and_frozen_cntm_remain_unchanged(self) -> None:
        paths = (
            memory.HOST_PATH,
            memory.ADAPTER_PATH,
            memory.GOVERNANCE_PATH,
            memory.CNTM_V3_0F_PATH,
        )
        before = tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in paths)
        memory.run_shadow_memory(ordinary_host.baseline_jobs())
        after = tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in paths)
        self.assertEqual(before, after)
        self.assertEqual(before[3], EXPECTED_CNTM_HASH)

    def test_safe_detachment_returns_original_host_behavior(self) -> None:
        jobs = ordinary_host.baseline_jobs()
        before = ordinary_host.run_jobs(jobs)
        memory.run_shadow_memory(jobs)
        after = ordinary_host.run_jobs(jobs)
        self.assertEqual(before, after)

    def test_memory_source_has_no_frozen_execution_or_write_path(self) -> None:
        source = MEMORY_PATH.read_text(encoding="utf-8").lower()
        forbidden = (
            "subprocess",
            "write_text",
            "write_bytes",
            "unlink(",
            "rename(",
            "chmod(",
            "import cntm",
            "from cntm",
        )
        for term in forbidden:
            self.assertNotIn(term, source)

    def test_invalid_capacity_is_rejected(self) -> None:
        for invalid in (0, -1, True):
            with self.assertRaises(ValueError):
                memory.BoundedCNTMShadowMemory(invalid)

    def test_session_identifier_changes_with_run_evidence(self) -> None:
        first = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        second = governance.run_shadow_governance(tuple(reversed(ordinary_host.baseline_jobs())))
        self.assertNotEqual(memory.session_identifier(first), memory.session_identifier(second))


if __name__ == "__main__":
    unittest.main(verbosity=2)

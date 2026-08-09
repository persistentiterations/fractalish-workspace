#!/usr/bin/env python3
"""Stage 2 qualification tests for the observation-only adapter."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
HOST_PATH = PROJECT_DIR / "host" / "ordinary_host.py"
ADAPTER_PATH = PROJECT_DIR / "adapter" / "bolt_on_adapter.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ordinary_host = load_module("stage2_test_ordinary_host", HOST_PATH)
adapter = load_module("stage2_test_bolt_on_adapter", ADAPTER_PATH)
Job = ordinary_host.Job

EXPECTED_HOST_DIGEST = "04d2438f1dbff0b0ddfe5e5eb6382f6623fbe1d18e92078bde8b8dc95bba1c8e"
EXPECTED_OBSERVER_DIGEST = "7943e8e6422a0b3beef771649327be0ecacbcdc59f63d2c18b1bc0b2c158f42d"
EXPECTED_RECEIPT_COUNT = 24


class ObservationOnlyAdapterTests(unittest.TestCase):
    def test_baseline_host_output_is_exactly_equivalent(self) -> None:
        jobs = ordinary_host.baseline_jobs()
        direct = ordinary_host.run_jobs(jobs)
        report = adapter.observe_jobs(jobs)
        self.assertEqual(direct.canonical_text(), report.host_run.canonical_text())
        self.assertEqual(direct.run_digest, report.host_run.run_digest)
        self.assertEqual(direct.run_digest, EXPECTED_HOST_DIGEST)
        self.assertEqual(report.host_run.run_digest, EXPECTED_HOST_DIGEST)

    def test_equivalence_qualification_passes(self) -> None:
        qualification = adapter.qualify_observation_equivalence(
            ordinary_host.baseline_jobs()
        )
        self.assertTrue(qualification.passed)
        self.assertTrue(qualification.input_unchanged)
        self.assertTrue(qualification.replay_pass)
        self.assertEqual(qualification.direct_digest, EXPECTED_HOST_DIGEST)
        self.assertEqual(qualification.observed_digest, EXPECTED_HOST_DIGEST)

    def test_observer_is_deterministic(self) -> None:
        first = adapter.observe_jobs(ordinary_host.baseline_jobs())
        second = adapter.observe_jobs(ordinary_host.baseline_jobs())
        self.assertEqual(first, second)
        self.assertEqual(first.observer_digest, EXPECTED_OBSERVER_DIGEST)
        self.assertEqual(len(first.receipts), EXPECTED_RECEIPT_COUNT)

    def test_input_objects_are_not_mutated(self) -> None:
        jobs = ordinary_host.baseline_jobs()
        before = repr(jobs)
        adapter.observe_jobs(jobs)
        self.assertEqual(repr(jobs), before)

    def test_observation_replay_validates_full_chain(self) -> None:
        report = adapter.observe_jobs(ordinary_host.baseline_jobs())
        replay = adapter.replay_observation_receipts(report.receipts)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.checked_receipts, len(report.receipts))
        self.assertEqual(replay.final_digest, report.observer_digest)
        self.assertEqual(replay.first_error, "NONE")

    def test_tampered_receipt_is_rejected(self) -> None:
        report = adapter.observe_jobs(ordinary_host.baseline_jobs())
        tampered = adapter.tamper_receipt(
            report.receipts,
            index=4,
            replacement_payload="TAMPERED",
        )
        replay = adapter.replay_observation_receipts(tampered)
        self.assertFalse(replay.passed)
        self.assertEqual(replay.first_error, "RECEIPT_HASH_MISMATCH:5")

    def test_missing_receipt_is_rejected(self) -> None:
        report = adapter.observe_jobs(ordinary_host.baseline_jobs())
        missing = report.receipts[:3] + report.receipts[4:]
        replay = adapter.replay_observation_receipts(missing)
        self.assertFalse(replay.passed)
        self.assertTrue(
            replay.first_error.startswith("RECEIPT_ID_MISMATCH")
            or replay.first_error.startswith("PRIOR_HASH_MISMATCH")
        )

    def test_safe_detachment_returns_same_host_behavior(self) -> None:
        jobs = ordinary_host.baseline_jobs()
        before = ordinary_host.run_jobs(jobs)
        adapter.observe_jobs(jobs)
        after = ordinary_host.run_jobs(jobs)
        self.assertEqual(before, after)
        self.assertEqual(after.run_digest, EXPECTED_HOST_DIGEST)

    def test_host_source_bytes_remain_unchanged(self) -> None:
        before = hashlib.sha256(HOST_PATH.read_bytes()).hexdigest()
        adapter.observe_jobs(ordinary_host.baseline_jobs())
        after = hashlib.sha256(HOST_PATH.read_bytes()).hexdigest()
        self.assertEqual(before, after)

    def test_adapter_has_no_governance_or_memory_dependencies(self) -> None:
        source = ADAPTER_PATH.read_text(encoding="utf-8").lower()
        forbidden = (
            "import natural_math",
            "from natural_math",
            "import cntm",
            "from cntm",
            "subprocess",
            ".write(",
            "open(",
        )
        for term in forbidden:
            self.assertNotIn(term, source)

    def test_nonbaseline_fixture_is_also_equivalent(self) -> None:
        jobs = (
            Job("A", "SET", 7),
            Job("B", "MULTIPLY", 4, ("A",)),
            Job("C", "SUBTRACT", 3, ("B",)),
            Job("D", "ADD", 10, ("MISSING",)),
        )
        direct = ordinary_host.run_jobs(jobs, starting_value=99)
        observed = adapter.observe_jobs(jobs, starting_value=99)
        self.assertEqual(direct.canonical_text(), observed.host_run.canonical_text())
        self.assertEqual(direct.run_digest, observed.host_run.run_digest)
        self.assertEqual(direct.final_value, 25)
        self.assertEqual(direct.delayed_ids, ("D",))

    def test_snapshot_is_an_independent_value_record(self) -> None:
        jobs = ordinary_host.baseline_jobs()
        report = adapter.observe_jobs(jobs)
        self.assertEqual(len(report.input_snapshot), len(jobs))
        self.assertNotEqual(id(report.input_snapshot[0]), id(jobs[0]))
        self.assertEqual(report.input_snapshot[0].job_id, jobs[0].job_id)
        self.assertEqual(report.input_snapshot[0].operation, jobs[0].operation)


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Baseline qualification tests for the ordinary deterministic host."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
HOST_PATH = PROJECT_DIR / "host" / "ordinary_host.py"

spec = importlib.util.spec_from_file_location("ordinary_host", HOST_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not load host module from {HOST_PATH}")
ordinary_host = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ordinary_host
spec.loader.exec_module(ordinary_host)

Job = ordinary_host.Job
EXPECTED_BASELINE_DIGEST = "04d2438f1dbff0b0ddfe5e5eb6382f6623fbe1d18e92078bde8b8dc95bba1c8e"


class OrdinaryHostBaselineTests(unittest.TestCase):
    def test_baseline_contract(self) -> None:
        run = ordinary_host.run_jobs(
            ordinary_host.baseline_jobs(),
            starting_value=0,
        )
        self.assertEqual(run.final_value, 43)
        self.assertEqual(
            run.completed_ids,
            ("J001", "J002", "J003", "J004", "J007"),
        )
        self.assertEqual(run.rejected_ids, ("J006", "<EMPTY>"))
        self.assertEqual(run.delayed_ids, ("J005",))
        self.assertEqual(run.run_digest, EXPECTED_BASELINE_DIGEST)

    def test_repeat_is_exact(self) -> None:
        first = ordinary_host.run_jobs(ordinary_host.baseline_jobs())
        second = ordinary_host.run_jobs(ordinary_host.baseline_jobs())
        self.assertEqual(first, second)
        self.assertEqual(first.canonical_text(), second.canonical_text())

    def test_input_jobs_are_not_mutated(self) -> None:
        jobs = ordinary_host.baseline_jobs()
        before = repr(jobs)
        ordinary_host.run_jobs(jobs)
        self.assertEqual(repr(jobs), before)

    def test_unmet_dependency_is_delayed_without_blocking_valid_work(self) -> None:
        jobs = (
            Job("A", "ADD", 2, ("MISSING",)),
            Job("B", "SET", 8),
            Job("C", "ADD", 4, ("B",)),
        )
        run = ordinary_host.run_jobs(jobs)
        self.assertEqual(run.final_value, 12)
        self.assertEqual(run.completed_ids, ("B", "C"))
        self.assertEqual(run.delayed_ids, ("A",))

    def test_duplicate_ids_are_rejected_deterministically(self) -> None:
        jobs = (
            Job("DUP", "SET", 1),
            Job("DUP", "ADD", 2),
            Job("OK", "SET", 9),
        )
        run = ordinary_host.run_jobs(jobs)
        self.assertEqual(run.final_value, 9)
        self.assertEqual(run.completed_ids, ("OK",))
        self.assertEqual(run.rejected_ids, ("DUP", "DUP"))

    def test_invalid_values_and_operations_are_rejected(self) -> None:
        jobs = (
            Job("BOOL", "SET", True),
            Job("TEXT", "ADD", "5"),  # type: ignore[arg-type]
            Job("BADOP", "POWER", 3),
            Job("GOOD", "SET", 6),
        )
        run = ordinary_host.run_jobs(jobs)
        self.assertEqual(run.final_value, 6)
        self.assertEqual(
            run.rejected_ids,
            ("BOOL", "TEXT", "BADOP"),
        )

    def test_host_has_no_bolt_on_dependencies(self) -> None:
        source = HOST_PATH.read_text(encoding="utf-8").lower()
        forbidden_imports = (
            "import natural_math",
            "from natural_math",
            "import cntm",
            "from cntm",
        )
        for forbidden in forbidden_imports:
            self.assertNotIn(forbidden, source)

    def test_source_hash_is_reported_for_reference(self) -> None:
        source_hash = hashlib.sha256(HOST_PATH.read_bytes()).hexdigest()
        self.assertEqual(len(source_hash), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)

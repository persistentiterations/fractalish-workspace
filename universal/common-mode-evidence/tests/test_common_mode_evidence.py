#!/usr/bin/env python3
"""Standard-library acceptance tests for the constructed-fixture trial."""

from pathlib import Path
import importlib.util
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "common_mode_evidence.py"
SPEC = importlib.util.spec_from_file_location("common_mode_evidence", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class CommonModeEvidenceTests(unittest.TestCase):
    def test_causal_policy_acceptance(self):
        summaries, rows = MODULE.execute()
        MODULE.assert_causal_acceptance(summaries, rows)

    def test_same_root_opposition_is_not_overwritten(self):
        case = next(x for x in MODULE.CASES if x.case_id == "same_root_opposed_values")
        self.assertEqual(
            MODULE.decide(case, "CAUSAL_DEPENDENCY_ROOT"),
            ("HOLD", 1, 0, 0, 1),
        )

    def test_opposed_roots_report_total_support_and_opposition(self):
        case = next(x for x in MODULE.CASES if x.case_id == "contradicted_root_plus_opposed_valid_roots")
        self.assertEqual(
            MODULE.decide(case, "CAUSAL_DEPENDENCY_ROOT"),
            ("HOLD", 2, 1, 1, 0),
        )

    def test_cycle_is_unresolved(self):
        case = next(x for x in MODULE.CASES if x.case_id == "dependency_cycle")
        self.assertEqual(MODULE.decide(case, "CAUSAL_DEPENDENCY_ROOT")[0], "UNRESOLVED")

    def test_replay_is_identical(self):
        self.assertEqual(MODULE.execute(), MODULE.execute())


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Stage 3 tests for the Natural Math shadow-governance interface."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
GOVERNANCE_PATH = PROJECT_DIR / "governance" / "natural_math_shadow_governance.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


governance = load_module("stage3_test_shadow_governance", GOVERNANCE_PATH)
ordinary_host = governance.ordinary_host
adapter = governance.adapter
Job = ordinary_host.Job

EXPECTED_HOST_DIGEST = "04d2438f1dbff0b0ddfe5e5eb6382f6623fbe1d18e92078bde8b8dc95bba1c8e"
EXPECTED_OBSERVER_DIGEST = "7943e8e6422a0b3beef771649327be0ecacbcdc59f63d2c18b1bc0b2c158f42d"
EXPECTED_GOVERNANCE_DIGEST = "71e72e0608272f485c6872ec7efb31f467f9bdc0d603373a95f443722b4a5075"
EXPECTED_RC21_HASH = "97c75d0035b2844287e902a0df9bbbb804d37691be02512e0ab98c119106b863"
EXPECTED_RECEIPTS = 18


class NaturalMathShadowGovernanceTests(unittest.TestCase):
    def test_baseline_shadow_qualification_passes(self) -> None:
        result = governance.qualify_shadow_governance(ordinary_host.baseline_jobs())
        self.assertTrue(result.passed)
        self.assertTrue(result.all_outcomes_match)
        self.assertEqual(result.intervention_attempts, 0)
        self.assertEqual(result.host_digest, EXPECTED_HOST_DIGEST)
        self.assertEqual(result.observer_digest, EXPECTED_OBSERVER_DIGEST)
        self.assertEqual(result.governance_digest, EXPECTED_GOVERNANCE_DIGEST)
        self.assertEqual(result.natural_math_rc21_hash, EXPECTED_RC21_HASH)
        self.assertEqual(result.receipt_count, EXPECTED_RECEIPTS)

    def test_baseline_decision_distribution(self) -> None:
        report = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        decisions = tuple(item.decision for item in report.decisions)
        self.assertEqual(decisions.count(governance.PROCEED), 5)
        self.assertEqual(decisions.count(governance.DEFER), 1)
        self.assertEqual(decisions.count(governance.RESTRICT), 2)
        self.assertEqual(decisions.count(governance.UNKNOWN), 0)

    def test_baseline_recommendations_match_terminal_outcomes(self) -> None:
        report = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        self.assertTrue(all(audit.status == "MATCH" for audit in report.audits))
        mapping = {item.job_id: item.decision for item in report.decisions}
        self.assertEqual(mapping["J005"], governance.DEFER)
        self.assertEqual(mapping["J006"], governance.RESTRICT)
        self.assertEqual(mapping["J007"], governance.PROCEED)

    def test_shadow_mode_preserves_host_output(self) -> None:
        jobs = ordinary_host.baseline_jobs()
        direct = ordinary_host.run_jobs(jobs)
        report = governance.run_shadow_governance(jobs)
        self.assertEqual(direct, report.observation_report.host_run)
        self.assertEqual(direct.run_digest, EXPECTED_HOST_DIGEST)
        self.assertEqual(report.intervention_attempts, 0)

    def test_governance_is_deterministic(self) -> None:
        first = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        second = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        self.assertEqual(first, second)
        self.assertEqual(first.governance_digest, EXPECTED_GOVERNANCE_DIGEST)

    def test_governance_receipts_replay(self) -> None:
        report = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        replay = governance.replay_governance_receipts(report.receipts)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.final_digest, report.governance_digest)
        self.assertEqual(replay.checked_receipts, len(report.receipts))

    def test_tampered_governance_receipt_is_rejected(self) -> None:
        report = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        tampered = governance.tamper_governance_receipt(
            report.receipts, 3, "TAMPERED"
        )
        replay = governance.replay_governance_receipts(tampered)
        self.assertFalse(replay.passed)
        self.assertEqual(replay.first_error, "RECEIPT_HASH_MISMATCH:4")

    def test_missing_governance_receipt_is_rejected(self) -> None:
        report = governance.run_shadow_governance(ordinary_host.baseline_jobs())
        missing = report.receipts[:2] + report.receipts[3:]
        replay = governance.replay_governance_receipts(missing)
        self.assertFalse(replay.passed)
        self.assertTrue(
            replay.first_error.startswith("RECEIPT_ID_MISMATCH")
            or replay.first_error.startswith("PRIOR_HASH_MISMATCH")
        )

    def test_input_objects_are_not_mutated(self) -> None:
        jobs = ordinary_host.baseline_jobs()
        before = repr(jobs)
        governance.run_shadow_governance(jobs)
        self.assertEqual(repr(jobs), before)

    def test_sources_and_frozen_rc21_remain_unchanged(self) -> None:
        paths = (governance.HOST_PATH, governance.ADAPTER_PATH, governance.RC21_PATH)
        before = tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in paths)
        governance.run_shadow_governance(ordinary_host.baseline_jobs())
        after = tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in paths)
        self.assertEqual(before, after)
        self.assertEqual(before[2], EXPECTED_RC21_HASH)

    def test_dependency_cycle_is_deferred(self) -> None:
        jobs = (
            Job("A", "SET", 1, ("B",)),
            Job("B", "ADD", 2, ("A",)),
        )
        report = governance.run_shadow_governance(jobs)
        self.assertEqual(
            tuple(item.decision for item in report.decisions),
            (governance.DEFER, governance.DEFER),
        )
        self.assertEqual(report.observation_report.host_run.delayed_ids, ("A", "B"))
        self.assertTrue(all(audit.status == "MATCH" for audit in report.audits))

    def test_dependency_on_restricted_job_is_deferred(self) -> None:
        jobs = (
            Job("BAD", "DIVIDE", 2),
            Job("WAIT", "ADD", 1, ("BAD",)),
        )
        report = governance.run_shadow_governance(jobs)
        self.assertEqual(report.decisions[0].decision, governance.RESTRICT)
        self.assertEqual(report.decisions[1].decision, governance.DEFER)
        self.assertEqual(report.decisions[1].reason_code, "DEPENDENCY_NOT_ADMISSIBLE")
        self.assertTrue(all(audit.status == "MATCH" for audit in report.audits))

    def test_duplicate_jobs_are_restricted_and_dependents_deferred(self) -> None:
        jobs = (
            Job("DUP", "SET", 1),
            Job("DUP", "ADD", 2),
            Job("WAIT", "ADD", 3, ("DUP",)),
        )
        report = governance.run_shadow_governance(jobs)
        self.assertEqual(
            tuple(item.decision for item in report.decisions),
            (governance.RESTRICT, governance.RESTRICT, governance.DEFER),
        )
        self.assertTrue(all(audit.status == "MATCH" for audit in report.audits))

    def test_incomplete_evidence_returns_unknown(self) -> None:
        item = adapter.ObservedJob(
            ordinal=1,
            job_id="<UNREADABLE>",
            operation="<UNREADABLE>",
            value_text="<UNREADABLE>",
            value_type="unknown",
            requires=(),
        )
        decision = governance.classify_snapshot((item,))[0]
        self.assertEqual(decision.decision, governance.UNKNOWN)
        self.assertEqual(decision.ternary, 0)
        self.assertEqual(decision.reason_code, "INSUFFICIENT_EVIDENCE")

    def test_contradictory_terminal_evidence_returns_unknown(self) -> None:
        decision = governance.GovernanceDecision(
            1,
            "A",
            governance.PROCEED,
            1,
            "LOCAL_EVIDENCE_ADMISSIBLE",
            "COMPLETED",
            (),
        )
        audit = governance.audit_one_decision(
            decision, ("COMPLETED", "REJECTED")
        )
        self.assertEqual(audit.status, governance.UNKNOWN)
        self.assertEqual(audit.reason_code, "CONTRADICTORY_TERMINAL_EVIDENCE")

    def test_reordered_fixture_remains_deterministic_and_nonintervening(self) -> None:
        jobs = tuple(reversed(ordinary_host.baseline_jobs()))
        first = governance.run_shadow_governance(jobs)
        second = governance.run_shadow_governance(jobs)
        direct = ordinary_host.run_jobs(jobs)
        self.assertEqual(first, second)
        self.assertEqual(first.observation_report.host_run, direct)
        self.assertEqual(first.intervention_attempts, 0)

    def test_governance_source_has_no_write_or_execution_path_to_frozen_code(self) -> None:
        source = GOVERNANCE_PATH.read_text(encoding="utf-8").lower()
        forbidden = (
            "subprocess",
            "write_text",
            "write_bytes",
            "unlink(",
            "rename(",
            "chmod(",
            "import natural_math",
            "from natural_math",
        )
        for term in forbidden:
            self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)

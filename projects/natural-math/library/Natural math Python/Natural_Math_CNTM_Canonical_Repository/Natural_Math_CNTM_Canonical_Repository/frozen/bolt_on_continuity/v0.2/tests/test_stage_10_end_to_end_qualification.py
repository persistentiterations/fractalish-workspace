from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on_continuity_v0_2.end_to_end_qualification import (
    NOT_READY,
    READY,
    REQUIRED_STAGES,
    qualify_release_candidate,
    serialize_qualification_report,
    validate_qualification_report,
)


def evidence_set() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for index, stage in enumerate(REQUIRED_STAGES, start=1):
        result[stage] = {
            "stage": stage,
            "status": "PASS",
            "evidence_digest": hashlib.sha256(f"{index}:{stage}".encode()).hexdigest(),
            "frozen_regression_passed": True,
            "authority_expanded": False,
        }
    return result


class Stage10QualificationTests(unittest.TestCase):
    def test_complete_qualification_is_ready(self) -> None:
        report = qualify_release_candidate(evidence_set())
        self.assertEqual(report["outcome"], READY)
        self.assertEqual(len(report["stage_evidence"]), 9)

    def test_input_order_does_not_change_report(self) -> None:
        evidence = evidence_set()
        reversed_evidence = dict(reversed(list(evidence.items())))
        self.assertEqual(
            serialize_qualification_report(qualify_release_candidate(evidence)),
            serialize_qualification_report(qualify_release_candidate(reversed_evidence)),
        )

    def test_missing_evidence_fails_closed(self) -> None:
        evidence = evidence_set()
        evidence.pop(REQUIRED_STAGES[-1])
        self.assertEqual(qualify_release_candidate(evidence)["outcome"], NOT_READY)

    def test_failed_evidence_fails_closed(self) -> None:
        evidence = evidence_set()
        evidence[REQUIRED_STAGES[3]]["status"] = "FAIL"
        self.assertEqual(qualify_release_candidate(evidence)["outcome"], NOT_READY)

    def test_authority_expansion_fails_closed(self) -> None:
        evidence = evidence_set()
        evidence[REQUIRED_STAGES[6]]["authority_expanded"] = True
        self.assertEqual(qualify_release_candidate(evidence)["outcome"], NOT_READY)

    def test_invalid_digest_fails_closed(self) -> None:
        evidence = evidence_set()
        evidence[REQUIRED_STAGES[2]]["evidence_digest"] = "not-a-digest"
        self.assertEqual(qualify_release_candidate(evidence)["outcome"], NOT_READY)

    def test_stage_identity_mismatch_fails_closed(self) -> None:
        evidence = evidence_set()
        evidence[REQUIRED_STAGES[1]]["stage"] = REQUIRED_STAGES[0]
        self.assertEqual(qualify_release_candidate(evidence)["outcome"], NOT_READY)

    def test_duplicate_digest_fails_closed(self) -> None:
        evidence = evidence_set()
        evidence[REQUIRED_STAGES[1]]["evidence_digest"] = evidence[REQUIRED_STAGES[0]]["evidence_digest"]
        self.assertEqual(qualify_release_candidate(evidence)["outcome"], NOT_READY)

    def test_safe_authority_state(self) -> None:
        authority = qualify_release_candidate(evidence_set())["authority"]
        self.assertTrue(authority["observation_only"])
        for key, value in authority.items():
            if key != "observation_only":
                self.assertFalse(value)

    def test_claim_boundary_is_explicit(self) -> None:
        report = qualify_release_candidate(evidence_set())
        excluded = set(report["excluded_capabilities"])
        self.assertIn("gateway execution", excluded)
        self.assertIn("Docker mutation", excluded)
        self.assertIn("production-readiness claims", excluded)

    def test_serialization_is_stable(self) -> None:
        report = qualify_release_candidate(evidence_set())
        self.assertEqual(serialize_qualification_report(report), serialize_qualification_report(report))

    def test_tamper_detection(self) -> None:
        report = qualify_release_candidate(evidence_set())
        tampered = copy.deepcopy(report)
        tampered["outcome"] = NOT_READY
        with self.assertRaises(ValueError):
            validate_qualification_report(tampered)

    def test_extra_evidence_fails_closed(self) -> None:
        evidence = evidence_set()
        evidence["stage_10_unapproved"] = dict(evidence[REQUIRED_STAGES[0]])
        self.assertEqual(qualify_release_candidate(evidence)["outcome"], NOT_READY)

    def test_frozen_regression_required(self) -> None:
        evidence = evidence_set()
        evidence[REQUIRED_STAGES[8]]["frozen_regression_passed"] = False
        self.assertEqual(qualify_release_candidate(evidence)["outcome"], NOT_READY)


if __name__ == "__main__":
    unittest.main()

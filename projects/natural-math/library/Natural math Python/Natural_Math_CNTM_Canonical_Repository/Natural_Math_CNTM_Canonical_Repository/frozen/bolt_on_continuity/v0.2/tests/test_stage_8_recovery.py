from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from bolt_on_continuity_v0_2.recovery_classifier import (  # noqa: E402
    RecoveryError,
    classify_recovery,
    serialize_recovery_report,
)

CID = "a" * 64
CID2 = "b" * 64
DIGEST = "sha256:" + "1" * 64


def subject(cid: str = CID, name: str = "app", state: str = "running") -> dict[str, str]:
    return {"container_id": cid, "display_name": name, "state": state}


class Stage8RecoveryTests(unittest.TestCase):
    def classify(self, **overrides):
        kwargs = {
            "enrolled_container_id": CID,
            "enrolled_display_name": "app",
            "current_subjects": [subject()],
            "store_state": "STORE_HEALTHY",
        }
        kwargs.update(overrides)
        return classify_recovery(**kwargs)

    def test_healthy_restart_resumes_observation_only(self):
        report = self.classify()
        self.assertEqual(report["disposition"], "RESUME_OBSERVATION_ONLY")

    def test_terminal_request_is_suppressed(self):
        report = self.classify(
            request_id="req-1",
            request_digest=DIGEST,
            prior_records=[{"request_id": "req-1", "request_digest": DIGEST, "terminal_result": "DOCKER_ACCEPTED"}],
        )
        self.assertEqual(report["disposition"], "SUPPRESS_DUPLICATE")

    def test_conflicting_request_id_fails_closed(self):
        report = self.classify(
            request_id="req-1",
            request_digest=DIGEST,
            prior_records=[{"request_id": "req-1", "request_digest": "sha256:" + "2" * 64, "terminal_result": "DOCKER_ACCEPTED"}],
        )
        self.assertEqual(report["disposition"], "FAIL_CLOSED_UNCERTAIN")

    def test_unresolved_terminal_result_fails_closed(self):
        report = self.classify(
            request_id="req-1",
            request_digest=DIGEST,
            prior_records=[{"request_id": "req-1", "request_digest": DIGEST, "terminal_result": "PENDING"}],
        )
        self.assertEqual(report["disposition"], "FAIL_CLOSED_UNCERTAIN")

    def test_same_name_replacement_requires_reenrollment(self):
        report = self.classify(current_subjects=[subject(CID2)])
        self.assertEqual(report["subject_status"], "SUBJECT_REPLACED")
        self.assertEqual(report["disposition"], "REQUIRE_REENROLLMENT")

    def test_missing_subject_is_reported(self):
        report = self.classify(current_subjects=[])
        self.assertEqual(report["disposition"], "REPORT_SUBJECT_UNAVAILABLE")

    def test_stopped_subject_is_reported(self):
        report = self.classify(current_subjects=[subject(state="exited")])
        self.assertEqual(report["subject_status"], "SUBJECT_STOPPED")

    def test_duplicate_subject_evidence_is_ambiguous(self):
        report = self.classify(current_subjects=[subject(), subject()])
        self.assertEqual(report["disposition"], "FAIL_CLOSED_UNCERTAIN")

    def test_all_store_failures_fail_closed(self):
        for state in {
            "STORE_MISSING", "STORE_PERMISSION_DENIED", "STORE_PARTIAL_WRITE",
            "STORE_CORRUPT", "STORE_DISK_FULL", "STORE_AMBIGUOUS",
        }:
            with self.subTest(state=state):
                self.assertEqual(self.classify(store_state=state)["disposition"], "FAIL_CLOSED_STORE")

    def test_safe_flags_are_fixed(self):
        report = self.classify()
        self.assertTrue(report["observation_only"])
        self.assertFalse(report["gateway_enabled"])
        self.assertFalse(report["native_execution_authorized"])

    def test_canonical_serialization_is_stable(self):
        first = self.classify()
        second = self.classify()
        self.assertEqual(serialize_recovery_report(first), serialize_recovery_report(second))

    def test_report_tampering_is_rejected(self):
        report = self.classify()
        altered = copy.deepcopy(report)
        altered["reason"] = "tampered"
        with self.assertRaises(RecoveryError):
            serialize_recovery_report(altered)

    def test_short_container_id_rejected(self):
        with self.assertRaises(RecoveryError):
            self.classify(enrolled_container_id="abc")

    def test_incomplete_request_identity_rejected(self):
        with self.assertRaises(RecoveryError):
            self.classify(request_id="req-1")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Stage 5 full-stack adversarial qualification tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
HARNESS_PATH = PROJECT_DIR / "qualification" / "integrated_adversarial_qualification.py"

spec = importlib.util.spec_from_file_location("stage5_integrated_harness", HARNESS_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not load Stage 5 harness from {HARNESS_PATH}")
harness = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = harness
spec.loader.exec_module(harness)

EXPECTED_CAMPAIGN_DIGEST = "9ff12f5a0776c93c11fe4d020bcaf8b756caff82c5f3a1076c23c6ed152f6eab"
EXPECTED_SHARED_MEMORY_DIGEST = "6ba2c70e929777e37feeb6798aba39fc5f2e95b574e8872867f5e53017d66a73"


class IntegratedAdversarialQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.clean = harness.execute_clean_campaign()
        cls.qualification = harness.qualify_integrated_stack()

    def test_stage5_qualification_passes(self) -> None:
        self.assertTrue(self.qualification.passed)

    def test_expected_campaigns_are_present(self) -> None:
        self.assertEqual(
            tuple(item.name for item in self.clean.cases),
            (
                "NORMAL",
                "REORDERED",
                "DUPLICATE",
                "MISSING_DEPENDENCY",
                "DEPENDENCY_CYCLE",
                "MIXED_INVALID",
            ),
        )

    def test_every_campaign_preserves_host_behavior(self) -> None:
        self.assertTrue(all(item.host_equivalent for item in self.clean.cases))

    def test_every_layer_replays_in_every_campaign(self) -> None:
        self.assertTrue(
            all(
                item.observation_replay_pass
                and item.governance_replay_pass
                and item.memory_replay_pass
                for item in self.clean.cases
            )
        )

    def test_unauthorized_interventions_remain_zero(self) -> None:
        self.assertEqual(self.qualification.unauthorized_interventions, 0)

    def test_multi_run_memory_contains_seven_distinct_sessions(self) -> None:
        image = self.clean.shared_memory_image
        self.assertEqual(len(image.session_ids), 7)
        self.assertEqual(len(set(image.session_ids)), 7)

    def test_shared_memory_replays_to_exact_digest(self) -> None:
        replay = self.clean.shared_memory_replay
        self.assertTrue(replay.passed)
        self.assertEqual(replay.final_digest, self.clean.shared_memory_image.final_digest)
        self.assertEqual(replay.session_count, 7)

    def test_duplicate_session_rejection_is_atomic(self) -> None:
        self.assertTrue(self.clean.duplicate_rejected_atomically)

    def test_capacity_exhaustion_rejection_is_atomic(self) -> None:
        self.assertTrue(self.clean.capacity_rejected_atomically)

    def test_contradictory_evidence_is_preserved(self) -> None:
        self.assertTrue(self.clean.contradiction_preserved)

    def test_unknown_is_not_forced(self) -> None:
        self.assertTrue(self.clean.unknown_not_forced)

    def test_observation_tamper_is_detected(self) -> None:
        row = next(item for item in self.clean.faults if item.name == "OBSERVATION_TAMPER")
        self.assertTrue(row.detected)
        self.assertTrue(row.clean_evidence_preserved)

    def test_missing_observation_receipt_is_detected(self) -> None:
        row = next(item for item in self.clean.faults if item.name == "OBSERVATION_MISSING_RECEIPT")
        self.assertTrue(row.detected)
        self.assertTrue(row.clean_evidence_preserved)

    def test_governance_tamper_is_detected(self) -> None:
        row = next(item for item in self.clean.faults if item.name == "GOVERNANCE_TAMPER")
        self.assertTrue(row.detected)
        self.assertTrue(row.clean_evidence_preserved)

    def test_missing_governance_receipt_is_detected(self) -> None:
        row = next(item for item in self.clean.faults if item.name == "GOVERNANCE_MISSING_RECEIPT")
        self.assertTrue(row.detected)
        self.assertTrue(row.clean_evidence_preserved)

    def test_memory_tamper_is_detected(self) -> None:
        row = next(item for item in self.clean.faults if item.name == "MEMORY_TAMPER")
        self.assertTrue(row.detected)
        self.assertTrue(row.clean_evidence_preserved)

    def test_missing_memory_record_is_detected(self) -> None:
        row = next(item for item in self.clean.faults if item.name == "MEMORY_MISSING_RECORD")
        self.assertTrue(row.detected)
        self.assertTrue(row.clean_evidence_preserved)

    def test_repeated_attachment_and_detachment_is_safe(self) -> None:
        self.assertTrue(self.clean.attach_detach_pass)
        self.assertEqual(self.clean.attach_detach_cycles, 5)

    def test_source_and_frozen_hashes_are_unchanged(self) -> None:
        self.assertEqual(self.clean.source_manifest_before, self.clean.source_manifest_after)
        self.assertTrue(self.qualification.source_integrity_pass)
        self.assertEqual(self.clean.frozen_file_count, 11)

    def test_full_campaign_is_deterministic(self) -> None:
        second = harness.execute_clean_campaign()
        self.assertEqual(self.clean.campaign_digest, second.campaign_digest)
        self.assertEqual(self.clean.cases, second.cases)
        self.assertEqual(self.clean.shared_memory_image, second.shared_memory_image)

    def test_fixed_release_digests_match(self) -> None:
        self.assertEqual(self.clean.campaign_digest, EXPECTED_CAMPAIGN_DIGEST)
        self.assertEqual(self.clean.shared_memory_image.final_digest, EXPECTED_SHARED_MEMORY_DIGEST)


if __name__ == "__main__":
    unittest.main(verbosity=2)

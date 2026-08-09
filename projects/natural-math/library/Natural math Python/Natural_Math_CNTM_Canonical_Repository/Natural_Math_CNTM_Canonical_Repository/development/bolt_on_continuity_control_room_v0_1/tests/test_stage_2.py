from __future__ import annotations
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from control_room.comparison import compare_identity, generate_comparison_receipt
from control_room.observation import build_record
from control_room.observer import FixtureObserver
from control_room.receipt import generate_receipt
from control_room.retention import FROZEN_ROOT, RETAINED_SCHEMA, RetainedObservations, RetentionError, capture_and_retain, load_retained, retain_verified
from control_room.webapp import render_continuity

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "docker_inspect_one.json"

class StageTwoTests(unittest.TestCase):
    def setUp(self) -> None:
        raw = FixtureObserver(FIXTURE).inspect_one("bolt-on-demo")
        first = build_record("bolt-on-demo", raw, "Docker CLI inspect (read-only)", "docker inspect --type container bolt-on-demo", "2026-08-02T12:01:00Z")
        second = build_record("bolt-on-demo", raw, "Docker CLI inspect (read-only)", "docker inspect --type container bolt-on-demo", "2026-08-02T12:02:00Z")
        self.document = retain_verified([(first, generate_receipt(first)), (second, generate_receipt(second))])

    def test_explicit_capture_retains_contiguous_contract_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.json"
            document = capture_and_retain(FixtureObserver(FIXTURE), "bolt-on-demo", path, 2)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(document.schema, RETAINED_SCHEMA)
        self.assertEqual([item.observation_index for item in document.observations], [1, 2])
        self.assertEqual(set(payload), {"schema", "subject_selector", "observations"})
        self.assertEqual(set(payload["observations"][0]), {"observation_index", "observation_schema", "observation_receipt_id", "container_id", "observed_at", "source_interface"})

    def test_local_retention_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.json"
            capture_and_retain(FixtureObserver(FIXTURE), "bolt-on-demo", path, 2)
            loaded = load_retained(path)
        self.assertEqual(loaded.schema, RETAINED_SCHEMA)
        self.assertEqual(len(loaded.observations), 2)

    def test_retention_refuses_a_frozen_destination(self) -> None:
        with self.assertRaises(RetentionError):
            capture_and_retain(FixtureObserver(FIXTURE), "bolt-on-demo", FROZEN_ROOT / "must-not-write.json", 2)

    def test_same_full_identity_classifies_same_subject(self) -> None:
        result = compare_identity(self.document)
        self.assertEqual((result.classification, result.reason), ("SAME_SUBJECT", None))

    def test_source_reordering_is_canonicalized_by_index(self) -> None:
        reversed_document = RetainedObservations(RETAINED_SCHEMA, self.document.subject_selector, tuple(reversed(self.document.observations)))
        original = generate_comparison_receipt(self.document)
        replay = generate_comparison_receipt(reversed_document)
        self.assertEqual(original.receipt_id, replay.receipt_id)

    def test_duplicate_or_missing_indices_fail_closed(self) -> None:
        duplicate = RetainedObservations(RETAINED_SCHEMA, self.document.subject_selector, (self.document.observations[0], replace(self.document.observations[1], observation_index=1)))
        missing = RetainedObservations(RETAINED_SCHEMA, self.document.subject_selector, (self.document.observations[0], replace(self.document.observations[1], observation_index=3)))
        for document in (duplicate, missing):
            with self.subTest(indices=[item.observation_index for item in document.observations]):
                result = compare_identity(document)
                self.assertEqual((result.classification, result.reason), ("INDETERMINATE", "invalid_order"))

    def test_insufficient_missing_and_malformed_identity_fail_closed(self) -> None:
        insufficient = RetainedObservations(RETAINED_SCHEMA, self.document.subject_selector, self.document.observations[:1])
        missing = RetainedObservations(RETAINED_SCHEMA, self.document.subject_selector, (replace(self.document.observations[0], container_id=None), self.document.observations[1]))
        malformed = RetainedObservations(RETAINED_SCHEMA, self.document.subject_selector, (replace(self.document.observations[0], container_id="short"), self.document.observations[1]))
        self.assertEqual(compare_identity(insufficient).reason, "insufficient_observations")
        self.assertEqual(compare_identity(missing).reason, "missing_identity")
        self.assertEqual(compare_identity(malformed).reason, "missing_identity")

    def test_conflicting_identity_is_not_a_replacement_claim(self) -> None:
        conflict = RetainedObservations(RETAINED_SCHEMA, self.document.subject_selector, (self.document.observations[0], replace(self.document.observations[1], container_id="b" * 64)))
        result = compare_identity(conflict)
        self.assertEqual((result.classification, result.reason), ("INDETERMINATE", "identity_mismatch_out_of_scope"))

    def test_unverified_receipt_fails_closed(self) -> None:
        bad = RetainedObservations(RETAINED_SCHEMA, self.document.subject_selector, (replace(self.document.observations[0], observation_receipt_id="sha256:not-a-receipt"), self.document.observations[1]))
        self.assertEqual(compare_identity(bad).reason, "unverified_observation_receipt")

    def test_comparison_receipt_changes_for_identity_or_reason(self) -> None:
        baseline = generate_comparison_receipt(self.document)
        conflict = RetainedObservations(RETAINED_SCHEMA, self.document.subject_selector, (self.document.observations[0], replace(self.document.observations[1], container_id="b" * 64)))
        self.assertNotEqual(baseline.receipt_id, generate_comparison_receipt(conflict).receipt_id)

    def test_page_labels_retention_derivation_and_classification(self) -> None:
        result = compare_identity(self.document)
        page = render_continuity(self.document, result)
        for marker in ("operator-entered", "observed", "retained", "derived", "classification", "SAME_SUBJECT", "sha256:"):
            self.assertIn(marker, page)

if __name__ == "__main__": unittest.main()

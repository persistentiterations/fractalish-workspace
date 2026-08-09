from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import sys

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "portability"
    / "portable_adapter_contract.py"
)
SPEC = importlib.util.spec_from_file_location("portable_adapter_contract", MODULE_PATH)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


def make_frozen_fixture(root: Path) -> tuple[Path, str]:
    release = root / "frozen" / "bolt_on" / "v0.2"
    (release / "authority").mkdir(parents=True)
    (release / "README.md").write_text("frozen\n", encoding="utf-8", newline="\n")
    (release / "authority" / "contract.py").write_text(
        "HOLD='HOLD'\nRELEASE='RELEASE'\n", encoding="utf-8", newline="\n"
    )
    files = [release / "README.md", release / "authority" / "contract.py"]
    rows = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(release).as_posix()}"
        for path in files
    ]
    manifest = release / "RELEASE_MANIFEST_SHA256.txt"
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return release, hashlib.sha256(manifest.read_bytes()).hexdigest()


class PortableAdapterContractTests(unittest.TestCase):
    def setUp(self):
        self.queue = M.QueueFixtureAdapter()
        self.ledger = M.LedgerFixtureAdapter()
        self.queue_raw, self.ledger_raw = M._fixture_inputs()
        self.queue_events = tuple(self.queue.normalize_event(item) for item in self.queue_raw)
        self.ledger_events = tuple(self.ledger.normalize_event(item) for item in self.ledger_raw)
        self.queue_requests = M._requests_for(self.queue_events)
        self.ledger_requests = M._requests_for(self.ledger_events)

    def test_contract_has_no_execution_surface(self):
        self.assertEqual(M.EXECUTION_AUTHORITY, "NONE")
        for name in ("execute", "apply", "dispatch", "mutate_host"):
            self.assertFalse(hasattr(M.PortableHostAdapter, name))

    def test_supported_actions_are_hold_and_release_only(self):
        self.assertEqual(M.SUPPORTED_ACTIONS, ("HOLD", "RELEASE"))

    def test_identity_is_deterministic(self):
        first = M.build_adapter_identity(
            adapter_id="A", adapter_version="1", host_family="F", host_instance="I"
        )
        second = M.build_adapter_identity(
            adapter_id="A", adapter_version="1", host_family="F", host_instance="I"
        )
        self.assertEqual(first, second)

    def test_identity_tamper_fails(self):
        identity = self.queue.identity()
        valid, reason = M.validate_adapter_identity(
            replace(identity, host_instance="OTHER")
        )
        self.assertFalse(valid)
        self.assertEqual(reason, "IDENTITY_DIGEST_MISMATCH")

    def test_duplicate_capability_rejected(self):
        with self.assertRaises(ValueError):
            M.build_adapter_identity(
                adapter_id="A",
                adapter_version="1",
                host_family="F",
                host_instance="I",
                capabilities=("HOLD", "HOLD"),
            )

    def test_boolean_sequence_rejected(self):
        with self.assertRaises(TypeError):
            M.build_canonical_event(
                self.queue.identity(),
                sequence=True,
                event_id="E",
                event_type="X",
                subject_id="S",
                state_before=0,
                state_after=1,
            )

    def test_attribute_order_is_canonical(self):
        identity = self.queue.identity()
        first = M.build_canonical_event(
            identity,
            sequence=1,
            event_id="E",
            event_type="X",
            subject_id="S",
            state_before=0,
            state_after=1,
            attributes=(("b", 2), ("a", 1)),
        )
        second = M.build_canonical_event(
            identity,
            sequence=1,
            event_id="E",
            event_type="X",
            subject_id="S",
            state_before=0,
            state_after=1,
            attributes=(("a", 1), ("b", 2)),
        )
        self.assertEqual(first, second)

    def test_equivalent_events_share_semantic_digest(self):
        self.assertEqual(
            tuple(item.semantic_digest for item in self.queue_events),
            tuple(item.semantic_digest for item in self.ledger_events),
        )

    def test_adapter_binding_changes_event_digest(self):
        self.assertNotEqual(
            tuple(item.event_digest for item in self.queue_events),
            tuple(item.event_digest for item in self.ledger_events),
        )

    def test_queue_adapter_passes(self):
        report = M.evaluate_adapter(self.queue, self.queue_raw, self.queue_requests)
        self.assertTrue(report.passed)
        self.assertEqual(report.executed_actions, 0)

    def test_ledger_adapter_passes(self):
        report = M.evaluate_adapter(self.ledger, self.ledger_raw, self.ledger_requests)
        self.assertTrue(report.passed)
        self.assertEqual(report.executed_actions, 0)

    def test_host_operations_are_adapter_specific(self):
        queue = M.evaluate_adapter(self.queue, self.queue_raw, self.queue_requests)
        ledger = M.evaluate_adapter(self.ledger, self.ledger_raw, self.ledger_requests)
        self.assertNotEqual(
            tuple(item.host_operation for item in queue.outcomes),
            tuple(item.host_operation for item in ledger.outcomes),
        )
        self.assertEqual(
            tuple(item.action for item in queue.outcomes),
            tuple(item.action for item in ledger.outcomes),
        )

    def test_missing_adapter_fails_closed(self):
        report = M.evaluate_adapter(None, (), self.queue_requests)
        self.assertFalse(report.passed)
        self.assertEqual(report.first_error, "NO_ADAPTER")
        self.assertTrue(all(item.disposition == M.REJECTED for item in report.outcomes))

    def test_out_of_scope_action_fails_closed(self):
        hold_only = M.build_adapter_identity(
            adapter_id="HOLD-ONLY",
            adapter_version="1",
            host_family="F",
            host_instance="I",
            capabilities=(M.HOLD,),
        )

        class HoldOnly(M.QueueFixtureAdapter):
            def __init__(self):
                self._identity = hold_only

        adapter = HoldOnly()
        events = tuple(adapter.normalize_event(item) for item in self.queue_raw)
        report = M.evaluate_adapter(adapter, self.queue_raw, M._requests_for(events))
        self.assertFalse(report.passed)
        self.assertEqual(report.outcomes[1].reason_code, "ACTION_OUT_OF_SCOPE")

    def test_unknown_action_builder_rejects(self):
        with self.assertRaises(ValueError):
            M.build_action_request(
                request_id=1,
                action="DELETE",
                subject_id="S",
                source_event_digest="a" * 64,
                governance_session_digest="b" * 64,
                authority_digest="c" * 64,
                expected_state_digest="d" * 64,
                current_epoch=1,
            )

    def test_request_digest_tamper_rejected(self):
        request = replace(self.queue_requests[0], subject_id="OTHER")
        valid, reason = M.validate_action_request(request)
        self.assertFalse(valid)
        self.assertEqual(reason, "REQUEST_DIGEST_MISMATCH")

    def test_request_sequence_mismatch_rejected(self):
        original = self.queue_requests[0]
        bad = M.build_action_request(
            request_id=2,
            action=original.action,
            subject_id=original.subject_id,
            source_event_digest=original.source_event_digest,
            governance_session_digest=original.governance_session_digest,
            authority_digest=original.authority_digest,
            expected_state_digest=original.expected_state_digest,
            current_epoch=original.current_epoch,
        )
        report = M.evaluate_adapter(self.queue, self.queue_raw, (bad,))
        self.assertFalse(report.passed)
        self.assertEqual(report.outcomes[0].reason_code, "REQUEST_SEQUENCE_MISMATCH")

    def test_source_event_missing_rejected(self):
        request = M.build_action_request(
            request_id=1,
            action=M.HOLD,
            subject_id="TASK-7",
            source_event_digest="f" * 64,
            governance_session_digest="a" * 64,
            authority_digest="b" * 64,
            expected_state_digest=self.queue_events[0].state_after_digest,
            current_epoch=1,
        )
        report = M.evaluate_adapter(self.queue, self.queue_raw, (request,))
        self.assertFalse(report.passed)
        self.assertEqual(report.outcomes[0].reason_code, "SOURCE_EVENT_NOT_FOUND")

    def test_expected_state_mismatch_rejected(self):
        request = M.build_action_request(
            request_id=1,
            action=M.HOLD,
            subject_id="TASK-7",
            source_event_digest=self.queue_events[0].event_digest,
            governance_session_digest="a" * 64,
            authority_digest="b" * 64,
            expected_state_digest="c" * 64,
            current_epoch=1,
        )
        report = M.evaluate_adapter(self.queue, self.queue_raw, (request,))
        self.assertFalse(report.passed)
        self.assertEqual(report.outcomes[0].reason_code, "EXPECTED_STATE_MISMATCH")

    def test_event_sequence_mismatch_rejected(self):
        bad = dict(self.queue_raw[0])
        bad["sequence"] = 2
        report = M.evaluate_adapter(self.queue, (bad,), ())
        self.assertFalse(report.passed)
        self.assertEqual(report.first_error, "EVENT_SEQUENCE_MISMATCH")

    def test_duplicate_event_id_rejected(self):
        duplicate = dict(self.queue_raw[1])
        duplicate["event_id"] = self.queue_raw[0]["event_id"]
        report = M.evaluate_adapter(self.queue, (self.queue_raw[0], duplicate), ())
        self.assertFalse(report.passed)
        self.assertEqual(report.first_error, "DUPLICATE_EVENT_ID")

    def test_projection_claiming_execution_rejected(self):
        class Executing(M.QueueFixtureAdapter):
            def project_action(self, request, event):
                return M.build_projection(
                    self._identity,
                    request,
                    event,
                    host_operation="QUEUE_PAUSE",
                    would_dispatch=True,
                    executed=True,
                )

        adapter = Executing()
        events = tuple(adapter.normalize_event(item) for item in self.queue_raw)
        report = M.evaluate_adapter(adapter, self.queue_raw, M._requests_for(events))
        self.assertFalse(report.passed)
        self.assertEqual(report.outcomes[0].reason_code, "HIDDEN_EXECUTION_AUTHORITY")

    def test_projection_subject_mismatch_rejected(self):
        class Mismatch(M.QueueFixtureAdapter):
            def project_action(self, request, event):
                projection = super().project_action(request, event)
                return replace(projection, subject_id="OTHER")

        adapter = Mismatch()
        events = tuple(adapter.normalize_event(item) for item in self.queue_raw)
        report = M.evaluate_adapter(adapter, self.queue_raw, M._requests_for(events))
        self.assertFalse(report.passed)
        self.assertEqual(report.outcomes[0].reason_code, "PROJECTION_SUBJECT_MISMATCH")

    def test_adapter_identity_change_rejected(self):
        class Changing(M.QueueFixtureAdapter):
            def __init__(self):
                super().__init__()
                self.calls = 0

            def identity(self):
                self.calls += 1
                if self.calls == 1:
                    return self._identity
                return M.build_adapter_identity(
                    adapter_id="CHANGED",
                    adapter_version="1",
                    host_family="F",
                    host_instance="I",
                )

        adapter = Changing()
        report = M.evaluate_adapter(adapter, (), ())
        self.assertFalse(report.passed)
        self.assertEqual(report.first_error, "ADAPTER_IDENTITY_CHANGED")

    def test_receipt_replay_passes(self):
        report = M.evaluate_adapter(self.queue, self.queue_raw, self.queue_requests)
        replay = M.replay_receipts(report.receipts)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.final_digest, report.report_digest)

    def test_receipt_payload_tamper_detected(self):
        report = M.evaluate_adapter(self.queue, self.queue_raw, self.queue_requests)
        receipts = list(report.receipts)
        receipts[2] = replace(receipts[2], payload="tampered")
        self.assertFalse(M.replay_receipts(tuple(receipts)).passed)

    def test_receipt_reorder_detected(self):
        report = M.evaluate_adapter(self.queue, self.queue_raw, self.queue_requests)
        receipts = list(report.receipts)
        receipts[2], receipts[3] = receipts[3], receipts[2]
        self.assertFalse(M.replay_receipts(tuple(receipts)).passed)

    def test_summary_execution_claim_detected_even_if_rehashed(self):
        report = M.evaluate_adapter(self.queue, self.queue_raw, self.queue_requests)
        receipts = list(report.receipts)
        summary = replace(receipts[-1], payload='{"executed_actions":1}')
        summary = replace(
            summary,
            receipt_hash=M._receipt_hash(
                summary.receipt_id,
                summary.kind,
                summary.subject,
                summary.payload,
                summary.prior_hash,
            ),
        )
        receipts[-1] = summary
        replay = M.replay_receipts(tuple(receipts))
        self.assertFalse(replay.passed)
        self.assertEqual(replay.first_error, "SUMMARY_EXECUTION_NONZERO")

    def test_valid_frozen_fixture_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            result = M.verify_frozen_v02(release, manifest_sha)
            self.assertTrue(result.passed)
            self.assertEqual(result.checked_files, 2)

    def test_changed_frozen_file_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            (release / "README.md").write_text("changed\n", encoding="utf-8")
            result = M.verify_frozen_v02(release, manifest_sha)
            self.assertFalse(result.passed)
            self.assertTrue(result.first_error.startswith("FILE_HASH_MISMATCH:"))

    def test_extra_frozen_file_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            (release / "extra.txt").write_text("extra", encoding="utf-8")
            result = M.verify_frozen_v02(release, manifest_sha)
            self.assertFalse(result.passed)
            self.assertTrue(result.first_error.startswith("EXTRA_FILE:"))

    def test_manifest_digest_mismatch_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            release, _ = make_frozen_fixture(Path(directory))
            result = M.verify_frozen_v02(release, "0" * 64)
            self.assertFalse(result.passed)
            self.assertEqual(result.first_error, "MANIFEST_SHA256_MISMATCH")

    def test_stage1_qualification_passes_against_fixture_release(self):
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            qualification = M.run_stage1_qualification(
                frozen_root=release, expected_manifest_sha256=manifest_sha
            )
            self.assertTrue(qualification.passed)
            self.assertEqual(qualification.adapters_qualified, 2)
            self.assertEqual(qualification.executed_actions, 0)

    def test_stage1_qualification_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            first = M.run_stage1_qualification(
                frozen_root=release, expected_manifest_sha256=manifest_sha
            )
            second = M.run_stage1_qualification(
                frozen_root=release, expected_manifest_sha256=manifest_sha
            )
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

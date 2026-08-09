from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import sys

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "portability"
    / "live_host_substitution.py"
)
SPEC = importlib.util.spec_from_file_location("live_host_substitution", MODULE_PATH)
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


def rehash_campaign(receipts):
    rebuilt = []
    for receipt in receipts:
        prior = rebuilt[-1].receipt_hash if rebuilt else M.ZERO_DIGEST
        digest = M._receipt_hash(
            receipt.receipt_id,
            receipt.kind,
            receipt.subject,
            receipt.payload,
            prior,
        )
        rebuilt.append(replace(receipt, prior_hash=prior, receipt_hash=digest))
    return tuple(rebuilt)


class LiveHostSubstitutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = M.run_live_substitution()
        cls.queue_request = cls.report.queue_adapter_report.requests[0]
        cls.queue_projection = cls.report.queue_adapter_report.projections[0]
        cls.workflow_request = cls.report.workflow_adapter_report.requests[0]
        cls.workflow_projection = cls.report.workflow_adapter_report.projections[0]

    def test_queue_host_name(self):
        self.assertEqual(M.queue_host.HOST_NAME, "DETERMINISTIC LEASE QUEUE HOST")

    def test_queue_host_baseline(self):
        run = M.queue_host.run_queue(M.queue_host.baseline_commands())
        self.assertEqual(run.final_records, (M.queue_host.QueueRecord("TASK-7", M.queue_host.COMPLETE, 4),))
        self.assertFalse(run.rejected_command_ids)

    def test_queue_host_deterministic(self):
        commands = M.queue_host.baseline_commands()
        self.assertEqual(M.queue_host.run_queue(commands), M.queue_host.run_queue(commands))

    def test_queue_host_duplicate_command_rejected(self):
        command = M.queue_host.QueueCommand("D", "T", M.queue_host.ENQUEUE, 0)
        run = M.queue_host.run_queue((command, command))
        self.assertEqual(run.rejected_command_ids, ("D", "D"))

    def test_queue_host_version_mismatch_rejected(self):
        run = M.queue_host.run_queue((M.queue_host.QueueCommand("A", "T", M.queue_host.ENQUEUE, 1),))
        self.assertEqual(run.events[0].reason, "VERSION_MISMATCH")

    def test_queue_host_unsupported_operation_rejected(self):
        run = M.queue_host.run_queue((M.queue_host.QueueCommand("A", "T", "DELETE", 0),))
        self.assertEqual(run.events[0].reason, "UNSUPPORTED_OPERATION")

    def test_queue_host_boolean_version_rejected(self):
        run = M.queue_host.run_queue((M.queue_host.QueueCommand("A", "T", M.queue_host.ENQUEUE, True),))
        self.assertEqual(run.events[0].reason, "VERSION_NOT_INTEGER")

    def test_queue_host_negative_version_rejected(self):
        run = M.queue_host.run_queue((M.queue_host.QueueCommand("A", "T", M.queue_host.ENQUEUE, -1),))
        self.assertEqual(run.events[0].reason, "NEGATIVE_VERSION")

    def test_queue_host_missing_item_rejected(self):
        run = M.queue_host.run_queue((M.queue_host.QueueCommand("A", "T", M.queue_host.CLAIM, 0),))
        self.assertEqual(run.events[0].reason, "ITEM_NOT_FOUND")

    def test_queue_host_illegal_transition_rejected(self):
        commands = (
            M.queue_host.QueueCommand("A", "T", M.queue_host.ENQUEUE, 0),
            M.queue_host.QueueCommand("B", "T", M.queue_host.FINISH, 1),
        )
        run = M.queue_host.run_queue(commands)
        self.assertEqual(run.events[-1].reason, "ILLEGAL_TRANSITION")

    def test_queue_host_drop_from_ready(self):
        commands = (
            M.queue_host.QueueCommand("A", "T", M.queue_host.ENQUEUE, 0),
            M.queue_host.QueueCommand("B", "T", M.queue_host.DROP, 1),
        )
        self.assertEqual(M.queue_host.run_queue(commands).final_records[0].phase, M.queue_host.DROPPED)

    def test_queue_host_suspend_continue(self):
        commands = (
            M.queue_host.QueueCommand("A", "T", M.queue_host.ENQUEUE, 0),
            M.queue_host.QueueCommand("B", "T", M.queue_host.CLAIM, 1),
            M.queue_host.QueueCommand("C", "T", M.queue_host.SUSPEND, 2),
            M.queue_host.QueueCommand("D", "T", M.queue_host.CONTINUE, 3),
        )
        self.assertEqual(M.queue_host.run_queue(commands).final_records[0], M.queue_host.QueueRecord("T", M.queue_host.ACTIVE, 4))

    def test_queue_host_digest_matches_text(self):
        run = M.queue_host.run_queue(M.queue_host.baseline_commands())
        self.assertEqual(hashlib.sha256(run.canonical_text().encode()).hexdigest(), run.run_digest)

    def test_queue_host_has_no_bolt_on_import(self):
        tree = ast.parse(M.QUEUE_HOST_PATH.read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name.lower() for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append((node.module or "").lower())
        for token in ("portable_adapter_contract", "natural_math", "cntm", "governance", "bolt_on"):
            self.assertFalse(any(token in module for module in imported))

    def test_adapter_surfaces_have_no_execution_method(self):
        for cls in (M.contract.PortableHostAdapter, M.QueueLiveAdapter, M.WorkflowLiveAdapter):
            for name in ("execute", "apply", "dispatch", "mutate_host"):
                self.assertFalse(hasattr(cls, name))

    def test_queue_adapter_identity(self):
        identity = M.QueueLiveAdapter().identity()
        self.assertEqual(identity.host_instance, M.QUEUE_HOST_ID)
        self.assertTrue(M.contract.validate_adapter_identity(identity)[0])

    def test_workflow_adapter_identity(self):
        identity = M.WorkflowLiveAdapter().identity()
        self.assertEqual(identity.host_instance, M.WORKFLOW_HOST_ID)
        self.assertTrue(M.contract.validate_adapter_identity(identity)[0])

    def test_queue_event_normalization(self):
        adapter = M.QueueLiveAdapter()
        event = adapter.normalize_event(self.report.queue_runtime_before.run.events[-1])
        self.assertEqual(event.subject_id, M.SUBJECT_ID)
        self.assertEqual(event.sequence, 2)

    def test_workflow_event_normalization(self):
        adapter = M.WorkflowLiveAdapter()
        event = adapter.normalize_event(self.report.workflow_runtime_before.run.events[-1])
        self.assertEqual(event.subject_id, M.SUBJECT_ID)
        self.assertEqual(event.sequence, 3)

    def test_queue_hold_projection(self):
        self.assertEqual(self.queue_projection.host_operation, M.queue_host.SUSPEND)
        self.assertFalse(self.queue_projection.executed)

    def test_workflow_release_projection(self):
        self.assertEqual(self.workflow_projection.host_operation, M.workflow_host.RESUME)
        self.assertFalse(self.workflow_projection.executed)

    def test_projections_do_not_execute(self):
        self.assertFalse(self.report.queue_adapter_report.outcomes[0].executed)
        self.assertFalse(self.report.workflow_adapter_report.outcomes[0].executed)

    def test_queue_adapter_rejects_wrong_raw_type(self):
        with self.assertRaises(TypeError):
            M.QueueLiveAdapter().normalize_event({})

    def test_execution_permit_is_deterministic(self):
        first = M.issue_execution_permit(
            session_digest=self.report.session_digest,
            host_id=M.QUEUE_HOST_ID,
            identity=self.report.queue_adapter_report.identity,
            request=self.queue_request,
            projection=self.queue_projection,
            expected_native_state=M.queue_host.ACTIVE,
            valid_epoch=500,
        )
        self.assertEqual(first, self.report.queue_permit)

    def test_queue_execution_permit_valid(self):
        self.assertEqual(M.validate_execution_permit(self.report.queue_permit), (True, "VALID"))

    def test_workflow_execution_permit_valid(self):
        self.assertEqual(M.validate_execution_permit(self.report.workflow_permit), (True, "VALID"))

    def test_execution_permit_hash_tamper(self):
        permit = replace(self.report.queue_permit, host_id="OTHER")
        self.assertEqual(M.validate_execution_permit(permit)[1], "PERMIT_HASH_MISMATCH")

    def test_execution_permit_use_budget(self):
        permit = replace(self.report.queue_permit, max_uses=2)
        self.assertEqual(M.validate_execution_permit(permit)[1], "PERMIT_USE_BUDGET_INVALID")

    def test_queue_epoch_mismatch_rejected(self):
        _, outcome = M.execute_queue_host_boundary(
            self.report.queue_runtime_before,
            identity=self.report.queue_adapter_report.identity,
            request=self.queue_request,
            projection=self.queue_projection,
            permit=self.report.queue_permit,
            current_epoch=501,
        )
        self.assertFalse(outcome.executed)
        self.assertEqual(outcome.reason_code, "PERMIT_EPOCH_MISMATCH")

    def test_queue_host_mismatch_rejected(self):
        permit = replace(self.report.queue_permit, host_id=M.WORKFLOW_HOST_ID)
        permit = replace(permit, permit_hash=M._digest_json(permit.unsigned_record()))
        _, outcome = M.execute_queue_host_boundary(
            self.report.queue_runtime_before,
            identity=self.report.queue_adapter_report.identity,
            request=self.queue_request,
            projection=self.queue_projection,
            permit=permit,
            current_epoch=500,
        )
        self.assertEqual(outcome.reason_code, "PERMIT_HOST_MISMATCH")

    def test_queue_adapter_binding_mismatch_rejected(self):
        permit = replace(self.report.queue_permit, adapter_identity_digest="a" * 64)
        permit = replace(permit, permit_hash=M._digest_json(permit.unsigned_record()))
        _, outcome = M.execute_queue_host_boundary(
            self.report.queue_runtime_before,
            identity=self.report.queue_adapter_report.identity,
            request=self.queue_request,
            projection=self.queue_projection,
            permit=permit,
            current_epoch=500,
        )
        self.assertEqual(outcome.reason_code, "PERMIT_ADAPTER_MISMATCH")

    def test_queue_request_binding_mismatch_rejected(self):
        permit = replace(self.report.queue_permit, request_digest="a" * 64)
        permit = replace(permit, permit_hash=M._digest_json(permit.unsigned_record()))
        _, outcome = M.execute_queue_host_boundary(
            self.report.queue_runtime_before,
            identity=self.report.queue_adapter_report.identity,
            request=self.queue_request,
            projection=self.queue_projection,
            permit=permit,
            current_epoch=500,
        )
        self.assertEqual(outcome.reason_code, "PERMIT_REQUEST_MISMATCH")

    def test_queue_projection_binding_mismatch_rejected(self):
        permit = replace(self.report.queue_permit, projection_digest="a" * 64)
        permit = replace(permit, permit_hash=M._digest_json(permit.unsigned_record()))
        _, outcome = M.execute_queue_host_boundary(
            self.report.queue_runtime_before,
            identity=self.report.queue_adapter_report.identity,
            request=self.queue_request,
            projection=self.queue_projection,
            permit=permit,
            current_epoch=500,
        )
        self.assertEqual(outcome.reason_code, "PERMIT_PROJECTION_MISMATCH")

    def test_queue_native_state_mismatch_rejected(self):
        permit = replace(self.report.queue_permit, expected_native_state=M.queue_host.HELD)
        permit = replace(permit, permit_hash=M._digest_json(permit.unsigned_record()))
        _, outcome = M.execute_queue_host_boundary(
            self.report.queue_runtime_before,
            identity=self.report.queue_adapter_report.identity,
            request=self.queue_request,
            projection=self.queue_projection,
            permit=permit,
            current_epoch=500,
        )
        self.assertEqual(outcome.reason_code, "NATIVE_STATE_MISMATCH")

    def test_queue_operation_mismatch_rejected(self):
        projection = replace(self.queue_projection, host_operation=M.queue_host.CONTINUE)
        projection = replace(projection, projection_digest=M.contract._digest_json(projection.unsigned_record()))
        permit = M.issue_execution_permit(
            session_digest=self.report.session_digest,
            host_id=M.QUEUE_HOST_ID,
            identity=self.report.queue_adapter_report.identity,
            request=self.queue_request,
            projection=projection,
            expected_native_state=M.queue_host.ACTIVE,
            valid_epoch=500,
        )
        _, outcome = M.execute_queue_host_boundary(
            self.report.queue_runtime_before,
            identity=self.report.queue_adapter_report.identity,
            request=self.queue_request,
            projection=projection,
            permit=permit,
            current_epoch=500,
        )
        self.assertEqual(outcome.reason_code, "QUEUE_OPERATION_NOT_AUTHORIZED")

    def test_queue_hold_executes_at_host_boundary(self):
        self.assertTrue(self.report.queue_outcome.executed)
        self.assertEqual(self.report.queue_outcome.native_state_after, M.queue_host.HELD)

    def test_workflow_release_executes_at_host_boundary(self):
        self.assertTrue(self.report.workflow_outcome.executed)
        self.assertEqual(self.report.workflow_outcome.native_state_after, M.workflow_host.RUNNING)

    def test_reused_permit_rejected(self):
        _, outcome = M.execute_queue_host_boundary(
            self.report.queue_runtime_after,
            identity=self.report.queue_adapter_report.identity,
            request=self.queue_request,
            projection=self.queue_projection,
            permit=self.report.queue_permit,
            current_epoch=500,
        )
        self.assertEqual(outcome.reason_code, "PERMIT_ALREADY_CONSUMED")

    def test_checkpoint_valid(self):
        self.assertEqual(M.validate_checkpoint(self.report.checkpoint), (True, "VALID"))

    def test_checkpoint_semantic_tamper_rejected(self):
        checkpoint = replace(self.report.checkpoint, portable_state="ACTIVE")
        self.assertEqual(M.validate_checkpoint(checkpoint)[1], "CHECKPOINT_SEMANTICS_INVALID")

    def test_checkpoint_requires_executed_hold(self):
        outcome = replace(self.report.queue_outcome, executed=False)
        outcome = replace(outcome, outcome_digest=M._digest_json(outcome.unsigned_record()))
        with self.assertRaises(ValueError):
            M.build_checkpoint(session_digest=self.report.session_digest, outcome=outcome)

    def test_substitution_ticket_valid(self):
        valid, _ = M.validate_substitution_ticket(
            self.report.substitution_ticket,
            checkpoint=self.report.checkpoint,
            source_detach_digest=self.report.attachment_events[1].event_digest,
            target_ready_digest=self.report.workflow_runtime_before.run.run_digest,
            current_epoch=501,
        )
        self.assertTrue(valid)

    def test_substitution_ticket_target_tamper(self):
        ticket = replace(self.report.substitution_ticket, target_host_id="OTHER")
        valid, reason = M.validate_substitution_ticket(
            ticket,
            checkpoint=self.report.checkpoint,
            source_detach_digest=self.report.attachment_events[1].event_digest,
            target_ready_digest=self.report.workflow_runtime_before.run.run_digest,
            current_epoch=501,
        )
        self.assertFalse(valid)
        self.assertEqual(reason, "TICKET_TARGET_HOST_MISMATCH")

    def test_substitution_ticket_epoch_mismatch(self):
        valid, reason = M.validate_substitution_ticket(
            self.report.substitution_ticket,
            checkpoint=self.report.checkpoint,
            source_detach_digest=self.report.attachment_events[1].event_digest,
            target_ready_digest=self.report.workflow_runtime_before.run.run_digest,
            current_epoch=502,
        )
        self.assertFalse(valid)
        self.assertEqual(reason, "TICKET_EPOCH_MISMATCH")

    def test_substitution_ticket_detach_binding(self):
        valid, reason = M.validate_substitution_ticket(
            self.report.substitution_ticket,
            checkpoint=self.report.checkpoint,
            source_detach_digest="a" * 64,
            target_ready_digest=self.report.workflow_runtime_before.run.run_digest,
            current_epoch=501,
        )
        self.assertFalse(valid)
        self.assertEqual(reason, "TICKET_DETACH_MISMATCH")

    def test_substitution_ticket_target_ready_binding(self):
        valid, reason = M.validate_substitution_ticket(
            self.report.substitution_ticket,
            checkpoint=self.report.checkpoint,
            source_detach_digest=self.report.attachment_events[1].event_digest,
            target_ready_digest="a" * 64,
            current_epoch=501,
        )
        self.assertFalse(valid)
        self.assertEqual(reason, "TICKET_TARGET_READY_MISMATCH")

    def test_attachment_replay_passes(self):
        self.assertTrue(self.report.attachment_replay.passed)

    def test_attachment_host_sequence(self):
        self.assertEqual(self.report.attachment_replay.host_sequence, (M.QUEUE_HOST_ID, M.WORKFLOW_HOST_ID))

    def test_attachment_rejects_attach_with_active_host(self):
        first = self.report.attachment_events[0]
        second = M.build_attachment_event(
            sequence=2,
            event_type="ATTACH",
            host_id=M.WORKFLOW_HOST_ID,
            adapter_identity_digest=self.report.workflow_adapter_report.identity.identity_digest,
            session_digest=self.report.session_digest,
            checkpoint_digest=self.report.checkpoint.checkpoint_digest,
            prior_event_digest=first.event_digest,
        )
        self.assertEqual(M.replay_attachment_events((first, second)).first_error, "ATTACH_WITH_ACTIVE_HOST")

    def test_attachment_rejects_detach_mismatch(self):
        first = self.report.attachment_events[0]
        second = replace(self.report.attachment_events[1], host_id=M.WORKFLOW_HOST_ID)
        second = replace(second, event_digest=M._digest_json(second.unsigned_record()))
        self.assertEqual(M.replay_attachment_events((first, second)).first_error, "DETACH_HOST_MISMATCH")

    def test_attachment_rejects_missing_substitution_checkpoint(self):
        events = list(self.report.attachment_events[:3])
        events[2] = replace(events[2], checkpoint_digest=M.ZERO_DIGEST)
        events[2] = replace(events[2], event_digest=M._digest_json(events[2].unsigned_record()))
        self.assertEqual(M.replay_attachment_events(tuple(events)).first_error, "SUBSTITUTION_CHECKPOINT_MISSING")

    def test_attachment_rejects_session_change(self):
        events = list(self.report.attachment_events)
        events[2] = replace(events[2], session_digest="a" * 64)
        events[2] = replace(events[2], event_digest=M._digest_json(events[2].unsigned_record()))
        self.assertEqual(M.replay_attachment_events(tuple(events)).first_error, "ATTACHMENT_SESSION_MISMATCH")

    def test_attachment_rejects_detach_adapter_change(self):
        events = list(self.report.attachment_events[:2])
        events[1] = replace(events[1], adapter_identity_digest="a" * 64)
        events[1] = replace(events[1], event_digest=M._digest_json(events[1].unsigned_record()))
        self.assertEqual(M.replay_attachment_events(tuple(events)).first_error, "DETACH_ADAPTER_MISMATCH")

    def test_attachment_digest_tamper(self):
        events = list(self.report.attachment_events)
        events[1] = replace(events[1], checkpoint_digest="a" * 64)
        self.assertEqual(M.replay_attachment_events(tuple(events)).first_error, "ATTACHMENT_DIGEST_MISMATCH")

    def test_live_report_deterministic(self):
        self.assertEqual(self.report, M.run_live_substitution())

    def test_campaign_replay_passes(self):
        self.assertTrue(self.report.replay.passed)

    def test_campaign_and_replay_digest_match(self):
        self.assertEqual(self.report.campaign_digest, self.report.replay.final_digest)

    def test_campaign_action_order(self):
        self.assertEqual(self.report.replay.actions, (M.contract.HOLD, M.contract.RELEASE))

    def test_campaign_final_native_state(self):
        self.assertEqual(self.report.replay.final_native_state, M.workflow_host.DONE)

    def test_campaign_queue_ends_held(self):
        self.assertEqual(self.report.queue_runtime_after.run.final_records[0].phase, M.queue_host.HELD)

    def test_campaign_workflow_resumes(self):
        self.assertEqual(self.report.workflow_runtime_after.run.final_records[0].state, M.workflow_host.RUNNING)

    def test_campaign_workflow_continues_to_done(self):
        self.assertEqual(self.report.workflow_final_run.final_records[0].state, M.workflow_host.DONE)

    def test_campaign_receipt_count(self):
        self.assertEqual(len(self.report.receipts), 20)

    def test_campaign_receipt_tamper_detected(self):
        receipts = list(self.report.receipts)
        receipts[7] = replace(receipts[7], payload="TAMPERED")
        self.assertFalse(M.replay_campaign_receipts(tuple(receipts)).passed)

    def test_campaign_receipt_reorder_detected(self):
        receipts = list(self.report.receipts)
        receipts[8], receipts[9] = receipts[9], receipts[8]
        self.assertFalse(M.replay_campaign_receipts(tuple(receipts)).passed)

    def test_rehashed_session_authority_tamper_detected(self):
        receipts = list(self.report.receipts)
        payload = json.loads(receipts[0].payload)
        payload["bolt_on_execution_authority"] = "DIRECT"
        receipts[0] = replace(receipts[0], payload=M._canonical_json(payload))
        replay = M.replay_campaign_receipts(rehash_campaign(receipts))
        self.assertEqual(replay.first_error, "SESSION_AUTHORITY_INVALID")

    def test_rehashed_projection_execution_tamper_detected(self):
        receipts = list(self.report.receipts)
        payload = json.loads(receipts[4].payload)
        payload["executed"] = True
        receipts[4] = replace(receipts[4], payload=M._canonical_json(payload))
        replay = M.replay_campaign_receipts(rehash_campaign(receipts))
        self.assertEqual(replay.first_error, "ADAPTER_EXECUTION_NONZERO")

    def test_rehashed_outcome_transition_tamper_detected(self):
        receipts = list(self.report.receipts)
        payload = json.loads(receipts[6].payload)
        payload["native_state_after"] = M.queue_host.COMPLETE
        unsigned = {key: value for key, value in payload.items() if key != "outcome_digest"}
        payload["outcome_digest"] = M._digest_json(unsigned)
        receipts[6] = replace(receipts[6], payload=M._canonical_json(payload))
        replay = M.replay_campaign_receipts(rehash_campaign(receipts))
        self.assertEqual(replay.first_error, "QUEUE_TRANSITION_INVALID")

    def test_rehashed_checkpoint_tamper_detected(self):
        receipts = list(self.report.receipts)
        payload = json.loads(receipts[7].payload)
        payload["portable_state"] = "ACTIVE"
        unsigned = {key: value for key, value in payload.items() if key != "checkpoint_digest"}
        payload["checkpoint_digest"] = M._digest_json(unsigned)
        receipts[7] = replace(receipts[7], payload=M._canonical_json(payload))
        replay = M.replay_campaign_receipts(rehash_campaign(receipts))
        self.assertEqual(replay.first_error, "CHECKPOINT_INVALID")

    def test_rehashed_target_ready_tamper_detected(self):
        receipts = list(self.report.receipts)
        payload = json.loads(receipts[10].payload)
        payload["native_state"] = M.workflow_host.RUNNING
        receipts[10] = replace(receipts[10], payload=M._canonical_json(payload))
        replay = M.replay_campaign_receipts(rehash_campaign(receipts))
        self.assertEqual(replay.first_error, "CAMPAIGN_CONTINUITY_MISMATCH")

    def test_rehashed_summary_tamper_detected(self):
        receipts = list(self.report.receipts)
        payload = json.loads(receipts[-1].payload)
        payload["actions"] = [M.contract.RELEASE, M.contract.HOLD]
        receipts[-1] = replace(receipts[-1], payload=M._canonical_json(payload))
        replay = M.replay_campaign_receipts(rehash_campaign(receipts))
        self.assertEqual(replay.first_error, "CAMPAIGN_SUMMARY_INVALID")

    def test_stage4_qualification_with_frozen_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            result = M.run_stage4_qualification(
                frozen_root=release,
                expected_manifest_sha256=manifest_sha,
            )
            self.assertTrue(result.passed)

    def test_prior_source_hashes_are_bound(self):
        source = dict(M._source_snapshot())
        self.assertEqual(source[M.CONTRACT_PATH.relative_to(M.REPOSITORY_ROOT).as_posix()], M.EXPECTED_STAGE1_SOURCE_SHA256)
        self.assertEqual(source[M.STAGE2_PATH.relative_to(M.REPOSITORY_ROOT).as_posix()], M.EXPECTED_STAGE2_SOURCE_SHA256)
        self.assertEqual(source[M.STAGE3_PATH.relative_to(M.REPOSITORY_ROOT).as_posix()], M.EXPECTED_STAGE3_SOURCE_SHA256)

    def test_bolt_on_execution_count_zero(self):
        self.assertEqual(self.report.bolt_on_executed_actions, 0)

    def test_host_execution_count_two(self):
        self.assertEqual(self.report.executed_host_actions, 2)

    def test_exactly_one_substitution(self):
        self.assertEqual(self.report.substitutions, 1)


if __name__ == "__main__":
    unittest.main()

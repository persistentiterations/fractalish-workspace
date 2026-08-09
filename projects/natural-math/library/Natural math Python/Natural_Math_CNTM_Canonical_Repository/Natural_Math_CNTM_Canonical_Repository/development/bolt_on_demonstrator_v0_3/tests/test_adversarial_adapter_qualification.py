from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "portability"
    / "adversarial_adapter_qualification.py"
)
SPEC = importlib.util.spec_from_file_location(
    "adversarial_adapter_qualification", MODULE_PATH
)
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


class AdversarialAdapterQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = M.run_adversarial_campaign()
        cls.by_id = {item.attack_id: item for item in cls.report.attacks}

    def test_stage_constants(self):
        self.assertEqual(M.STAGE_VERSION, "0.3.5")
        self.assertEqual(M.BOLT_ON_EXECUTION_AUTHORITY, "NONE")
        self.assertEqual(M.EXECUTION_BOUNDARY, "HOST_BOUNDARY_ONLY")

    def test_attack_catalog_count_and_ids(self):
        self.assertEqual(len(M.ATTACK_SPECS), 48)
        ids = [item.attack_id for item in M.ATTACK_SPECS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids[0], "A01")
        self.assertEqual(ids[-1], "R06")

    def test_all_attacks_rejected(self):
        self.assertEqual(self.report.attack_count, 48)
        self.assertEqual(self.report.rejected_count, 48)
        self.assertTrue(all(item.rejected for item in self.report.attacks))

    def test_category_coverage(self):
        self.assertEqual(
            self.report.categories,
            ("ADAPTER", "PERMIT", "RECEIPT", "SUBSTITUTION"),
        )

    def test_execution_counts_and_state_preservation(self):
        self.assertEqual(self.report.baseline.executed_host_actions, 2)
        self.assertEqual(self.report.attack_host_actions, 0)
        self.assertEqual(self.report.bolt_on_executed_actions, 0)
        self.assertTrue(all(item.host_state_unchanged for item in self.report.attacks))

    def test_baseline_and_valid_controls(self):
        baseline = self.report.baseline
        self.assertTrue(baseline.replay.passed)
        self.assertEqual(baseline.campaign_digest, baseline.replay.final_digest)
        queue_valid, _ = M.validate_execution_context(
            baseline.queue_runtime_before,
            host_id=M.stage4.QUEUE_HOST_ID,
            identity=baseline.queue_adapter_report.identity,
            event=baseline.queue_adapter_report.events[-1],
            request=baseline.queue_adapter_report.requests[0],
            projection=baseline.queue_adapter_report.projections[0],
            permit=baseline.queue_permit,
            current_epoch=500,
        )
        workflow_valid, _ = M.validate_execution_context(
            baseline.workflow_runtime_before,
            host_id=M.stage4.WORKFLOW_HOST_ID,
            identity=baseline.workflow_adapter_report.identity,
            event=baseline.workflow_adapter_report.events[-1],
            request=baseline.workflow_adapter_report.requests[0],
            projection=baseline.workflow_adapter_report.projections[0],
            permit=baseline.workflow_permit,
            current_epoch=502,
        )
        substitution_valid, _ = M.validate_substitution_context(
            baseline.substitution_ticket,
            checkpoint=baseline.checkpoint,
            queue_outcome=baseline.queue_outcome,
            source_detach_event=baseline.attachment_events[1],
            target_runtime=baseline.workflow_runtime_before,
            current_epoch=501,
        )
        self.assertTrue(queue_valid and workflow_valid and substitution_valid)

    def test_adversarial_replay_and_digest(self):
        self.assertTrue(self.report.replay.passed)
        self.assertEqual(self.report.campaign_digest, self.report.replay.final_digest)
        self.assertEqual(self.report.replay.attack_count, 48)
        self.assertEqual(self.report.replay.rejected_count, 48)

    def test_deterministic_campaign(self):
        self.assertEqual(self.report, M.run_adversarial_campaign())

    def test_adversarial_receipt_tamper_detection(self):
        receipts = list(self.report.receipts)
        receipts[3] = replace(receipts[3], payload="TAMPERED")
        replay = M.replay_adversarial_receipts(tuple(receipts))
        self.assertFalse(replay.passed)
        self.assertTrue(replay.first_error.startswith("RECEIPT_HASH_MISMATCH"))

    def test_adversarial_receipt_reorder_detection(self):
        receipts = list(self.report.receipts)
        receipts[3], receipts[4] = receipts[4], receipts[3]
        replay = M.replay_adversarial_receipts(tuple(receipts))
        self.assertFalse(replay.passed)

    def test_adversarial_semantic_rehash_detection(self):
        receipts = list(self.report.receipts)
        payload = json.loads(receipts[2].payload)
        payload["rejected"] = False
        unsigned = {key: value for key, value in payload.items() if key != "result_digest"}
        payload["result_digest"] = M._digest_json(unsigned)
        receipts[2] = replace(receipts[2], payload=M._canonical_json(payload))
        replay = M.replay_adversarial_receipts(M._rehash_adversarial_receipts(receipts))
        self.assertFalse(replay.passed)
        self.assertEqual(replay.first_error, "ATTACK_NOT_SAFELY_REJECTED")

    def test_source_bindings_and_frozen_fixture(self):
        source = dict(M._source_snapshot())
        self.assertEqual(
            source[M.CONTRACT_PATH.relative_to(M.REPOSITORY_ROOT).as_posix()],
            M.EXPECTED_STAGE1_SOURCE_SHA256,
        )
        self.assertEqual(
            source[M.STAGE2_PATH.relative_to(M.REPOSITORY_ROOT).as_posix()],
            M.EXPECTED_STAGE2_SOURCE_SHA256,
        )
        self.assertEqual(
            source[M.STAGE3_PATH.relative_to(M.REPOSITORY_ROOT).as_posix()],
            M.EXPECTED_STAGE3_SOURCE_SHA256,
        )
        self.assertEqual(
            source[M.STAGE4_PATH.relative_to(M.REPOSITORY_ROOT).as_posix()],
            M.EXPECTED_STAGE4_SOURCE_SHA256,
        )
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            qualification = M.run_stage5_qualification(
                frozen_root=release,
                expected_manifest_sha256=manifest_sha,
            )
        self.assertTrue(qualification.passed)
        self.assertTrue(qualification.valid_control_contexts_pass)


def _make_attack_test(attack_id: str):
    def test(self):
        spec = next(item for item in M.ATTACK_SPECS if item.attack_id == attack_id)
        result = self.by_id[attack_id]
        self.assertTrue(result.rejected)
        self.assertEqual(result.expected_reason, spec.expected_reason)
        self.assertEqual(result.observed_reason, spec.expected_reason)
        self.assertTrue(result.host_state_unchanged)
        self.assertEqual(result.attack_host_actions, 0)
        self.assertEqual(result.bolt_on_executed_actions, 0)
        self.assertEqual(result.result_digest, M._digest_json(result.unsigned_record()))
    return test


for _spec in M.ATTACK_SPECS:
    setattr(
        AdversarialAdapterQualificationTests,
        f"test_attack_{_spec.attack_id.lower()}",
        _make_attack_test(_spec.attack_id),
    )


if __name__ == "__main__":
    unittest.main()

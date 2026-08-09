#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
PATH = PROJECT_DIR / "release" / "controlled_release_host.py"
spec = importlib.util.spec_from_file_location("controlled_release_host", PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(PATH)
release = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = release
spec.loader.exec_module(release)

class ControlledReleaseHostTests(unittest.TestCase):
    def setUp(self):
        self.jobs = release.ordinary_host.baseline_jobs()
        advisory = release.mediation.prepare_hold_authority(self.jobs, current_epoch=200)
        hold_permit = release.mediation.issue_hold_permit(advisory, current_epoch=200)
        self.hold = release.mediation.mediate_with_hold(self.jobs, advisory, hold_permit, current_epoch=200)
        self.grant = release.prepare_release_authority(self.hold, 201)
        self.permit = release.issue_release_permit(self.hold, self.grant, 201)
    def release_once(self, grant="DEFAULT", permit="DEFAULT", epoch=201, consumed=()):
        g = self.grant if grant == "DEFAULT" else grant
        p = self.permit if permit == "DEFAULT" else permit
        return release.release_from_hold(self.jobs, self.hold, g, p, epoch, consumed)
    def rehash_permit(self, permit):
        blank = replace(permit, permit_hash="")
        return replace(blank, permit_hash=release._permit_hash(blank))
    def rehash_grant(self, grant):
        blank = replace(grant, grant_hash="")
        return replace(blank, grant_hash=release._grant_hash(blank))
    def test_stage3_qualification_passes(self): self.assertTrue(release.qualify_stage3().passed)
    def test_release_executes_exactly_once(self):
        r=self.release_once(); self.assertTrue(r.released); self.assertEqual(r.executed_actions,1)
    def test_original_batch_is_restored_exactly(self): self.assertEqual(self.release_once().restored_batch,self.jobs)
    def test_released_job_is_immutable(self): self.assertEqual(self.release_once().released_jobs,self.hold.held_jobs)
    def test_hold_queue_is_empty_after_release(self): self.assertEqual(self.release_once().remaining_held_jobs,())
    def test_host_rules_are_not_bypassed(self):
        r=self.release_once(); self.assertEqual(r.released_host_run,r.direct_host_run); self.assertEqual(r.released_host_run.delayed_ids,("J005",))
    def test_release_does_not_force_execution(self): self.assertNotIn("J005",self.release_once().released_host_run.completed_ids)
    def test_no_permit_fails_closed(self):
        r=self.release_once(permit=None); self.assertFalse(r.released); self.assertEqual(r.reason_code,"NO_RELEASE_PERMIT")
    def test_no_grant_fails_closed(self):
        r=self.release_once(grant=None); self.assertFalse(r.released)
    def test_expired_permit_fails_closed(self): self.assertEqual(self.release_once(epoch=202).reason_code,"RELEASE_EPOCH_MISMATCH")
    def test_permit_is_single_use(self):
        first=self.release_once(); second=self.release_once(consumed=first.consumed_release_permit_ids); self.assertFalse(second.released)
    def test_duplicate_consumed_ids_rejected(self):
        with self.assertRaises(ValueError): self.release_once(consumed=(self.permit.permit_id,self.permit.permit_id))
    def test_hold_action_cannot_release(self):
        p=self.rehash_permit(replace(self.permit,action="HOLD")); self.assertEqual(self.release_once(permit=p).reason_code,"NON_RELEASE_ACTION_FORBIDDEN")
    def test_tampered_permit_detected(self):
        self.assertEqual(self.release_once(permit=replace(self.permit,held_job_id="X")).reason_code,"RELEASE_PERMIT_HASH_MISMATCH")
    def test_tampered_grant_detected(self):
        self.assertEqual(self.release_once(grant=replace(self.grant,held_job_id="X")).reason_code,"RELEASE_GRANT_HASH_MISMATCH")
    def test_wrong_hold_permit_binding_rejected(self):
        p=self.rehash_permit(replace(self.permit,hold_permit_hash="a"*64)); self.assertEqual(self.release_once(permit=p).reason_code,"HOLD_PERMIT_BINDING_MISMATCH")
    def test_wrong_hold_mediation_binding_rejected(self):
        p=self.rehash_permit(replace(self.permit,hold_mediation_digest="b"*64)); self.assertEqual(self.release_once(permit=p).reason_code,"HOLD_MEDIATION_BINDING_MISMATCH")
    def test_wrong_evidence_digest_rejected(self):
        p=self.rehash_permit(replace(self.permit,evidence_digest="c"*64)); self.assertEqual(self.release_once(permit=p).reason_code,"HOLD_EVIDENCE_MISMATCH")
    def test_wrong_job_binding_rejected(self):
        p=self.rehash_permit(replace(self.permit,held_job_id="J001")); self.assertEqual(self.release_once(permit=p).reason_code,"HELD_JOB_BINDING_MISMATCH")
    def test_wrong_ordinal_rejected(self):
        p=self.rehash_permit(replace(self.permit,original_ordinal=0)); self.assertEqual(self.release_once(permit=p).reason_code,"ORIGINAL_ORDINAL_INVALID")
    def test_release_grant_is_independent(self):
        self.assertEqual(self.grant.action,"RELEASE"); self.assertNotEqual(self.grant.grant_hash,self.hold.authority_report.grant.grant_hash)
    def test_release_budget_is_one(self): self.assertEqual((self.grant.max_actions,self.permit.max_uses),(1,1))
    def test_receipts_replay(self): self.assertTrue(self.release_once().replay.passed)
    def test_receipt_tamper_detected(self): self.assertFalse(release.replay_receipts(release.tamper_receipt(self.release_once().receipts,2)).passed)
    def test_repeated_run_is_exact(self): self.assertEqual(self.release_once(),self.release_once())
    def test_safe_detach_is_exact_host(self): self.assertEqual(release.ordinary_host.run_jobs(self.jobs),self.release_once().direct_host_run)
    def test_boolean_epoch_rejected(self):
        with self.assertRaises(TypeError): self.release_once(epoch=True)
    def test_authority_requires_one_held_job(self):
        bad=replace(self.hold,held_jobs=());
        with self.assertRaises(ValueError): release.prepare_release_authority(bad,201)
    def test_permit_issuance_rejects_wrong_epoch(self):
        with self.assertRaises(ValueError): release.issue_release_permit(self.hold,self.grant,202)
    def test_release_digest_changes_when_receipt_missing(self):
        r=self.release_once(); shortened=r.receipts[:-1]; self.assertNotEqual(release.replay_receipts(shortened).final_digest,r.replay.final_digest)

if __name__ == "__main__": unittest.main(verbosity=2)

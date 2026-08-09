from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys
import unittest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "integration"
    / "external_host_contract.py"
)
SPEC = importlib.util.spec_from_file_location("bolt_on_v04_stage1_contract", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load Stage 1 module")
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class ExternalHostContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = M.build_reference_profile()
        self.package = M.build_reference_package(self.profile)

    def test_stage_identity(self):
        self.assertEqual(M.STAGE_NAME, "EXTERNAL HOST INTEGRATION CONTRACT")
        self.assertEqual(M.STAGE_VERSION, "0.4.1")
        self.assertEqual(M.MODE, "EXTERNAL_HOST_CONTRACT_DRY_RUN")

    def test_execution_authority_none(self):
        self.assertEqual(M.EXECUTION_AUTHORITY, "NONE")

    def test_frozen_v03_manifest_digest(self):
        self.assertEqual(
            M._sha256_file(M.FROZEN_V03_MANIFEST),
            M.EXPECTED_FROZEN_V03_MANIFEST_SHA256,
        )

    def test_frozen_v03_release_verifies(self):
        passed, reason, count = M.verify_frozen_v03_release()
        self.assertTrue(passed, reason)
        self.assertEqual(reason, "VALID")
        self.assertEqual(count, 20)

    def test_portable_actions_come_from_frozen_v03(self):
        self.assertEqual(M.PORTABLE_ACTIONS, (M.HOLD, M.RELEASE))
        self.assertEqual(M.PORTABLE_ACTIONS, tuple(M.frozen_v03.SUPPORTED_ACTIONS))

    def test_adapter_interface_exact_surface(self):
        self.assertEqual(
            tuple(sorted(M.ExternalIntegrationAdapter.__abstractmethods__)),
            tuple(sorted(M.REQUIRED_ADAPTER_METHODS)),
        )

    def test_structural_authority_scan(self):
        passed, hits = M.structural_authority_scan()
        self.assertTrue(passed)
        self.assertEqual(hits, ())

    def test_reference_profile_valid(self):
        self.assertEqual(M.validate_external_host_profile(self.profile), (True, "VALID"))

    def test_reference_package_valid(self):
        self.assertEqual(M.validate_adapter_package(self.package), (True, "VALID"))

    def test_reference_assessment_compatible(self):
        assessment = M.assess_external_host_contract(self.profile, self.package)
        self.assertTrue(assessment.compatible)
        self.assertEqual(assessment.reason_codes, ())

    def test_reference_assessment_has_no_actions(self):
        assessment = M.assess_external_host_contract(self.profile, self.package)
        self.assertEqual(assessment.host_actions, 0)
        self.assertEqual(assessment.bolt_on_executed_actions, 0)

    def test_reference_assessment_deterministic(self):
        first = M.assess_external_host_contract(self.profile, self.package)
        second = M.assess_external_host_contract(self.profile, self.package)
        self.assertEqual(first, second)

    def test_reference_operation_map(self):
        self.assertEqual(
            dict(self.package.operation_map),
            {M.HOLD: "PAUSE_JOB", M.RELEASE: "RESUME_JOB"},
        )

    def test_reference_permissions_exact(self):
        self.assertEqual(self.package.requested_permissions, tuple(sorted(M.ALLOWED_PERMISSIONS)))

    def test_reference_baseline_clean(self):
        baseline = self.profile.baseline
        self.assertEqual(baseline.applied_operations, 4)
        self.assertEqual(baseline.rejected_operations, 0)
        self.assertEqual(baseline.final_state, "DONE")
        self.assertEqual(baseline.final_version, 4)

    def test_empty_registry_valid(self):
        registry = M.empty_registry()
        self.assertEqual(M.validate_registry(registry), (True, "VALID"))
        self.assertEqual(registry.installed_packages, ())
        self.assertEqual(registry.events, ())

    def test_install_sidecar(self):
        registry = M.install_sidecar(M.empty_registry(), self.profile, self.package)
        self.assertEqual(len(registry.events), 1)
        self.assertEqual(registry.events[0].event_type, M.INSTALL)
        self.assertEqual(registry.installed_packages, (self.package.package_digest,))
        self.assertEqual(M.validate_registry(registry), (True, "VALID"))

    def test_remove_sidecar(self):
        installed = M.install_sidecar(M.empty_registry(), self.profile, self.package)
        removed = M.remove_sidecar(installed, self.profile, self.package)
        self.assertEqual(len(removed.events), 2)
        self.assertEqual(removed.events[-1].event_type, M.REMOVE)
        self.assertEqual(removed.installed_packages, ())
        self.assertEqual(M.validate_registry(removed), (True, "VALID"))

    def test_duplicate_install_rejected(self):
        installed = M.install_sidecar(M.empty_registry(), self.profile, self.package)
        with self.assertRaisesRegex(ValueError, "already installed"):
            M.install_sidecar(installed, self.profile, self.package)

    def test_remove_unknown_rejected(self):
        with self.assertRaisesRegex(ValueError, "not installed"):
            M.remove_sidecar(M.empty_registry(), self.profile, self.package)

    def test_incompatible_install_rejected(self):
        bad = M._rehash(replace(self.package, contains_executor=True), "package_digest")
        with self.assertRaisesRegex(ValueError, "ADAPTER_CONTAINS_EXECUTOR"):
            M.install_sidecar(M.empty_registry(), self.profile, bad)

    def test_registry_chain_tamper_detected(self):
        installed = M.install_sidecar(M.empty_registry(), self.profile, self.package)
        event = replace(installed.events[0], baseline_digest="f" * 64)
        tampered = replace(installed, events=(event,))
        self.assertFalse(M.validate_registry(tampered)[0])

    def test_registry_reorder_detected(self):
        installed = M.install_sidecar(M.empty_registry(), self.profile, self.package)
        removed = M.remove_sidecar(installed, self.profile, self.package)
        reordered = replace(removed, events=tuple(reversed(removed.events)))
        self.assertFalse(M.validate_registry(reordered)[0])

    def _valid_receipts(self):
        assessment = M.assess_external_host_contract(self.profile, self.package)
        r0 = M.empty_registry()
        r1 = M.install_sidecar(r0, self.profile, self.package)
        r2 = M.remove_sidecar(r1, self.profile, self.package)
        receipts = ()
        receipts = M.append_receipt(receipts, "ASSESSMENT", self.package.package_id, assessment.unsigned_record())
        receipts = M.append_receipt(receipts, "INSTALL", r1.registry_id, r1.events[-1].unsigned_record())
        receipts = M.append_receipt(receipts, "NEUTRALITY", "INSTALL", {
            "baseline_before": self.profile.baseline.baseline_digest,
            "baseline_after": self.profile.baseline.baseline_digest,
        })
        receipts = M.append_receipt(receipts, "REMOVE", r2.registry_id, r2.events[-1].unsigned_record())
        receipts = M.append_receipt(receipts, "NEUTRALITY", "REMOVE", {
            "baseline_before": self.profile.baseline.baseline_digest,
            "baseline_after": self.profile.baseline.baseline_digest,
        })
        receipts = M.append_receipt(receipts, "SUMMARY", "STAGE-1", {
            "compatible": True,
            "installed_count": 0,
            "host_state_changes": 0,
            "host_actions": 0,
            "bolt_on_executed_actions": 0,
        })
        return receipts

    def test_receipt_replay(self):
        replay = M.replay_receipts(self._valid_receipts())
        self.assertTrue(replay.passed, replay.first_error)
        self.assertEqual(replay.installed_count, 0)
        self.assertEqual(replay.host_state_changes, 0)

    def test_receipt_hash_tamper_detected(self):
        receipts = list(self._valid_receipts())
        receipts[0] = replace(receipts[0], payload="{}")
        self.assertFalse(M.replay_receipts(receipts).passed)

    def test_receipt_reorder_detected(self):
        receipts = list(self._valid_receipts())
        receipts[1], receipts[2] = receipts[2], receipts[1]
        self.assertFalse(M.replay_receipts(receipts).passed)

    def test_rehashed_summary_forgery_detected(self):
        receipts = list(self._valid_receipts())
        summary = receipts[-1]
        forged_payload = json.dumps(
            {
                "compatible": True,
                "installed_count": 0,
                "host_state_changes": 0,
                "host_actions": 1,
                "bolt_on_executed_actions": 0,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        record = {
            "kind": summary.kind,
            "payload": forged_payload,
            "prior_hash": summary.prior_hash,
            "receipt_id": summary.receipt_id,
            "subject": summary.subject,
        }
        receipts[-1] = replace(
            summary,
            payload=forged_payload,
            receipt_hash=M._digest_json(record),
        )
        replay = M.replay_receipts(receipts)
        self.assertFalse(replay.passed)
        self.assertEqual(replay.first_error, "SUMMARY_SEMANTIC_INVALID")

    def test_profile_type_rejected(self):
        self.assertEqual(
            M.validate_external_host_profile(object()),
            (False, "HOST_PROFILE_TYPE_INVALID"),
        )

    def test_package_type_rejected(self):
        self.assertEqual(
            M.validate_adapter_package(object()),
            (False, "ADAPTER_PACKAGE_TYPE_INVALID"),
        )

    def test_duplicate_allowed_operation_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            M.build_command_boundary(
                boundary_id="X",
                owner="HOST",
                transport="LOCAL_COMMAND_API",
                allowed_operations=("PAUSE", "PAUSE"),
                requires_exact_subject=True,
                requires_expected_version=True,
                requires_idempotency_key=True,
                requires_authorization_token=True,
                adapter_receives_callable=False,
                wildcard_operations=False,
            )

    def test_duplicate_operation_map_key_rejected(self):
        with self.assertRaisesRegex(ValueError, "keys must be unique"):
            M.build_adapter_package(
                package_id="X",
                package_version="1",
                target_host_identity_digest=self.profile.identity.identity_digest,
                portable_actions=M.PORTABLE_ACTIONS,
                operation_map=((M.HOLD, "A"), (M.HOLD, "B")),
                state_map=(("A", "B"), ("C", "D")),
                requested_permissions=M.ALLOWED_PERMISSIONS,
                exported_methods=M.REQUIRED_ADAPTER_METHODS,
            )

    def test_exact_integer_rejects_bool(self):
        with self.assertRaises(TypeError):
            M._exact_int(True, "value")

    def test_registry_type_rejected(self):
        self.assertEqual(M.validate_registry(object()), (False, "REGISTRY_TYPE_INVALID"))

    def test_insufficient_state_map_rejected(self):
        bad = M._rehash(replace(self.package, state_map=(("RUNNING", "ACTIVE"),)), "package_digest")
        assessment = M.assess_external_host_contract(self.profile, bad)
        self.assertIn("STATE_MAP_INSUFFICIENT", assessment.reason_codes)

    def test_unsupported_deployment_rejected(self):
        identity = M._rehash(replace(self.profile.identity, deployment_kind="REMOTE_MAGIC"), "identity_digest")
        bad_profile = M.build_external_host_profile(identity, self.profile.observation, self.profile.command_boundary, self.profile.lifecycle, self.profile.baseline)
        self.assertIn("DEPLOYMENT_KIND_UNSUPPORTED", M.assess_external_host_contract(bad_profile, self.package).reason_codes)

    def test_idempotency_unbound_rejected(self):
        boundary = M._rehash(replace(self.profile.command_boundary, requires_idempotency_key=False), "boundary_digest")
        bad_profile = M.build_external_host_profile(self.profile.identity, self.profile.observation, boundary, self.profile.lifecycle, self.profile.baseline)
        self.assertIn("COMMAND_IDEMPOTENCY_UNBOUND", M.assess_external_host_contract(bad_profile, self.package).reason_codes)

    def test_exact_subject_unbound_rejected(self):
        boundary = M._rehash(replace(self.profile.command_boundary, requires_exact_subject=False), "boundary_digest")
        bad_profile = M.build_external_host_profile(self.profile.identity, self.profile.observation, boundary, self.profile.lifecycle, self.profile.baseline)
        self.assertIn("COMMAND_SUBJECT_NOT_EXACT", M.assess_external_host_contract(bad_profile, self.package).reason_codes)

    def test_environment_mutation_rejected(self):
        lifecycle = M._rehash(replace(self.profile.lifecycle, environment_mutation_required=True), "lifecycle_digest")
        bad_profile = M.build_external_host_profile(self.profile.identity, self.profile.observation, self.profile.command_boundary, lifecycle, self.profile.baseline)
        self.assertIn("HOST_ENVIRONMENT_MUTATION_REQUIRED", M.assess_external_host_contract(bad_profile, self.package).reason_codes)

    def test_stage1_qualification_passes(self):
        qualification = M.run_stage1_qualification()
        self.assertTrue(qualification.passed)

    def test_stage1_counts(self):
        qualification = M.run_stage1_qualification()
        self.assertEqual(qualification.contract_requirements, 37)
        self.assertEqual(qualification.rejection_cases, 28)
        self.assertEqual(qualification.rejection_cases_safely_rejected, 28)
        self.assertEqual(qualification.install_registrations, 1)
        self.assertEqual(qualification.remove_registrations, 1)

    def test_stage1_zero_action_invariants(self):
        qualification = M.run_stage1_qualification()
        self.assertEqual(qualification.host_state_changes, 0)
        self.assertEqual(qualification.host_actions, 0)
        self.assertEqual(qualification.bolt_on_executed_actions, 0)

    def test_stage1_receipt_replay_digest_matches(self):
        qualification = M.run_stage1_qualification()
        self.assertEqual(qualification.receipt_digest, qualification.replay_digest)

    def test_stage1_preserves_frozen_v03(self):
        qualification = M.run_stage1_qualification()
        self.assertTrue(qualification.frozen_v03_pre_pass)
        self.assertTrue(qualification.frozen_v03_post_pass)
        self.assertTrue(qualification.frozen_v03_unchanged)

    def test_stage1_preserves_source(self):
        self.assertTrue(M.run_stage1_qualification().source_unchanged)

    def test_stage1_registry_empty_after_remove(self):
        self.assertTrue(M.run_stage1_qualification().registry_empty_after_remove)


# Each adversarial contract case receives its own independently named test.
def _make_rejection_test(case_index: int):
    def test(self):
        cases = M.rejection_cases(self.profile, self.package)
        case_id, expected, candidate_profile, candidate_package = cases[case_index]
        assessment = M.assess_external_host_contract(candidate_profile, candidate_package)
        self.assertFalse(assessment.compatible, case_id)
        self.assertIn(expected, assessment.reason_codes, case_id)
        self.assertEqual(assessment.host_actions, 0, case_id)
        self.assertEqual(assessment.bolt_on_executed_actions, 0, case_id)
        self.assertEqual(self.profile.baseline.baseline_digest, M.build_reference_profile().baseline.baseline_digest)
    return test


for _index in range(28):
    setattr(
        ExternalHostContractTests,
        f"test_rejection_case_{_index + 1:02d}",
        _make_rejection_test(_index),
    )


if __name__ == "__main__":
    unittest.main()

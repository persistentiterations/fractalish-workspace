"""
PIA pilot success-requirements tests.

These tests intentionally validate the bounded pilot claim only.  They do not
claim production model-host portability, durable identity, or consciousness.
"""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.cognitive_basin.pia import (
    ConditionBlindStateAccessController,
    ContinuityBundle,
    ContradictionObservation,
    DeterministicPilotHost,
    FormationAuthority,
    FormationService,
    HostStateStore,
    PIAValidationError,
    PIAGuardedExecutor,
    commit_blinded_fixture,
    validate_formed_history,
    validate_pia_run_receipt,
    validate_typed_route_distribution,
    verify_fixture_steward_record,
)
from python.cognitive_basin.pia.pilot import build_typed_route_distribution, digest_payload


def _authority() -> FormationAuthority:
    return FormationAuthority("pia-test-authority", "local-test-secret")


def _formed_history():
    authority = _authority()
    service = FormationService(authority)
    observations = [
        ContradictionObservation(
            "obs-1",
            "routing-corridor",
            "safe",
            "The routing corridor was described as safe.",
            "evidence:review-note-1",
            1,
            "human-local-review",
            "pilot",
        ),
        ContradictionObservation(
            "obs-2",
            "routing-corridor",
            "unsafe",
            "Later review flagged the same routing corridor as unsafe.",
            "evidence:review-note-2",
            2,
            "human-local-review",
            "pilot",
        ),
    ]
    return authority, service.form_contradiction_history(observations, scope="pilot")


def _resign_history_record(record: dict, authority: FormationAuthority) -> dict:
    unsigned = {
        "schema_version": record["schema_version"],
        "history_id": record["history_id"],
        "claim_key": record["claim_key"],
        "conflicting_observations": record["conflicting_observations"],
        "resolution_status": record["resolution_status"],
        "confidence": record["confidence"],
        "provenance_refs": record["provenance_refs"],
        "scope": record["scope"],
        "eligibility": record["eligibility"],
        "created_sequence": record["created_sequence"],
        "formation_policy_id": record["formation_policy_id"],
    }
    record["content_digest"] = digest_payload(unsigned)
    record["lineage_digest"] = digest_payload(
        {
            "formation_policy_id": record["formation_policy_id"],
            "observations": record["conflicting_observations"],
            "scope": record["scope"],
        }
    )
    record["formation_signature"] = authority.sign(
        {
            "schema_version": record["schema_version"],
            "formation_policy_id": record["formation_policy_id"],
            "scope": record["scope"],
            "content_digest": record["content_digest"],
            "lineage_digest": record["lineage_digest"],
            "authority_key_id": record["authority_key_id"],
        }
    )
    return record


def _resign_import_receipt(record: dict, authority: FormationAuthority) -> dict:
    unsigned = {
        "schema_version": record["schema_version"],
        "destination_host_id": record["destination_host_id"],
        "destination_model_id": record["destination_model_id"],
        "source_host_id": record["source_host_id"],
        "source_model_id": record["source_model_id"],
        "bundle_id": record["bundle_id"],
        "export_digest": record["export_digest"],
        "stored_content_digest": record["stored_content_digest"],
        "controller_config_digest": record["controller_config_digest"],
        "status": record["status"],
    }
    record["import_receipt_digest"] = digest_payload(unsigned)
    record["authority_key_id"] = authority.key_id
    record["import_signature"] = authority.sign(
        {
            "schema_version": record["schema_version"],
            "destination_host_id": record["destination_host_id"],
            "destination_model_id": record["destination_model_id"],
            "source_host_id": record["source_host_id"],
            "source_model_id": record["source_model_id"],
            "bundle_id": record["bundle_id"],
            "export_digest": record["export_digest"],
            "stored_content_digest": record["stored_content_digest"],
            "import_receipt_digest": record["import_receipt_digest"],
            "authority_key_id": record["authority_key_id"],
        }
    )
    return record


def test_governed_formation_rejects_forged_or_directive_history():
    authority, formed = _formed_history()
    accepted = validate_formed_history(formed.to_record(), authority)
    assert accepted.history_id == formed.history_id
    assert "selected_route" not in formed.to_record()

    tampered = formed.to_record()
    tampered["conflicting_observations"][0]["statement"] = "rewritten after signing"
    with pytest.raises(PIAValidationError, match="digest mismatch"):
        validate_formed_history(tampered, authority)

    directive = formed.to_record()
    directive["expected_route"] = "preserve_and_review"
    with pytest.raises(PIAValidationError, match="directive field"):
        validate_formed_history(directive, authority)

    service = FormationService(authority)
    with pytest.raises(PIAValidationError, match="evidence_ref"):
        service.form_contradiction_history(
            [
                ContradictionObservation("o1", "claim", "yes", "yes", "", 1, "test", "pilot"),
                ContradictionObservation("o2", "claim", "no", "no", "evidence:2", 2, "test", "pilot"),
            ],
            scope="pilot",
        )
    with pytest.raises(PIAValidationError, match="directive value"):
        service.form_contradiction_history(
            [
                ContradictionObservation("o1", "claim", "yes", "expected_route: release", "evidence:1", 1, "test", "pilot"),
                ContradictionObservation("o2", "claim", "no", "no", "evidence:2", 2, "test", "pilot"),
            ],
            scope="pilot",
        )


def test_condition_blind_controller_exposes_only_valid_eligible_state():
    authority, formed = _formed_history()
    controller = ConditionBlindStateAccessController(authority)
    decision = controller.select([formed.to_record()], purpose="routing", scope="pilot")

    assert decision.selected_history_ids == [formed.history_id]
    assert decision.selected_content_digests == [formed.content_digest]
    assert decision.controller_config_digest.startswith("sha256:")

    leaked = formed.to_record()
    leaked["metadata"] = {"condition_id": "treatment", "expected_outcome": "preserve"}
    with pytest.raises(PIAValidationError, match="directive field"):
        controller.select([leaked], purpose="routing", scope="pilot")

    wrong_scope = formed.to_record()
    wrong_scope["scope"] = "other"
    wrong_scope = _resign_history_record(wrong_scope, authority)
    assert controller.select([wrong_scope], purpose="routing", scope="pilot").selected_history_ids == []

    ineligible = formed.to_record()
    ineligible["eligibility"] = "ineligible"
    ineligible = _resign_history_record(ineligible, authority)
    assert controller.select([ineligible], purpose="routing", scope="pilot").selected_history_ids == []


def test_continuity_bundle_imports_into_clean_host_b_namespace():
    authority, formed = _formed_history()
    controller = ConditionBlindStateAccessController(authority)
    host_a_state = HostStateStore("host-a", "model-a")
    host_a_receipt = host_a_state.store_formed_history(formed, authority=authority)
    bundle = ContinuityBundle.export(
        formed,
        authority=authority,
        source_host_id="host-a",
        source_model_id="model-a",
        source_state_receipt=host_a_receipt,
        destination_scope="pilot",
    )
    host_b_state = HostStateStore("host-b", "model-b")
    assert host_b_state.namespace == {}

    receipt = host_b_state.import_bundle(
        bundle.to_record(),
        authority=authority,
        controller=controller,
        purpose="routing",
    )
    assert receipt["source_host_id"] == "host-a"
    assert receipt["destination_host_id"] == "host-b"
    assert receipt["stored_content_digest"] == formed.content_digest
    assert list(host_b_state.namespace) == [formed.content_digest]

    tampered = bundle.to_record()
    tampered["formed_history"]["scope"] = "wrong"
    with pytest.raises(PIAValidationError):
        HostStateStore("host-b2", "model-b").import_bundle(
            tampered,
            authority=authority,
            controller=controller,
            purpose="routing",
        )

    forged_export = bundle.to_record()
    forged_export["export_signature"] = "hmac-sha256:" + "0" * 64
    with pytest.raises(PIAValidationError, match="signature"):
        HostStateStore("host-b3", "model-b").import_bundle(
            forged_export,
            authority=authority,
            controller=controller,
            purpose="routing",
        )


def test_blinded_fixtures_and_typed_route_distributions_are_complete():
    fixture, steward = commit_blinded_fixture(
        "fixture-opaque-1",
        "Resolve the current continuity-risk route without seeing the expected answer.",
        {"expected_route": "preserve_and_review"},
    )
    runtime_record = fixture.to_runtime_record()
    assert "expected_route" not in str(runtime_record)
    assert steward["expected_analysis"]["expected_route"] == "preserve_and_review"
    verification = verify_fixture_steward_record(fixture, steward, authority=_authority())
    assert verification["verified"] is True
    assert verification["verification_signature"].startswith("hmac-sha256:")

    tampered_steward = copy.deepcopy(steward)
    tampered_steward["expected_analysis"]["expected_route"] = "hold_for_authority"
    with pytest.raises(PIAValidationError, match="expected commitment|steward record digest"):
        verify_fixture_steward_record(fixture, tampered_steward, authority=_authority())

    host = DeterministicPilotHost("host-b", "model-b", route_bias="preserve_and_review")
    inference = host.infer(fixture, [])
    distribution = build_typed_route_distribution(inference, [])
    accepted = validate_typed_route_distribution(distribution.to_record())
    assert accepted.selected_route in {"preserve_and_review", "release_with_caveat", "hold_for_authority"}
    assert {support.route_id for support in accepted.supports} == set(accepted.route_vocabulary)

    incomplete = distribution.to_record()
    incomplete["supports"] = incomplete["supports"][:-1]
    with pytest.raises(PIAValidationError, match="every declared route"):
        validate_typed_route_distribution(incomplete)

    wrong_path = distribution.to_record()
    wrong_path["supports"][0]["selected_path"] = "routes/not-declared"
    with pytest.raises(PIAValidationError, match="selected_path"):
        validate_typed_route_distribution(wrong_path)


def test_guarded_execution_receipt_binds_host_substitution_and_blocks_bypass():
    authority, formed = _formed_history()
    controller = ConditionBlindStateAccessController(authority)
    host_a_state = HostStateStore("host-a", "model-a")
    host_a_receipt = host_a_state.store_formed_history(formed, authority=authority)
    bundle = ContinuityBundle.export(
        formed,
        authority=authority,
        source_host_id="host-a",
        source_model_id="model-a",
        source_state_receipt=host_a_receipt,
        destination_scope="pilot",
    )
    host_b = DeterministicPilotHost("host-b", "model-b", route_bias="preserve_and_review")
    host_b_state = HostStateStore("host-b", "model-b")
    host_b_state.import_bundle(bundle.to_record(), authority=authority, controller=controller, purpose="routing")
    fixture, _steward = commit_blinded_fixture(
        "fixture-opaque-2",
        "Choose the bounded continuity route.",
        {"expected_route": "preserve_and_review"},
    )

    receipt = PIAGuardedExecutor(authority).run_trial(
        fixture=fixture,
        host_b=host_b,
        host_b_state=host_b_state,
        controller=controller,
        purpose="routing",
        scope="pilot",
        source_host_id="host-a",
        source_model_id="model-a",
        run_id="pia-run-test-1",
    )
    accepted = validate_pia_run_receipt(receipt.to_record(), authority)
    assert accepted.source_host_id == "host-a"
    assert accepted.destination_host_id == "host-b"
    assert accepted.source_model_id == "model-a"
    assert accepted.destination_model_id == "model-b"
    assert accepted.host_substitution_level == "deterministic-pilot-model-host-substitution"
    assert accepted.pilot_claim_status == "DETERMINISTIC_HARNESS_VERIFIED"
    assert accepted.route_distribution["supports"]

    lower_layer_only = receipt.route_distribution
    with pytest.raises(PIAValidationError, match="missing fields"):
        validate_pia_run_receipt(lower_layer_only, authority)

    forged = copy.deepcopy(receipt.to_record())
    forged["authorization"]["authorization_signature"] = "hmac-sha256:" + "0" * 64
    with pytest.raises(PIAValidationError, match="output commitment|authorization signature"):
        validate_pia_run_receipt(forged, authority)

    empty_state = copy.deepcopy(receipt.to_record())
    empty_state["imported_state_digests"] = []
    with pytest.raises(PIAValidationError, match="at least one imported state"):
        validate_pia_run_receipt(empty_state, authority)

    mismatched_import = copy.deepcopy(receipt.to_record())
    mismatched_import["host_b_import_receipts"][0]["source_host_id"] = "other-host"
    _resign_import_receipt(mismatched_import["host_b_import_receipts"][0], authority)
    with pytest.raises(PIAValidationError, match="source and destination"):
        validate_pia_run_receipt(mismatched_import, authority)

    split_import_evidence = copy.deepcopy(receipt.to_record())
    valid_import = split_import_evidence["host_b_import_receipts"][0]
    identity_only_import = copy.deepcopy(valid_import)
    identity_only_import["stored_content_digest"] = "sha256:" + "0" * 64
    _resign_import_receipt(identity_only_import, authority)
    digest_only_import = copy.deepcopy(valid_import)
    digest_only_import["source_host_id"] = "other-host"
    _resign_import_receipt(digest_only_import, authority)
    split_import_evidence["host_b_import_receipts"] = [identity_only_import, digest_only_import]
    with pytest.raises(PIAValidationError, match="imported state digest and source and destination"):
        validate_pia_run_receipt(split_import_evidence, authority)

    wrong_inference_identity = copy.deepcopy(receipt.to_record())
    wrong_inference_identity["inference"]["host_id"] = "host-not-b"
    with pytest.raises(PIAValidationError, match="inference identity"):
        validate_pia_run_receipt(wrong_inference_identity, authority)

    stale_output_commitment = copy.deepcopy(receipt.to_record())
    stale_output_commitment["output_commitment"] = "sha256:" + "0" * 64
    with pytest.raises(PIAValidationError, match="output commitment"):
        validate_pia_run_receipt(stale_output_commitment, authority)

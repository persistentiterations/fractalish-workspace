"""
Deterministic PIA pilot acceptance runner.

The runner writes retained evidence artifacts for the bounded PIA checklist.
It intentionally labels deterministic-host evidence separately from live
model-host evidence.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from .pilot import (
    ConditionBlindStateAccessController,
    ContinuityBundle,
    ContradictionObservation,
    DeterministicPilotHost,
    FormationAuthority,
    FormationService,
    HostStateStore,
    PIAGuardedExecutor,
    commit_blinded_fixture,
    validate_formed_history,
    validate_pia_run_receipt,
    validate_typed_route_distribution,
    verify_fixture_steward_record,
)


ROOT = Path(__file__).resolve().parents[3]


def _current_commit() -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _write_json(root: Path, name: str, payload: Dict[str, Any]) -> str:
    path = root / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(path)


def _assert_scenario(results: List[Dict[str, Any]], scenario: str, passed: bool, **details: Any) -> None:
    results.append({"scenario": scenario, "passed": passed, **details})


def _fixture_observations() -> List[ContradictionObservation]:
    return [
        ContradictionObservation(
            observation_id="pia-obs-a",
            claim_key="continuity-route",
            asserted_value="release",
            statement="Initial route notes allowed release after a lightweight check.",
            evidence_ref="evidence:pia-source-observation-a",
            sequence=1,
            provenance="human-local-review",
            scope="pilot",
        ),
        ContradictionObservation(
            observation_id="pia-obs-b",
            claim_key="continuity-route",
            asserted_value="hold",
            statement="Later route notes identified unresolved authority and contradiction risk.",
            evidence_ref="evidence:pia-source-observation-b",
            sequence=2,
            provenance="human-local-review",
            scope="pilot",
        ),
    ]


def run_acceptance_suite(artifact_dir: str | Path | None = None) -> Dict[str, Any]:
    started = time.time()
    artifact_root = Path(artifact_dir) if artifact_dir else None
    if artifact_root:
        artifact_root.mkdir(parents=True, exist_ok=True)

    authority = FormationAuthority("pia-pilot-authority-v0.1", "deterministic-local-pilot-secret")
    formation_service = FormationService(authority)
    controller = ConditionBlindStateAccessController(authority)
    results: List[Dict[str, Any]] = []

    formed = formation_service.form_contradiction_history(_fixture_observations(), scope="pilot")
    formed_record = formed.to_record()
    _assert_scenario(
        results,
        "governed contradiction-history formation",
        validate_formed_history(formed_record, authority).history_id == formed.history_id,
        history_id=formed.history_id,
        content_digest=formed.content_digest,
    )

    directive_free = not any(key in json.dumps(formed_record) for key in ["selected_route", "expected_route", "fixture_outcome"])
    _assert_scenario(results, "non-directive formed-history object", directive_free, history_id=formed.history_id)

    host_a_state = HostStateStore("pia-host-a", "pia-model-a")
    host_a_state_receipt = host_a_state.store_formed_history(formed, authority=authority)
    _assert_scenario(
        results,
        "Host A source state namespace",
        formed.content_digest in host_a_state.namespace and host_a_state_receipt["status"] == "STORED",
        host_a_state_receipt=host_a_state_receipt,
    )

    continuity_bundle = ContinuityBundle.export(
        formed,
        authority=authority,
        source_host_id=host_a_state.host_id,
        source_model_id=host_a_state.model_id,
        source_state_receipt=host_a_state_receipt,
        destination_scope="pilot",
    )
    host_b = DeterministicPilotHost("pia-host-b", "pia-model-b", route_bias="preserve_and_review")
    host_b_state = HostStateStore(host_b.host_id, host_b.model_id)
    import_receipt = host_b_state.import_bundle(
        continuity_bundle.to_record(),
        authority=authority,
        controller=controller,
        purpose="routing",
    )
    _assert_scenario(
        results,
        "Host B continuity-state import",
        import_receipt["status"] == "IMPORTED_AND_CONTROLLER_VISIBLE"
        and import_receipt["destination_host_id"] == "pia-host-b",
        import_receipt=import_receipt,
    )

    fixture, steward_record = commit_blinded_fixture(
        "pia-fixture-opaque-001",
        "Select a bounded continuity route from the visible formed history only.",
        {"expected_route": "preserve_and_review", "steward_note": "withheld until outputs are committed"},
    )
    runtime_fixture = fixture.to_runtime_record()
    steward_verification = verify_fixture_steward_record(fixture, steward_record, authority=authority)
    _assert_scenario(
        results,
        "blinded final fixture runtime record",
        "expected_route" not in json.dumps(runtime_fixture),
        fixture_commitment=fixture.fixture_commitment,
        steward_record_digest=fixture.steward_record_digest,
    )
    _assert_scenario(
        results,
        "blinded fixture steward seal verification",
        steward_verification["verified"] is True
        and steward_verification["steward_record_digest"] == fixture.steward_record_digest
        and steward_verification["verification_signature"].startswith("hmac-sha256:"),
        steward_verification_digest=steward_verification["steward_verification_digest"],
    )

    executor = PIAGuardedExecutor(authority)
    receipt = executor.run_trial(
        fixture=fixture,
        host_b=host_b,
        host_b_state=host_b_state,
        controller=controller,
        purpose="routing",
        scope="pilot",
        source_host_id="pia-host-a",
        source_model_id="pia-model-a",
        run_id="pia-run-deterministic-001",
    )
    receipt_record = receipt.to_record()
    validated_receipt = validate_pia_run_receipt(receipt_record, authority)
    route_distribution = validate_typed_route_distribution(receipt.route_distribution)

    _assert_scenario(
        results,
        "typed route distribution",
        len(route_distribution.supports) == len(route_distribution.route_vocabulary)
        and abs(sum(item.support for item in route_distribution.supports) - 1.0) < 0.00001,
        selected_route=route_distribution.selected_route,
        distribution_digest=route_distribution.distribution_digest,
    )
    _assert_scenario(
        results,
        "actual Host A to Host B substitution record",
        validated_receipt.source_host_id != validated_receipt.destination_host_id
        and validated_receipt.source_model_id != validated_receipt.destination_model_id
        and validated_receipt.inference["fresh_inference"] is True,
        host_substitution_level=validated_receipt.host_substitution_level,
        pilot_claim_status=validated_receipt.pilot_claim_status,
    )
    _assert_scenario(
        results,
        "guarded execution receipt",
        validated_receipt.authorization["guard_policy_id"] == "pia.guarded-execution.v0.1"
        and validated_receipt.receipt_signature.startswith("hmac-sha256:"),
        output_commitment=validated_receipt.output_commitment,
    )

    tamper_error = ""
    tampered = json.loads(json.dumps(receipt_record))
    tampered["route_distribution"]["selected_route"] = "hold_for_authority"
    try:
        validate_pia_run_receipt(tampered, authority)
    except ValueError as exc:
        tamper_error = str(exc)
    _assert_scenario(results, "tampered guarded receipt rejection", bool(tamper_error), error=tamper_error)

    bypass_error = ""
    try:
        validate_pia_run_receipt(receipt.route_distribution, authority)
    except ValueError as exc:
        bypass_error = str(exc)
    _assert_scenario(results, "lower-layer bypass cannot validate as PIA success", bool(bypass_error), error=bypass_error)

    artifacts = {
        "formed_history": "",
        "host_a_state_receipt": "",
        "continuity_bundle": "",
        "host_b_import_receipt": "",
        "blinded_fixture_runtime": "",
        "fixture_steward_record": "",
        "fixture_steward_verification": "",
        "route_distribution": "",
        "guarded_run_receipt": "",
        "summary": "",
    }
    if artifact_root:
        private_root = artifact_root / "private"
        private_root.mkdir(parents=True, exist_ok=True)
        artifacts["formed_history"] = _write_json(artifact_root, "formed-history.json", formed_record)
        artifacts["host_a_state_receipt"] = _write_json(artifact_root, "host-a-state-receipt.json", host_a_state_receipt)
        artifacts["continuity_bundle"] = _write_json(artifact_root, "continuity-bundle.json", continuity_bundle.to_record())
        artifacts["host_b_import_receipt"] = _write_json(artifact_root, "host-b-import-receipt.json", import_receipt)
        artifacts["blinded_fixture_runtime"] = _write_json(artifact_root, "blinded-fixture-runtime.json", runtime_fixture)
        artifacts["fixture_steward_record"] = _write_json(private_root, "fixture-steward-record-private.json", steward_record)
        artifacts["fixture_steward_verification"] = _write_json(artifact_root, "fixture-steward-verification.json", steward_verification)
        artifacts["route_distribution"] = _write_json(artifact_root, "typed-route-distribution.json", receipt.route_distribution)
        artifacts["guarded_run_receipt"] = _write_json(artifact_root, "guarded-run-receipt.json", receipt_record)

    summary = {
        "passed": all(item["passed"] for item in results),
        "scenario_count": len(results),
        "results": results,
        "exact_commit": _current_commit(),
        "artifacts": artifacts,
        "pilot_claim_status": receipt.pilot_claim_status,
        "host_substitution_level": receipt.host_substitution_level,
        "limitations": receipt.limitations,
        "elapsed_s": round(time.time() - started, 3),
    }
    if artifact_root:
        artifacts["summary"] = _write_json(artifact_root, "pia-pilot-acceptance-summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--artifact-dir", default="")
    args = parser.parse_args()
    if not args.all:
        parser.error("Only --all is currently supported")
    summary = run_acceptance_suite(args.artifact_dir or None)
    print(f"PIA pilot acceptance: commit={summary['exact_commit']} scenarios={summary['scenario_count']} passed={summary['passed']}")
    for result in summary["results"]:
        print(f"- {result['scenario']}: {'PASS' if result['passed'] else 'FAIL'}")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

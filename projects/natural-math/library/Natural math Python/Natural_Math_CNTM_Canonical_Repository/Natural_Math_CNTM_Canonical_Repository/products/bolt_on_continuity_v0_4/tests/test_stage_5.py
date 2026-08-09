import json

from bolt_on_v0_4.stage_3 import canonical_bytes
from bolt_on_v0_4.stage_4 import AUTHORITY as STAGE_4_AUTHORITY
from bolt_on_v0_4.stage_4 import CanonicalConfiguration, sha256
from bolt_on_v0_4.stage_5 import AUTHORITY, COMMANDS, SAFETY, execute


def valid_configuration() -> CanonicalConfiguration:
    base = {
        "action_vocabulary": ["NO_ACTION", "HOLD", "RELEASE"],
        "authority": dict(STAGE_4_AUTHORITY),
        "mode": {"approval_required": True, "autonomous_actions": False, "gateway_enabled": False, "observation_only": True},
        "product": "Bolt-On Continuity v0.4",
        "qualified_stage_3_head": "c6aa6590b46e802b1e59d05f3af94c2ce9ed58a0",
        "retention": {"maximum_incidents": 1000, "mode": "retain_until_operator_deletes"},
        "schema_version": 1,
        "stage": 4,
        "stage_3_qualification_record_sha256": "1715c97822c5639b4850a46f28f5620b09c19a981e1b32e93ecb4f9bbc741bf0",
        "stage_3_verifier_manifest_sha256": "f68cee14b5c47572e84b839cd2b2917f7c2c3f706bc87a7f83c0937b5e5fdbc9",
        "storage": {"data_directory": "data/bolt-on-continuity", "maximum_receipt_bytes_per_incident": 1048576, "persistence_authorized": False},
        "subject": {"container_id": "a" * 64, "display_name": "alpha", "image": "alpine:3.20", "platform": "linux"},
    }
    return CanonicalConfiguration({**base, "configuration_digest": sha256(canonical_bytes(base))})


def run(command: str):
    return execute(command, valid_configuration().canonical_bytes()).body()


def test_commands_exact():
    assert COMMANDS == {"config-check", "status", "start", "stop"}


def test_config_check_accepts():
    assert run("config-check")["accepted"] is True


def test_config_check_state():
    assert run("config-check")["lifecycle_state"] == "NOT_STARTED"


def test_status_not_started():
    assert run("status")["reason_code"] == "RUNTIME_NOT_STARTED"


def test_start_plan_ready():
    assert run("start")["lifecycle_state"] == "OBSERVATION_PLAN_READY"


def test_start_not_executed():
    assert run("start")["plan"]["execution_performed"] is False


def test_start_not_persisted():
    assert run("start")["plan"]["persistence_performed"] is False


def test_stop_plan_ready():
    assert run("stop")["lifecycle_state"] == "STOP_PLAN_READY"


def test_stop_container_independent():
    assert run("stop")["plan"]["monitored_container_remains_independently_operable"] is True


def test_stop_not_mutated():
    assert run("stop")["plan"]["container_mutated"] is False


def test_safety_exact():
    assert run("start")["safety"] == SAFETY


def test_authority_exact():
    assert run("start")["authority"] == AUTHORITY


def test_only_planning_authorities_true():
    assert {key for key, value in AUTHORITY.items() if value} == {"stage_4_configuration_consumption", "configuration_validation", "lifecycle_plan_construction"}


def test_subject_preserved():
    assert run("status")["subject_container_id"] == "a" * 64


def test_configuration_digest_preserved():
    assert run("status")["configuration_digest"] == valid_configuration().configuration_digest


def test_result_digest_valid():
    body = run("start")
    digest = body.pop("result_digest")
    assert digest == sha256(canonical_bytes(body))


def test_deterministic():
    assert execute("start", valid_configuration().canonical_bytes()).canonical_bytes() == execute("start", valid_configuration().canonical_bytes()).canonical_bytes()


def test_unknown_command_rejected():
    body = execute("launch", valid_configuration().canonical_bytes()).body()
    assert body["accepted"] is False and body["reason_code"] == "UNKNOWN_COMMAND"


def test_malformed_rejected():
    assert execute("start", b"not-json").body()["reason_code"] == "CONFIGURATION_INVALID"


def test_digest_alteration_rejected_even_when_json_formatted():
    raw = json.loads(valid_configuration().canonical_bytes())
    raw["configuration_digest"] = "0" * 64
    expanded = json.dumps(raw, indent=2).encode("utf-8")
    assert execute("start", expanded).body()["accepted"] is False

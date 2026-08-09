import json

from bolt_on.configuration_stage4 import build_configuration
from bolt_on.discovery import EnrollmentRecord
from bolt_on.lifecycle_stage5 import SAFETY, execute
from bolt_on.receipts import canonical_json_bytes

CID = "a" * 64


def config_bytes() -> bytes:
    base = {
        "container_id": CID,
        "contract": "bolt-on-continuity-v0.3-stage-3",
        "display_name": "demo",
        "gateway_enabled": False,
        "image": "example:1",
        "observation_only": True,
        "observed_state": "running",
        "schema_version": 1,
    }
    import hashlib
    record = EnrollmentRecord(CID, "demo", "example:1", "running", hashlib.sha256(canonical_json_bytes(base)).hexdigest())
    return build_configuration(record).canonical_bytes()


def test_config_check_is_deterministic():
    one = execute("config-check", config_bytes())
    two = execute("config-check", config_bytes())
    assert one.canonical_json() == two.canonical_json()
    assert one.body["accepted"] is True


def test_status_is_not_started():
    result = execute("status", config_bytes())
    assert result.body["lifecycle_state"] == "NOT_STARTED"
    assert result.body["plan"] is None


def test_start_is_plan_only():
    result = execute("start", config_bytes())
    assert result.body["lifecycle_state"] == "OBSERVATION_PLAN_READY"
    assert result.body["plan"]["execution_performed"] is False


def test_stop_preserves_container():
    result = execute("stop", config_bytes())
    assert result.body["lifecycle_state"] == "STOP_PLAN_READY"
    assert result.body["plan"]["container_mutated"] is False
    assert result.body["plan"]["monitored_container_remains_independently_operable"] is True


def test_invalid_configuration_fails_closed():
    result = execute("start", b"{}")
    assert result.body["accepted"] is False
    assert result.body["reason_code"] == "CONFIGURATION_INVALID"


def test_unknown_command_and_safety_fields():
    result = execute("launch", config_bytes())
    assert result.body["accepted"] is False
    assert result.body["reason_code"] == "UNKNOWN_COMMAND"
    assert result.body["safety"] == SAFETY

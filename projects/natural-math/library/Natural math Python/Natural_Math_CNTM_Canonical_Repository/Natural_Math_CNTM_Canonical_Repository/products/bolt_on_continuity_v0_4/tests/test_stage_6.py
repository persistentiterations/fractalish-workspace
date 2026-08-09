import json
import pytest
from bolt_on_v0_4.stage_6 import (
    AUTHORITY, IncidentError, canonical_bytes, export_incident, explain_incident,
    list_incidents, replay_incident, sha256, validate_incident,
)

CID = "a" * 64
CFG = "sha256:" + "b" * 64

def receipt(sequence, event_type, payload, previous):
    base = {"sequence": sequence, "event_type": event_type, "payload": payload, "previous_digest": previous}
    return {**base, "receipt_digest": sha256(canonical_bytes(base))}

def incident(seed="1", updated=2, status="PROJECTED"):
    first = receipt(1, "OBSERVED", {"state": "running"}, "0" * 64)
    second = receipt(updated, "DECIDED", {"decision": "HOLD"}, first["receipt_digest"])
    return {
        "incident_id": "inc-" + seed * 64,
        "container_id": CID,
        "configuration_digest": CFG,
        "opened_sequence": 1,
        "updated_sequence": updated,
        "decision": "HOLD",
        "reason_code": "THRESHOLD_REACHED",
        "action_status": status,
        "receipts": [first, second],
    }

def test_valid_incident():
    assert validate_incident(incident()).body()["decision"] == "HOLD"

@pytest.mark.parametrize("field", ["incident_id","container_id","configuration_digest","decision","reason_code","action_status"])
def test_invalid_scalar_fields(field):
    value = incident()
    value[field] = "bad"
    with pytest.raises(IncidentError):
        validate_incident(value)

def test_extra_field_rejected():
    value = incident(); value["extra"] = True
    with pytest.raises(IncidentError): validate_incident(value)

def test_receipt_digest_rejected():
    value = incident(); value["receipts"][1]["receipt_digest"] = "0" * 64
    with pytest.raises(IncidentError): validate_incident(value)

def test_receipt_link_rejected():
    value = incident(); value["receipts"][1]["previous_digest"] = "0" * 64
    with pytest.raises(IncidentError): validate_incident(value)

def test_receipt_order_rejected():
    value = incident(); value["receipts"][1]["sequence"] = 1
    with pytest.raises(IncidentError): validate_incident(value)

def test_sequence_bounds_rejected():
    value = incident(); value["updated_sequence"] = 3
    with pytest.raises(IncidentError): validate_incident(value)

def test_list_order_and_limit():
    a = incident("a", 2); b = incident("b", 4); c = incident("c", 4)
    body = list_incidents([a, c, b], 2).body()
    assert [x["incident_id"] for x in body["items"]] == [b["incident_id"], c["incident_id"]]

@pytest.mark.parametrize("limit", [0, -1, 1001, True])
def test_invalid_limit(limit):
    with pytest.raises(IncidentError): list_incidents([], limit)

def test_explain_projected_not_executed():
    explanation = explain_incident(incident()).body()["explanation"]
    assert explanation["projected_action_present"] is True
    assert explanation["native_execution_evidenced"] is False

def test_only_docker_accepted_is_executed():
    assert explain_incident(incident(status="DOCKER_ACCEPTED")).body()["explanation"]["native_execution_evidenced"] is True
    assert explain_incident(incident(status="APPROVED")).body()["explanation"]["native_execution_evidenced"] is False

def test_replay_terminal_receipt():
    value = incident()
    replay = replay_incident(value).body()["replay"]
    assert replay["receipt_count"] == 2
    assert replay["terminal_receipt_digest"] == value["receipts"][-1]["receipt_digest"]

def test_export_deterministic():
    one = export_incident(incident())
    two = export_incident(incident())
    assert one.canonical_bytes() == two.canonical_bytes()
    package = one.body()["export"]
    base = dict(package); digest = base.pop("package_digest")
    assert digest == sha256(canonical_bytes(base))

def test_export_is_in_memory_data():
    assert isinstance(export_incident(incident()).body()["export"], dict)

def test_authority_exact_enabled_set():
    enabled = {key for key, value in AUTHORITY.items() if value}
    assert enabled == {
        "stage_5_result_consumption","incident_validation","incident_listing",
        "incident_explanation","offline_replay","in_memory_export",
    }

def test_result_digest():
    result = replay_incident(incident()).body()
    base = dict(result); digest = base.pop("result_digest")
    assert digest == sha256(canonical_bytes(base))

def test_boolean_sequence_rejected():
    value = incident(); value["opened_sequence"] = True
    with pytest.raises(IncidentError): validate_incident(value)

def test_payload_nan_rejected():
    value = incident(); value["receipts"][0]["payload"] = float("nan")
    with pytest.raises(IncidentError): validate_incident(value)

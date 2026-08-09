import hashlib
import json

import pytest

from bolt_on.incident_stage6 import (
    IncidentError,
    explain_incident,
    export_incident,
    list_incidents,
    replay_incident,
    validate_incident,
)
from bolt_on.receipts import canonical_json_bytes

CID = "a" * 64
CONFIG = "sha256:" + "b" * 64


def receipt(sequence: int, event_type: str, payload: dict, previous: str) -> dict:
    base = {"event_type": event_type, "payload": payload, "previous_digest": previous, "sequence": sequence}
    return dict(base, receipt_digest=hashlib.sha256(canonical_json_bytes(base)).hexdigest())


def incident(updated: int = 1, incident_hex: str = "c") -> dict:
    first = receipt(0, "OBSERVED", {"state": "running"}, "0" * 64)
    second = receipt(1, "DECIDED", {"decision": "HOLD"}, first["receipt_digest"])
    return {
        "incident_id": "inc-" + incident_hex * 64,
        "container_id": CID,
        "configuration_digest": CONFIG,
        "opened_sequence": 0,
        "updated_sequence": updated,
        "decision": "HOLD",
        "reason_code": "BOUNDARY_REACHED",
        "action_status": "PROJECTED",
        "receipts": [first, second],
    }


def test_validation_and_replay_are_deterministic():
    value = incident()
    assert validate_incident(value) == validate_incident(value)
    replay = replay_incident(value)
    assert replay.decision == "HOLD"
    assert replay.action_status == "PROJECTED"
    assert replay.receipt_count == 2
    assert replay.chain_valid is True


def test_tampered_receipt_digest_rejected():
    value = incident()
    value["receipts"][1]["receipt_digest"] = "0" * 64
    with pytest.raises(IncidentError, match="RECEIPT_DIGEST_MISMATCH"):
        validate_incident(value)


def test_listing_order_and_limit():
    older = incident(1, "d")
    newer = incident(1, "c")
    listed = list_incidents([older, newer], 1)
    assert len(listed) == 1
    assert listed[0]["incident_id"] == "inc-" + "c" * 64
    with pytest.raises(IncidentError, match="INVALID_LIST_LIMIT"):
        list_incidents([older], True)


def test_explanation_does_not_confuse_projection_with_execution():
    explanation = explain_incident(incident())
    assert explanation["action"]["status"] == "PROJECTED"
    assert explanation["action"]["native_execution_evidenced"] is False


def test_only_docker_accepted_evidences_execution():
    value = incident()
    value["action_status"] = "DOCKER_ACCEPTED"
    assert explain_incident(value)["action"]["native_execution_evidenced"] is True


def test_export_is_deterministic_and_self_describing():
    one = export_incident(incident())
    two = export_incident(incident())
    assert one == two
    assert one.endswith(b"\n") and not one.endswith(b"\n\n")
    parsed = json.loads(one)
    base = dict(parsed)
    digest = base.pop("package_digest")
    assert digest == hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    assert [item["name"] for item in parsed["manifest"]] == ["incident.json", "replay.json", "summary.json"]

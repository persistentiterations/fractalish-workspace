from dataclasses import replace

import pytest

from bolt_on.approval_stage7 import (
    ApprovalError,
    GatewayState,
    create_request,
    decide,
    transition_gateway,
    validate_request,
)

CID = "a" * 64
RID = "req-" + "b" * 64
DIGEST = "sha256:" + "c" * 64


def request():
    return create_request(RID, CID, "HOLD", DIGEST, DIGEST, 10, 20)


def test_request_is_deterministic_and_valid():
    one = request()
    two = request()
    assert one.body() == two.body()
    validate_request(one)


def test_no_action_and_tampering_fail_closed():
    with pytest.raises(ApprovalError, match="INVALID_ACTION"):
        create_request(RID, CID, "NO_ACTION", DIGEST, DIGEST, 10, 20)
    with pytest.raises(ApprovalError, match="REQUEST_DIGEST_MISMATCH"):
        validate_request(replace(request(), request_digest=DIGEST))


def test_gateway_transitions_are_explicit():
    enabled = transition_gateway(GatewayState(), "ENABLED", 11)
    assert enabled.state == "ENABLED"
    with pytest.raises(ApprovalError, match="NO_GATEWAY_TRANSITION"):
        transition_gateway(enabled, "ENABLED", 12)
    assert transition_gateway(enabled, "DISABLED", 13).state == "DISABLED"


def test_approval_requires_enabled_gateway():
    with pytest.raises(ApprovalError, match="GATEWAY_NOT_ENABLED"):
        decide(request(), GatewayState(), "APPROVE", "OPERATOR_CONFIRMED", 12)
    record = decide(request(), GatewayState("ENABLED", 11), "APPROVE", "OPERATOR_CONFIRMED", 12)
    assert record.body()["native_execution_authorized"] is False


def test_denial_allowed_while_disabled_and_window_enforced():
    denied = decide(request(), GatewayState(), "DENY", "OPERATOR_DECLINED", 12)
    assert denied.decision == "DENY"
    with pytest.raises(ApprovalError, match="DECISION_OUTSIDE_WINDOW"):
        decide(request(), GatewayState(), "DENY", "OPERATOR_DECLINED", 21)


def test_duplicate_conflict_and_identifier_reuse_rejected():
    approved = decide(request(), GatewayState("ENABLED", 11), "APPROVE", "OPERATOR_CONFIRMED", 12)
    with pytest.raises(ApprovalError, match="DUPLICATE_DECISION"):
        decide(request(), GatewayState("ENABLED", 11), "APPROVE", "OPERATOR_CONFIRMED", 12, [approved])
    with pytest.raises(ApprovalError, match="CONFLICTING_DECISION"):
        decide(request(), GatewayState(), "DENY", "OPERATOR_DECLINED", 13, [approved])
    changed = create_request(RID, CID, "RELEASE", DIGEST, DIGEST, 10, 20)
    with pytest.raises(ApprovalError, match="REQUEST_IDENTIFIER_REUSE"):
        decide(changed, GatewayState(), "DENY", "OPERATOR_DECLINED", 13, [approved])

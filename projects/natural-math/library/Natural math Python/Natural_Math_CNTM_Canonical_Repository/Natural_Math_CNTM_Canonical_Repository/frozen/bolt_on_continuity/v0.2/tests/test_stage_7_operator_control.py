from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from bolt_on_continuity_v0_2.operator_control import (  # noqa: E402
    GatewayState,
    OperatorControlError,
    build_projected_request,
    canonical_record_bytes,
    create_operator_decision,
    register_decision,
    transition_gateway,
    validate_projected_request,
)

CID = "a" * 64
DIGEST_A = "sha256:" + "1" * 64
DIGEST_B = "sha256:" + "2" * 64


def request() -> dict:
    return build_projected_request(
        request_id="req-001",
        container_id=CID,
        action="HOLD",
        incident_digest=DIGEST_A,
        configuration_digest=DIGEST_B,
        issued_sequence=10,
        expiry_sequence=20,
    )


class Stage7OperatorControlTests(unittest.TestCase):
    def test_valid_approval(self) -> None:
        enabled, _ = transition_gateway(GatewayState(), enable=True, sequence=1)
        result = create_operator_decision(
            request(), gateway_state=enabled, decision="APPROVE",
            reason_code="OPERATOR_APPROVED", decision_sequence=12,
        )
        self.assertEqual(result["decision"], "APPROVE")
        self.assertFalse(result["native_execution_authorized"])

    def test_valid_denial_while_disabled(self) -> None:
        result = create_operator_decision(
            request(), gateway_state=GatewayState(), decision="DENY",
            reason_code="OPERATOR_DENIED", decision_sequence=12,
        )
        self.assertEqual(result["decision"], "DENY")

    def test_disabled_gateway_rejects_approval(self) -> None:
        with self.assertRaises(OperatorControlError):
            create_operator_decision(
                request(), gateway_state=GatewayState(), decision="APPROVE",
                reason_code="OPERATOR_APPROVED", decision_sequence=12,
            )

    def test_expired_request_rejected(self) -> None:
        enabled, _ = transition_gateway(GatewayState(), enable=True, sequence=1)
        with self.assertRaises(OperatorControlError):
            create_operator_decision(
                request(), gateway_state=enabled, decision="APPROVE",
                reason_code="OPERATOR_APPROVED", decision_sequence=21,
            )

    def test_preissued_decision_rejected(self) -> None:
        with self.assertRaises(OperatorControlError):
            create_operator_decision(
                request(), gateway_state=GatewayState(), decision="DENY",
                reason_code="NOT_REQUIRED", decision_sequence=9,
            )

    def test_request_digest_tampering_rejected(self) -> None:
        value = request()
        value["action"] = "RELEASE"
        with self.assertRaises(OperatorControlError):
            validate_projected_request(value)

    def test_no_action_rejected(self) -> None:
        with self.assertRaises(OperatorControlError):
            build_projected_request(
                request_id="req-001", container_id=CID, action="NO_ACTION",
                incident_digest=DIGEST_A, configuration_digest=DIGEST_B,
                issued_sequence=10, expiry_sequence=20,
            )

    def test_short_container_id_rejected(self) -> None:
        with self.assertRaises(OperatorControlError):
            build_projected_request(
                request_id="req-001", container_id="a" * 12, action="HOLD",
                incident_digest=DIGEST_A, configuration_digest=DIGEST_B,
                issued_sequence=10, expiry_sequence=20,
            )

    def test_extra_request_field_rejected(self) -> None:
        value = request()
        value["command"] = "docker pause"
        with self.assertRaises(OperatorControlError):
            validate_projected_request(value)

    def test_duplicate_decision_rejected(self) -> None:
        decision = create_operator_decision(
            request(), gateway_state=GatewayState(), decision="DENY",
            reason_code="OPERATOR_DENIED", decision_sequence=12,
        )
        registry = register_decision({}, request(), decision)
        with self.assertRaises(OperatorControlError):
            register_decision(registry, request(), decision)

    def test_conflicting_decision_rejected(self) -> None:
        denied = create_operator_decision(
            request(), gateway_state=GatewayState(), decision="DENY",
            reason_code="OPERATOR_DENIED", decision_sequence=12,
        )
        registry = register_decision({}, request(), denied)
        enabled, _ = transition_gateway(GatewayState(), enable=True, sequence=1)
        approved = create_operator_decision(
            request(), gateway_state=enabled, decision="APPROVE",
            reason_code="OPERATOR_APPROVED", decision_sequence=13,
        )
        with self.assertRaises(OperatorControlError):
            register_decision(registry, request(), approved)

    def test_request_id_reuse_with_different_digest_rejected(self) -> None:
        original = request()
        denied = create_operator_decision(
            original, gateway_state=GatewayState(), decision="DENY",
            reason_code="OPERATOR_DENIED", decision_sequence=12,
        )
        registry = register_decision({}, original, denied)
        changed = build_projected_request(
            request_id="req-001", container_id=CID, action="RELEASE",
            incident_digest=DIGEST_A, configuration_digest=DIGEST_B,
            issued_sequence=10, expiry_sequence=20,
        )
        with self.assertRaises(OperatorControlError):
            register_decision(registry, changed, denied)

    def test_gateway_transitions(self) -> None:
        enabled, enable_record = transition_gateway(GatewayState(), enable=True, sequence=1)
        disabled, disable_record = transition_gateway(enabled, enable=False, sequence=2)
        self.assertTrue(enable_record["enabled"])
        self.assertFalse(disable_record["enabled"])
        self.assertFalse(disabled.enabled)
        self.assertFalse(enable_record["native_execution_authorized"])

    def test_repeated_gateway_state_rejected(self) -> None:
        with self.assertRaises(OperatorControlError):
            transition_gateway(GatewayState(), enable=False, sequence=1)

    def test_canonical_serialization_is_stable(self) -> None:
        first = request()
        second = copy.deepcopy(first)
        self.assertEqual(canonical_record_bytes(first), canonical_record_bytes(second))


if __name__ == "__main__":
    unittest.main()

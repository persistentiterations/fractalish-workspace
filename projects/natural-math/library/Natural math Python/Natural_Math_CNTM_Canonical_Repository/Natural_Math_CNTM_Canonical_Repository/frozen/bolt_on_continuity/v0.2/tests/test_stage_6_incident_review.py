from __future__ import annotations

import hashlib
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bolt_on_continuity_v0_2.incident_review import (
    IncidentReviewError,
    create_export_package,
    explain_incident,
    list_incidents,
    replay_incident,
    validate_incident,
    verify_export_package,
)


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def digest(value):
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def receipt(sequence, event_type, payload, previous_digest):
    item = {
        "sequence": sequence,
        "event_type": event_type,
        "payload": payload,
        "previous_digest": previous_digest,
    }
    item["receipt_digest"] = digest(item)
    return item


def sample_incident(status="PROJECTED", suffix="a", opened=10):
    first = receipt(opened, "INCIDENT_OPENED", {"state": "running"}, None)
    second = receipt(opened + 1, "DECISION_RECORDED", {"decision": "HOLD"}, first["receipt_digest"])
    return {
        "incident_id": "inc-" + suffix * 64,
        "container_id": "b" * 64,
        "configuration_digest": "sha256:" + "c" * 64,
        "opened_sequence": opened,
        "updated_sequence": opened + 1,
        "decision": "HOLD",
        "reason_code": "BOUNDED_DIVERGENCE",
        "action_status": status,
        "receipts": [first, second],
    }


class Stage6IncidentReviewTests(unittest.TestCase):
    def test_valid_incident(self):
        self.assertEqual(validate_incident(sample_incident())["decision"], "HOLD")

    def test_extra_field_rejected(self):
        item = sample_incident()
        item["extra"] = True
        with self.assertRaises(IncidentReviewError):
            validate_incident(item)

    def test_listing_order_is_stable(self):
        older = sample_incident(suffix="a", opened=1)
        newer = sample_incident(suffix="b", opened=20)
        listed = list_incidents([older, newer])
        self.assertEqual([row["incident_id"] for row in listed], [newer["incident_id"], older["incident_id"]])

    def test_invalid_limit_rejected(self):
        with self.assertRaises(IncidentReviewError):
            list_incidents([sample_incident()], limit=0)

    def test_projected_action_is_not_execution(self):
        explanation = explain_incident(sample_incident("PROJECTED"))
        self.assertFalse(explanation["native_execution_evidenced"])
        self.assertFalse(explanation["projected_is_execution"])

    def test_docker_accepted_is_execution_evidence(self):
        self.assertTrue(explain_incident(sample_incident("DOCKER_ACCEPTED"))["native_execution_evidenced"])

    def test_valid_replay(self):
        replay = replay_incident(sample_incident())
        self.assertTrue(replay["chain_valid"])
        self.assertEqual(replay["receipt_count"], 2)

    def test_tampered_receipt_digest_rejected(self):
        item = sample_incident()
        item["receipts"][1]["receipt_digest"] = "sha256:" + "0" * 64
        with self.assertRaises(IncidentReviewError):
            replay_incident(item)

    def test_broken_chain_rejected(self):
        item = sample_incident()
        item["receipts"][1]["previous_digest"] = None
        item["receipts"][1]["receipt_digest"] = digest({k: item["receipts"][1][k] for k in ["event_type", "payload", "previous_digest", "sequence"]})
        with self.assertRaises(IncidentReviewError):
            replay_incident(item)

    def test_sequence_mismatch_rejected(self):
        item = sample_incident()
        item["receipts"][1]["sequence"] = 15
        item["receipts"][1]["receipt_digest"] = digest({k: item["receipts"][1][k] for k in ["event_type", "payload", "previous_digest", "sequence"]})
        with self.assertRaises(IncidentReviewError):
            replay_incident(item)

    def test_export_is_deterministic(self):
        first = create_export_package(sample_incident())
        second = create_export_package(sample_incident())
        self.assertEqual(first["manifest_bytes"], second["manifest_bytes"])
        self.assertEqual(first["package_digest"], second["package_digest"])

    def test_export_verifies(self):
        self.assertTrue(verify_export_package(create_export_package(sample_incident())))

    def test_tampered_export_fails(self):
        package = create_export_package(sample_incident())
        package = deepcopy(package)
        package["members"]["summary.json"] += b"x"
        self.assertFalse(verify_export_package(package))

    def test_export_member_names_are_fixed(self):
        package = create_export_package(sample_incident())
        self.assertEqual(set(package["members"]), {"incident.json", "replay.json", "summary.json"})


if __name__ == "__main__":
    unittest.main()

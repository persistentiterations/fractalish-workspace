"""Deterministic release-candidate preparation record with no release authority."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from .receipts import canonical_json_bytes

CANDIDATE_ID = "v0.3-rc1"
QUALIFIED_SOURCE_COMMIT = "6ef5595f4d0d86074fbb53e4a37a9c04d4a62f78"
STAGE_MANIFESTS = {
    "stage_0": "50fcd8211a1268382fb5bdef3916cf6256fee35a607007f97dd2483091a317e3",
    "stage_1": "243440198bc6477efcaa7b509361c9b7aba79530b97be3c1abad36d0a23639d6",
    "stage_2": "35a361b1e3db8dca05e87a4ebd606204a252a34e541ea0db301fa15887b4b81a",
    "stage_3": "64d646d4681351751caa41a1a670c6cb43595886e75db703dffc57ac0d62eab6",
    "stage_4": "286ad1dfc5df749de5c25f966a142575db0ddff991619e5bfca3c4069b1ac33c",
    "stage_5": "c25fa35e14129e63ba059a562f5bf78e9333c9891bc4733a6601412aad501741",
    "stage_6": "4be9096944d4b164a6a735ec9df527c282cd2518d61975db259140a847bc26a0",
    "stage_7": "2005070103500c149c6aa17742f41bac3ef9e558b0208427fa26ed3477e571ab",
    "stage_8": "bfd6146e5389f3abf555591aa4a0aead262366fb020529f59c223104013443e5",
    "stage_9": "cb3f62b119e7c60b4ba13f73df9cb255bbb0d1289e299a4237ddd0f06a2337e0",
    "stage_10": "24b80949a9655c7996c41e00ff8d45f388160fac38990ebc8862eac64e7dad78",
}


class RCPreparationError(ValueError):
    """Stable fail-closed RC preparation error."""


@dataclass(frozen=True)
class RCPreparationEvidence:
    tests_passed: int
    frozen_regression_passed: bool
    frozen_diff_clean: bool
    working_tree_clean: bool


@dataclass(frozen=True)
class RCPreparationRecord:
    body: Mapping[str, object]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(dict(self.body)) + b"\n"


def prepare_rc1(evidence: RCPreparationEvidence) -> RCPreparationRecord:
    if type(evidence.tests_passed) is not int or evidence.tests_passed != 66:
        raise RCPreparationError("TEST_EVIDENCE_MISMATCH")
    if evidence.frozen_regression_passed is not True:
        raise RCPreparationError("FROZEN_REGRESSION_NOT_PROVEN")
    if evidence.frozen_diff_clean is not True:
        raise RCPreparationError("FROZEN_DIFF_NOT_CLEAN")
    if evidence.working_tree_clean is not True:
        raise RCPreparationError("WORKING_TREE_NOT_CLEAN")

    base: dict[str, object] = {
        "authority": {
            "container_mutation_authorized": False,
            "merge_authorized": False,
            "native_execution_authorized": False,
            "production_readiness_claim_authorized": False,
            "publication_authorized": False,
            "release_freeze_authorized": False,
        },
        "candidate_id": CANDIDATE_ID,
        "evidence": {
            "frozen_diff_clean": True,
            "frozen_regression_passed": True,
            "tests_passed": 66,
            "working_tree_clean": True,
        },
        "product": "bolt-on-continuity-for-docker",
        "product_version": "0.3.0.dev0",
        "qualified_source_commit": QUALIFIED_SOURCE_COMMIT,
        "schema_version": 1,
        "stage_manifests": dict(STAGE_MANIFESTS),
        "status": "READY_FOR_RC_REVIEW",
    }
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    body = dict(base)
    body["record_digest"] = digest
    return RCPreparationRecord(body)

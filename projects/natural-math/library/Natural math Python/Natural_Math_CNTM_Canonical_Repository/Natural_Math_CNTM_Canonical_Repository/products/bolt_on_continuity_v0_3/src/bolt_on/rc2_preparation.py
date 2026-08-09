"""Deterministic RC2 preparation after corrected RC1 review findings."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from .receipts import canonical_json_bytes
from .rc1_preparation import STAGE_MANIFESTS

CANDIDATE_ID = "v0.3-rc2"
CORRECTED_SOURCE_COMMIT = "67e0da7e41e96870d8dbeafa8031e4de694bb03f"
CORRECTED_TREE_FILES = 76
CORRECTED_TREE_SHA256 = "203d43b5e3f7330c47f7cc72916540b887dccb67d039e1348989a6a8a2ea2376"


class RC2PreparationError(ValueError):
    """Stable fail-closed RC2 preparation error."""


@dataclass(frozen=True)
class RC2PreparationEvidence:
    tests_passed: int
    rc1_review_passed: bool
    frozen_regression_passed: bool
    frozen_diff_clean: bool
    working_tree_clean: bool


@dataclass(frozen=True)
class RC2PreparationRecord:
    body: Mapping[str, object]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(dict(self.body)) + b"\n"


def prepare_rc2(evidence: RC2PreparationEvidence) -> RC2PreparationRecord:
    if type(evidence.tests_passed) is not int or evidence.tests_passed != 78:
        raise RC2PreparationError("TEST_EVIDENCE_MISMATCH")
    if evidence.rc1_review_passed is not True:
        raise RC2PreparationError("RC1_REVIEW_NOT_PROVEN")
    if evidence.frozen_regression_passed is not True:
        raise RC2PreparationError("FROZEN_REGRESSION_NOT_PROVEN")
    if evidence.frozen_diff_clean is not True:
        raise RC2PreparationError("FROZEN_DIFF_NOT_CLEAN")
    if evidence.working_tree_clean is not True:
        raise RC2PreparationError("WORKING_TREE_NOT_CLEAN")

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
        "corrected_candidate": {
            "source_commit": CORRECTED_SOURCE_COMMIT,
            "tree_files": CORRECTED_TREE_FILES,
            "tree_sha256": CORRECTED_TREE_SHA256,
        },
        "evidence": {
            "frozen_diff_clean": True,
            "frozen_regression_passed": True,
            "rc1_review_passed": True,
            "tests_passed": 78,
            "working_tree_clean": True,
        },
        "product": "bolt-on-continuity-for-docker",
        "product_version": "0.3.0.dev0",
        "prior_candidate": {"candidate_id": "v0.3-rc1", "disposition": "NEEDS_CORRECTION"},
        "schema_version": 1,
        "stage_manifests": dict(STAGE_MANIFESTS),
        "status": "READY_FOR_RC2_REVIEW",
    }
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    body = dict(base)
    body["record_digest"] = digest
    return RC2PreparationRecord(body)

"""Deterministic formal RC2 review with no release authority."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from .receipts import canonical_json_bytes

CORRECTED_SOURCE_COMMIT = "67e0da7e41e96870d8dbeafa8031e4de694bb03f"
CORRECTED_TREE_FILES = 76
CORRECTED_TREE_SHA256 = "203d43b5e3f7330c47f7cc72916540b887dccb67d039e1348989a6a8a2ea2376"
RC2_PREPARATION_HEAD = "59bddbbeac43914633782be45d01e90f3d97b7c0"
RC2_RECORD_SHA256 = "3075d810faf9ae1cf0b201e94b81f0287894149479eba341b66a6ac6cfd8a051"
RC2_PREPARATION_MANIFEST_SHA256 = "cf36118ccdeb9642509f96fc986a7c7711976a09a91bdc3f68acb54de3c11f6d"


class RC2ReviewError(ValueError):
    """Stable fail-closed RC2 review error."""


@dataclass(frozen=True)
class RC2ReviewEvidence:
    tests_passed: int
    rc2_preparation_passed: bool
    rc1_findings_corrected: bool
    preparation_delta_only: bool
    frozen_regression_passed: bool
    frozen_diff_clean: bool
    working_tree_clean: bool


@dataclass(frozen=True)
class RC2ReviewRecord:
    body: Mapping[str, object]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(dict(self.body)) + b"\n"


def review_rc2(evidence: RC2ReviewEvidence) -> RC2ReviewRecord:
    if type(evidence.tests_passed) is not int or evidence.tests_passed != 84:
        raise RC2ReviewError("TEST_EVIDENCE_MISMATCH")
    checks = (
        (evidence.rc2_preparation_passed, "RC2_PREPARATION_NOT_PROVEN"),
        (evidence.rc1_findings_corrected, "RC1_FINDINGS_NOT_CORRECTED"),
        (evidence.preparation_delta_only, "PREPARATION_DELTA_NOT_PROVEN"),
        (evidence.frozen_regression_passed, "FROZEN_REGRESSION_NOT_PROVEN"),
        (evidence.frozen_diff_clean, "FROZEN_DIFF_NOT_CLEAN"),
        (evidence.working_tree_clean, "WORKING_TREE_NOT_CLEAN"),
    )
    for value, code in checks:
        if value is not True:
            raise RC2ReviewError(code)

    base: dict[str, object] = {
        "authority": {
            "container_mutation_authorized": False,
            "merge_authorized": False,
            "native_execution_authorized": False,
            "production_readiness_claim_authorized": False,
            "publication_authorized": False,
            "release_freeze_authorized": False,
        },
        "candidate_id": "v0.3-rc2",
        "corrected_candidate": {
            "source_commit": CORRECTED_SOURCE_COMMIT,
            "tree_files": CORRECTED_TREE_FILES,
            "tree_sha256": CORRECTED_TREE_SHA256,
        },
        "evidence": {
            "frozen_diff_clean": True,
            "frozen_regression_passed": True,
            "preparation_delta_only": True,
            "rc1_findings_corrected": True,
            "rc2_preparation_passed": True,
            "tests_passed": 84,
            "working_tree_clean": True,
        },
        "findings": {
            "complete_tree_coverage": "CORRECTED",
            "readme_scope": "CORRECTED",
            "new_product_behavior": "NONE",
        },
        "product": "bolt-on-continuity-for-docker",
        "product_version": "0.3.0.dev0",
        "rc2_preparation": {
            "head": RC2_PREPARATION_HEAD,
            "manifest_sha256": RC2_PREPARATION_MANIFEST_SHA256,
            "record_sha256": RC2_RECORD_SHA256,
        },
        "schema_version": 1,
        "status": "READY_FOR_FREEZE_DECISION",
    }
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    body = dict(base)
    body["review_digest"] = digest
    return RC2ReviewRecord(body)

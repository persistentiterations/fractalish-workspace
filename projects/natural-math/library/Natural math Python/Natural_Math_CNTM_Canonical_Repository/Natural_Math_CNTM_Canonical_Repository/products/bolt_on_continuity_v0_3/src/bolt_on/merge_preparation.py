"""Deterministic merge-preparation record with no merge authority."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from .receipts import canonical_json_bytes

TARGET_BRANCH = "main"
TARGET_HEAD = "0558d3e671d854549003b729eb3879059e8658cc"
FROZEN_BRANCH_HEAD = "75e9cd4d7b16558702b393cf2336cffe45a18474"
AHEAD_BY = 77
BEHIND_BY = 0
FROZEN_MANIFEST = "3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb"
RC2_REVIEW_SHA256 = "5e1709214599c0bf075e04557952ee5b563461749df71a41d6fe7bbcc4e1adeb"


class MergePreparationError(ValueError):
    """Stable fail-closed merge preparation error."""


@dataclass(frozen=True)
class MergePreparationEvidence:
    tests_passed: int
    frozen_verification_passed: bool
    fast_forward_only: bool
    frozen_diff_clean: bool
    working_tree_clean: bool


@dataclass(frozen=True)
class MergePreparationRecord:
    body: Mapping[str, object]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(dict(self.body)) + b"\n"


def prepare_merge(evidence: MergePreparationEvidence) -> MergePreparationRecord:
    if type(evidence.tests_passed) is not int or evidence.tests_passed != 90:
        raise MergePreparationError("TEST_EVIDENCE_MISMATCH")
    if evidence.frozen_verification_passed is not True:
        raise MergePreparationError("FROZEN_VERIFICATION_NOT_PROVEN")
    if evidence.fast_forward_only is not True:
        raise MergePreparationError("FAST_FORWARD_NOT_PROVEN")
    if evidence.frozen_diff_clean is not True:
        raise MergePreparationError("FROZEN_DIFF_NOT_CLEAN")
    if evidence.working_tree_clean is not True:
        raise MergePreparationError("WORKING_TREE_NOT_CLEAN")

    base: dict[str, object] = {
        "authority": {
            "merge_authorized": False,
            "publication_authorized": False,
            "tag_authorized": False,
            "installation_authorized": False,
            "production_readiness_claim_authorized": False,
            "container_mutation_authorized": False,
        },
        "evidence": {
            "tests_passed": 90,
            "frozen_verification_passed": True,
            "fast_forward_only": True,
            "frozen_diff_clean": True,
            "working_tree_clean": True,
        },
        "merge": {
            "target_branch": TARGET_BRANCH,
            "target_head": TARGET_HEAD,
            "candidate_head": FROZEN_BRANCH_HEAD,
            "ahead_by": AHEAD_BY,
            "behind_by": BEHIND_BY,
        },
        "release": {
            "version": "0.3",
            "frozen_manifest": FROZEN_MANIFEST,
            "rc2_review_sha256": RC2_REVIEW_SHA256,
        },
        "schema_version": 1,
        "status": "READY_FOR_MERGE_DECISION",
    }
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    body = dict(base)
    body["record_digest"] = digest
    return MergePreparationRecord(body)

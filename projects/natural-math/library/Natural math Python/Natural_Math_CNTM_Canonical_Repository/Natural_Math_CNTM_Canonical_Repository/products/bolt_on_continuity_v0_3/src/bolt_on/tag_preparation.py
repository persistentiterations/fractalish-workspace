"""Deterministic tag preparation after the qualified v0.3 merge."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from .receipts import canonical_json_bytes

MERGED_BRANCH = "main"
MERGED_HEAD = "1c95a1ff8ead30675d4d26f7d77720097c5b9129"
FROZEN_SOURCE_COMMIT = "67e0da7e41e96870d8dbeafa8031e4de694bb03f"
FROZEN_MANIFEST = "3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb"
PROPOSED_TAG = "bolt-on-continuity-v0.3"


class TagPreparationError(ValueError):
    """Stable fail-closed tag preparation error."""


@dataclass(frozen=True)
class TagPreparationEvidence:
    tests_passed: int
    merged_main_verified: bool
    frozen_regression_passed: bool
    working_tree_clean: bool
    tag_absent_checked: bool


@dataclass(frozen=True)
class TagPreparationRecord:
    body: Mapping[str, object]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(dict(self.body)) + b"\n"


def prepare_tag(evidence: TagPreparationEvidence) -> TagPreparationRecord:
    if type(evidence.tests_passed) is not int or evidence.tests_passed != 98:
        raise TagPreparationError("TEST_EVIDENCE_MISMATCH")
    if evidence.merged_main_verified is not True:
        raise TagPreparationError("MERGED_MAIN_NOT_PROVEN")
    if evidence.frozen_regression_passed is not True:
        raise TagPreparationError("FROZEN_REGRESSION_NOT_PROVEN")
    if evidence.working_tree_clean is not True:
        raise TagPreparationError("WORKING_TREE_NOT_CLEAN")
    if evidence.tag_absent_checked is not True:
        raise TagPreparationError("TAG_ABSENCE_NOT_CHECKED")

    base: dict[str, object] = {
        "authority": {
            "docker_mutation_authorized": False,
            "github_release_authorized": False,
            "installation_authorized": False,
            "production_readiness_claim_authorized": False,
            "publication_authorized": False,
            "release_asset_upload_authorized": False,
            "tag_creation_authorized": False,
            "tag_move_authorized": False,
        },
        "evidence": {
            "frozen_regression_passed": True,
            "merged_main_verified": True,
            "tag_absent_checked": True,
            "tests_passed": 98,
            "working_tree_clean": True,
        },
        "frozen_release": {
            "manifest_sha256": FROZEN_MANIFEST,
            "source_commit": FROZEN_SOURCE_COMMIT,
        },
        "merged_branch": MERGED_BRANCH,
        "merged_head": MERGED_HEAD,
        "product": "bolt-on-continuity-for-docker",
        "product_version": "0.3.0",
        "proposed_tag": {
            "kind": "annotated",
            "name": PROPOSED_TAG,
            "target": MERGED_HEAD,
        },
        "schema_version": 1,
        "status": "READY_FOR_TAG_DECISION",
    }
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    body = dict(base)
    body["record_digest"] = digest
    return TagPreparationRecord(body)

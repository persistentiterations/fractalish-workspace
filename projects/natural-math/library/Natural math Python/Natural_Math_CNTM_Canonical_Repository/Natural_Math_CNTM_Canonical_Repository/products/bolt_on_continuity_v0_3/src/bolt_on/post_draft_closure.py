"""Deterministic post-draft closure without publication authority."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib

from .receipts import canonical_json_bytes

REPOSITORY = "BonAcqui-LLC/cntm-natural-math-canonical-library"
RELEASE_TITLE = "Bolt-On Continuity v0.3"
TAG_NAME = "bolt-on-continuity-v0.3"
TAG_OBJECT = "fc3e27567e38a94322b437a4285c52ee38ac8407"
TAG_TARGET = "1c95a1ff8ead30675d4d26f7d77720097c5b9129"
FROZEN_MANIFEST = "3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb"
RELEASE_NOTES_SHA256 = "cafe56a302ecc7f091762a0e90f2d404f90b48683fee9e6272e522c71e622d30"


@dataclass(frozen=True)
class PostDraftEvidence:
    tests_passed: int
    release_exists: bool
    release_is_draft: bool
    release_is_unpublished: bool
    release_title_matches: bool
    tag_matches: bool
    tag_target_matches: bool
    release_notes_match: bool
    uploaded_assets_absent: bool
    frozen_verifier_passed: bool
    all_frozen_passed: bool
    frozen_diff_clean: bool
    worktree_clean: bool


@dataclass(frozen=True)
class PostDraftClosureRecord:
    repository: str
    release_title: str
    tag_name: str
    tag_object: str
    tag_target: str
    frozen_manifest: str
    release_notes_sha256: str
    source_archives_expected: int
    evidence: PostDraftEvidence
    status: str
    authority: dict[str, bool]
    record_digest: str

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(asdict(self))


def close_post_draft(evidence: PostDraftEvidence) -> PostDraftClosureRecord:
    ready = (
        evidence.tests_passed >= 126
        and evidence.release_exists
        and evidence.release_is_draft
        and evidence.release_is_unpublished
        and evidence.release_title_matches
        and evidence.tag_matches
        and evidence.tag_target_matches
        and evidence.release_notes_match
        and evidence.uploaded_assets_absent
        and evidence.frozen_verifier_passed
        and evidence.all_frozen_passed
        and evidence.frozen_diff_clean
        and evidence.worktree_clean
    )
    body = {
        "repository": REPOSITORY,
        "release_title": RELEASE_TITLE,
        "tag_name": TAG_NAME,
        "tag_object": TAG_OBJECT,
        "tag_target": TAG_TARGET,
        "frozen_manifest": FROZEN_MANIFEST,
        "release_notes_sha256": RELEASE_NOTES_SHA256,
        "source_archives_expected": 2,
        "evidence": asdict(evidence),
        "status": "POST_DRAFT_CLOSED" if ready else "NOT_READY",
        "authority": {
            "publish_release": False,
            "edit_release": False,
            "delete_release": False,
            "attach_assets": False,
            "distribute_packages": False,
            "install_or_activate": False,
            "native_execution": False,
            "docker_mutation": False,
            "production_claims": False,
        },
    }
    digest = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    record_fields = {**body, "evidence": evidence}
    return PostDraftClosureRecord(**record_fields, record_digest=digest)

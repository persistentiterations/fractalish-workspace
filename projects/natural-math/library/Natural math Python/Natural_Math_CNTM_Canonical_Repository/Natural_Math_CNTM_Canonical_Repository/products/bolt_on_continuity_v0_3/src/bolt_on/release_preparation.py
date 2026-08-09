"""Deterministic GitHub release preparation without publication authority."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib

from .receipts import canonical_json_bytes

REPOSITORY = "BonAcqui-LLC/cntm-natural-math-canonical-library"
TAG_NAME = "bolt-on-continuity-v0.3"
TAG_OBJECT = "fc3e27567e38a94322b437a4285c52ee38ac8407"
TAG_TARGET = "1c95a1ff8ead30675d4d26f7d77720097c5b9129"
FROZEN_MANIFEST = "3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb"
RELEASE_TITLE = "Bolt-On Continuity v0.3"

RELEASE_NOTES = """# Bolt-On Continuity v0.3

Bolt-On Continuity v0.3 is a frozen, deterministic, observation-first Docker continuity foundation qualified through Stages 0–10.

## Included scope

- fixed read-only Docker probes;
- deterministic discovery, enrollment, configuration, lifecycle-plan, incident-review, approval, recovery-evidence, installation-plan, and qualification records;
- exact receipts and repeatable verification;
- frozen release manifest and annotated source tag.

## Authority boundary

This release is observation-only by default. It does not run a background observer, install or activate services, enable a native gateway, execute recovery actions, or mutate containers. HOLD, RELEASE, approval, recovery, installation, and uninstall outputs remain data-only records or plans.

This prerelease does not claim production readiness, universal compatibility, zero drift, security certification, or operational Docker mutation authority.

## Verification identity

- Tag: `bolt-on-continuity-v0.3`
- Target commit: `1c95a1ff8ead30675d4d26f7d77720097c5b9129`
- Frozen manifest SHA-256: `3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb`
- Release assets: none
"""


@dataclass(frozen=True)
class ReleasePreparationEvidence:
    tests_passed: int
    tag_exists: bool
    tag_target_matches: bool
    frozen_verifier_passed: bool
    all_frozen_passed: bool
    frozen_diff_clean: bool
    worktree_clean: bool


@dataclass(frozen=True)
class ReleasePreparationRecord:
    repository: str
    tag_name: str
    tag_object: str
    tag_target: str
    frozen_manifest: str
    release_title: str
    release_notes_sha256: str
    draft: bool
    prerelease: bool
    assets: tuple[str, ...]
    evidence: ReleasePreparationEvidence
    status: str
    authority: dict[str, bool]
    record_digest: str

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(asdict(self))


def prepare_release(evidence: ReleasePreparationEvidence) -> ReleasePreparationRecord:
    ready = (
        evidence.tests_passed >= 110
        and evidence.tag_exists
        and evidence.tag_target_matches
        and evidence.frozen_verifier_passed
        and evidence.all_frozen_passed
        and evidence.frozen_diff_clean
        and evidence.worktree_clean
    )
    body = {
        "repository": REPOSITORY,
        "tag_name": TAG_NAME,
        "tag_object": TAG_OBJECT,
        "tag_target": TAG_TARGET,
        "frozen_manifest": FROZEN_MANIFEST,
        "release_title": RELEASE_TITLE,
        "release_notes_sha256": hashlib.sha256(RELEASE_NOTES.encode("utf-8")).hexdigest(),
        "draft": True,
        "prerelease": True,
        "assets": (),
        "evidence": asdict(evidence),
        "status": "READY_FOR_RELEASE_DECISION" if ready else "NOT_READY",
        "authority": {
            "create_release": False,
            "publish_release": False,
            "attach_assets": False,
            "distribute_packages": False,
            "install_or_activate": False,
            "native_execution": False,
            "docker_mutation": False,
            "production_claims": False,
        },
    }
    digest = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return ReleasePreparationRecord(
        repository=REPOSITORY,
        tag_name=TAG_NAME,
        tag_object=TAG_OBJECT,
        tag_target=TAG_TARGET,
        frozen_manifest=FROZEN_MANIFEST,
        release_title=RELEASE_TITLE,
        release_notes_sha256=body["release_notes_sha256"],
        draft=True,
        prerelease=True,
        assets=(),
        evidence=evidence,
        status=body["status"],
        authority=body["authority"],
        record_digest=digest,
    )

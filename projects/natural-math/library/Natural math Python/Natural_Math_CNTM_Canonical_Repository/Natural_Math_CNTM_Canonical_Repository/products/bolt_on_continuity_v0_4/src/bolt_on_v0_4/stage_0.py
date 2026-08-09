"""Deterministic Stage 0 product-scope qualification."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

PRODUCT = "Bolt-On Continuity v0.4"
BASE_MAIN = "9e69a9edb61f0812a312502aabc8377c7aabf62a"
FOUNDATION_TAG = "bolt-on-continuity-v0.3"
FOUNDATION_TARGET = "1c95a1ff8ead30675d4d26f7d77720097c5b9129"
REQUIRED_CAPABILITIES = (
    "single_documented_local_launch_path",
    "single_bounded_demonstration_workflow",
    "deterministic_replayable_receipts",
    "observation_only_default",
    "clear_success_hold_failure_output",
    "second_machine_qualification_before_release",
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class AcceptanceEvidence:
    scope_defined: bool
    capabilities_defined: bool
    exclusions_defined: bool
    evidence_requirements_defined: bool
    authority_denied: bool


@dataclass(frozen=True)
class StageZeroRecord:
    product: str
    stage: int
    base_main: str
    foundation_tag: str
    foundation_target: str
    required_capabilities: tuple[str, ...]
    evidence: AcceptanceEvidence
    status: str
    authority: dict[str, bool]
    record_digest: str

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(asdict(self))


def qualify_stage_zero(evidence: AcceptanceEvidence) -> StageZeroRecord:
    ready = all(asdict(evidence).values())
    body = {
        "product": PRODUCT,
        "stage": 0,
        "base_main": BASE_MAIN,
        "foundation_tag": FOUNDATION_TAG,
        "foundation_target": FOUNDATION_TARGET,
        "required_capabilities": REQUIRED_CAPABILITIES,
        "evidence": asdict(evidence),
        "status": "STAGE_0_QUALIFIED" if ready else "NOT_READY",
        "authority": {
            "installer_execution": False,
            "background_service": False,
            "native_execution": False,
            "docker_mutation": False,
            "automatic_recovery": False,
            "attach_or_distribute_packages": False,
            "publish_release": False,
            "production_claims": False,
        },
    }
    digest = hashlib.sha256(canonical_bytes(body)).hexdigest()
    return StageZeroRecord(**{**body, "evidence": evidence}, record_digest=digest)

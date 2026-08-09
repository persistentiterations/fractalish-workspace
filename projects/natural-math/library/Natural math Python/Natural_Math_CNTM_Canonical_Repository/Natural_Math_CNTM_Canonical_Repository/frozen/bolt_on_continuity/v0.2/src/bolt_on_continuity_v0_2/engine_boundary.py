"""Data-only loader for the frozen v0.1 engine candidate boundary."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_ALLOWED_TOP_LEVEL = {
    "allowed_actions",
    "authoritative_commit",
    "components",
    "frozen_root",
    "product",
    "product_version",
    "schema_version",
    "stage",
}
_ALLOWED_ACTIONS = ["NO_ACTION", "HOLD", "RELEASE"]
_ALLOWED_PROOFS = {
    "adversarial_rejection_equivalence",
    "behavior_equivalence",
    "bounded_observation_equivalence",
    "receipt_and_digest_equivalence",
    "source_and_command_equivalence",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_FROZEN_PREFIX = "frozen/bolt_on_continuity_v0_1/"
_COMPONENT_FIELDS = {
    "component_id",
    "disposition",
    "expected_sha256",
    "future_proof_type",
    "native_docker_authority_present",
    "source_path",
}


class BoundaryValidationError(ValueError):
    """Raised when the data-only engine boundary is malformed or unsafe."""


def load_boundary(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate a Stage 1 frozen-engine boundary manifest."""

    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BoundaryValidationError(f"unable to load boundary: {exc}") from exc

    if not isinstance(payload, dict) or set(payload) != _ALLOWED_TOP_LEVEL:
        raise BoundaryValidationError("unexpected top-level structure")
    if payload["schema_version"] != 1 or payload["stage"] != 1:
        raise BoundaryValidationError("unsupported schema version or stage")
    if payload["allowed_actions"] != _ALLOWED_ACTIONS:
        raise BoundaryValidationError("unexpected action values")
    if payload["frozen_root"] != "frozen/bolt_on_continuity_v0_1":
        raise BoundaryValidationError("unexpected frozen root")
    if not _COMMIT_RE.fullmatch(str(payload["authoritative_commit"])):
        raise BoundaryValidationError("invalid authoritative commit")

    components = payload["components"]
    if not isinstance(components, list) or not components:
        raise BoundaryValidationError("components must be a non-empty list")

    identifiers: set[str] = set()
    for component in components:
        if not isinstance(component, dict) or set(component) != _COMPONENT_FIELDS:
            raise BoundaryValidationError("unexpected component structure")
        component_id = component["component_id"]
        if not isinstance(component_id, str) or not component_id or component_id in identifiers:
            raise BoundaryValidationError("invalid or duplicate component identifier")
        identifiers.add(component_id)
        if component["disposition"] != "candidate_only":
            raise BoundaryValidationError("component is not candidate-only")
        if component["future_proof_type"] not in _ALLOWED_PROOFS:
            raise BoundaryValidationError("unknown future proof type")
        if not isinstance(component["native_docker_authority_present"], bool):
            raise BoundaryValidationError("invalid authority marker")
        if not _SHA256_RE.fullmatch(str(component["expected_sha256"])):
            raise BoundaryValidationError("invalid SHA-256 digest")
        source_path = component["source_path"]
        if not isinstance(source_path, str) or not source_path.startswith(_FROZEN_PREFIX):
            raise BoundaryValidationError("source path escapes frozen boundary")
        if Path(source_path).is_absolute() or ".." in Path(source_path).parts:
            raise BoundaryValidationError("unsafe source path")

    return payload

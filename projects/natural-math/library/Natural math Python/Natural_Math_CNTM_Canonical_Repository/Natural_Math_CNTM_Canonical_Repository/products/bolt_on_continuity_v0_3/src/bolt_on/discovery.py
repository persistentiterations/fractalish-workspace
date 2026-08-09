"""Bounded read-only container discovery and enrollment."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from typing import Callable, Sequence

from .receipts import canonical_json_bytes

FULL_ID = re.compile(r"^[0-9a-f]{64}$")
DISCOVERY_VECTOR = ("docker", "container", "ls", "--all", "--no-trunc", "--format", "{{json .}}")


class DiscoveryError(ValueError):
    """Stable fail-closed Stage 3 error."""


@dataclass(frozen=True)
class ContainerCandidate:
    container_id: str
    names: str
    image: str
    state: str
    status: str

    def body(self) -> dict[str, str]:
        return {
            "container_id": self.container_id,
            "image": self.image,
            "names": self.names,
            "state": self.state,
            "status": self.status,
        }


@dataclass(frozen=True)
class EnrollmentRecord:
    container_id: str
    display_name: str
    image: str
    observed_state: str
    enrollment_digest: str

    def body(self) -> dict[str, object]:
        return {
            "container_id": self.container_id,
            "contract": "bolt-on-continuity-v0.3-stage-3",
            "display_name": self.display_name,
            "enrollment_digest": self.enrollment_digest,
            "gateway_enabled": False,
            "image": self.image,
            "observation_only": True,
            "observed_state": self.observed_state,
            "schema_version": 1,
        }

    def canonical_json(self) -> str:
        return canonical_json_bytes(self.body()).decode("utf-8")


Runner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]


def _run(vector: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(vector, capture_output=True, text=True, timeout=timeout, check=False, shell=False)


def parse_discovery(text: str) -> tuple[ContainerCandidate, ...]:
    found: dict[str, ContainerCandidate] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DiscoveryError("MALFORMED_DISCOVERY") from exc
        if not isinstance(raw, dict):
            raise DiscoveryError("MALFORMED_DISCOVERY")
        cid = raw.get("ID")
        if not isinstance(cid, str) or not FULL_ID.fullmatch(cid):
            raise DiscoveryError("INVALID_CONTAINER_ID")
        if cid in found:
            raise DiscoveryError("DUPLICATE_SUBJECT")
        platform_value = raw.get("Platform") or raw.get("OSType")
        if platform_value is not None and str(platform_value).lower() != "linux":
            raise DiscoveryError("UNSUPPORTED_PLATFORM")
        def bounded(key: str, limit: int = 256) -> str:
            value = raw.get(key, "")
            if not isinstance(value, str) or len(value) > limit:
                raise DiscoveryError("AMBIGUOUS_DISCOVERY")
            return value
        found[cid] = ContainerCandidate(cid, bounded("Names"), bounded("Image"), bounded("State", 64).lower(), bounded("Status"))
    return tuple(found[key] for key in sorted(found))


def discover(runner: Runner = _run, timeout: float = 5.0) -> tuple[ContainerCandidate, ...]:
    try:
        result = runner(DISCOVERY_VECTOR, timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiscoveryError("DISCOVERY_UNAVAILABLE") from exc
    if result.returncode != 0:
        raise DiscoveryError("DISCOVERY_UNAVAILABLE")
    return parse_discovery(result.stdout)


def select(candidates: Sequence[ContainerCandidate], selected_id: str, confirmation_id: str) -> ContainerCandidate:
    if not FULL_ID.fullmatch(selected_id):
        raise DiscoveryError("INVALID_SELECTION")
    if confirmation_id != selected_id:
        raise DiscoveryError("CONFIRMATION_MISMATCH")
    matches = [item for item in candidates if item.container_id == selected_id]
    if len(matches) != 1:
        raise DiscoveryError("INVALID_SELECTION")
    return matches[0]


def inspect_and_enroll(candidate: ContainerCandidate, runner: Runner = _run, timeout: float = 5.0) -> EnrollmentRecord:
    vector = ("docker", "inspect", candidate.container_id)
    try:
        result = runner(vector, timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiscoveryError("INSPECTION_UNAVAILABLE") from exc
    if result.returncode != 0:
        raise DiscoveryError("INSPECTION_UNAVAILABLE")
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DiscoveryError("MALFORMED_INSPECTION") from exc
    if not isinstance(raw, list) or len(raw) != 1 or not isinstance(raw[0], dict):
        raise DiscoveryError("MALFORMED_INSPECTION")
    item = raw[0]
    if item.get("Id") != candidate.container_id:
        raise DiscoveryError("INSPECTION_MISMATCH")
    platform_value = item.get("Platform")
    if platform_value is not None and str(platform_value).lower() != "linux":
        raise DiscoveryError("UNSUPPORTED_PLATFORM")
    name = item.get("Name", candidate.names)
    if isinstance(name, str) and name.startswith("/"):
        name = name[1:]
    if not isinstance(name, str) or len(name) > 256:
        raise DiscoveryError("MALFORMED_INSPECTION")
    base = {
        "container_id": candidate.container_id,
        "contract": "bolt-on-continuity-v0.3-stage-3",
        "display_name": name,
        "gateway_enabled": False,
        "image": candidate.image,
        "observation_only": True,
        "observed_state": candidate.state,
        "schema_version": 1,
    }
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    return EnrollmentRecord(candidate.container_id, name, candidate.image, candidate.state, digest)

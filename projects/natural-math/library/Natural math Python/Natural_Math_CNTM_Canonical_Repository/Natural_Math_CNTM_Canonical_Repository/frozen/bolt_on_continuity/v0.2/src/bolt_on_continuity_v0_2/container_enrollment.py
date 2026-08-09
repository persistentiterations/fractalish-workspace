from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence

FULL_ID = re.compile(r"^[0-9a-f]{64}$")
DISCOVERY_ARGS = ("container", "ls", "--all", "--no-trunc", "--format", "{{json .}}")
INSPECT_PREFIX = ("inspect",)
PROBE_TIMEOUT_SECONDS = 10
SCHEMA_VERSION = "1"
CONTRACT_ID = "BONACQUI_BOLT_ON_CONTINUITY_DOCKER_V0_2_STAGE_3"


class EnrollmentError(ValueError):
    """Stable fail-closed discovery or enrollment failure."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str = ""


@dataclass(frozen=True)
class ContainerCandidate:
    container_id: str
    names: str
    image: str
    state: str
    status: str

    def as_dict(self) -> dict[str, str]:
        return {
            "container_id": self.container_id,
            "image": self.image,
            "names": self.names,
            "state": self.state,
            "status": self.status,
        }


Runner = Callable[[Sequence[str], int], CommandResult]


def _bounded_text(value: object, field: str, limit: int = 512) -> str:
    if not isinstance(value, str):
        raise EnrollmentError(f"INVALID_{field.upper()}")
    cleaned = value.strip()
    if len(cleaned.encode("utf-8")) > limit:
        raise EnrollmentError(f"OVERSIZED_{field.upper()}")
    return cleaned


def _full_id(value: object, reason: str) -> str:
    if not isinstance(value, str) or FULL_ID.fullmatch(value) is None:
        raise EnrollmentError(reason)
    return value


def parse_discovery_jsonl(text: str) -> tuple[ContainerCandidate, ...]:
    candidates: list[ContainerCandidate] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        try:
            item = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise EnrollmentError("MALFORMED_DISCOVERY_JSON") from exc
        if not isinstance(item, dict):
            raise EnrollmentError("MALFORMED_DISCOVERY_RECORD")
        container_id = _full_id(item.get("ID"), "INVALID_DISCOVERY_CONTAINER_ID")
        if container_id in seen:
            raise EnrollmentError("DUPLICATE_DISCOVERY_CONTAINER_ID")
        seen.add(container_id)
        platform = item.get("Platform")
        if platform not in (None, "", "linux"):
            raise EnrollmentError("UNSUPPORTED_CONTAINER_PLATFORM")
        candidates.append(
            ContainerCandidate(
                container_id=container_id,
                names=_bounded_text(item.get("Names", ""), "names"),
                image=_bounded_text(item.get("Image", ""), "image"),
                state=_bounded_text(item.get("State", ""), "state", 64).lower(),
                status=_bounded_text(item.get("Status", ""), "status"),
            )
        )
    return tuple(sorted(candidates, key=lambda value: value.container_id))


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_discovery(candidates: Iterable[ContainerCandidate]) -> str:
    return canonical_json([candidate.as_dict() for candidate in candidates])


def discover_containers(runner: Runner) -> tuple[ContainerCandidate, ...]:
    result = runner(DISCOVERY_ARGS, PROBE_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise EnrollmentError("DISCOVERY_UNAVAILABLE")
    return parse_discovery_jsonl(result.stdout)


def select_candidate(candidates: Iterable[ContainerCandidate], selection: str) -> ContainerCandidate:
    selected_id = _full_id(selection, "INVALID_SELECTION_FULL_ID")
    matches = [candidate for candidate in candidates if candidate.container_id == selected_id]
    if len(matches) != 1:
        raise EnrollmentError("SELECTION_NOT_DISCOVERED")
    return matches[0]


def _parse_inspect(text: str, expected_id: str) -> Mapping[str, object]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EnrollmentError("MALFORMED_INSPECTION_JSON") from exc
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise EnrollmentError("MALFORMED_INSPECTION_RECORD")
    item = payload[0]
    actual_id = _full_id(item.get("Id"), "INVALID_INSPECTION_CONTAINER_ID")
    if actual_id != expected_id:
        raise EnrollmentError("INSPECTION_ID_MISMATCH")
    platform = item.get("Platform")
    if platform not in (None, "", "linux"):
        raise EnrollmentError("UNSUPPORTED_CONTAINER_PLATFORM")
    return item


def _digest_record(record_without_digest: Mapping[str, object]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(record_without_digest).encode("utf-8")).hexdigest()


def enroll_container(
    candidates: Iterable[ContainerCandidate],
    selection: str,
    confirmation: str,
    runner: Runner,
) -> dict[str, object]:
    candidate = select_candidate(candidates, selection)
    if confirmation != candidate.container_id:
        raise EnrollmentError("CONFIRMATION_MISMATCH")
    result = runner(INSPECT_PREFIX + (candidate.container_id,), PROBE_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise EnrollmentError("INSPECTION_UNAVAILABLE")
    inspected = _parse_inspect(result.stdout, candidate.container_id)
    config = inspected.get("Config") if isinstance(inspected.get("Config"), dict) else {}
    state = inspected.get("State") if isinstance(inspected.get("State"), dict) else {}
    name = inspected.get("Name")
    display_name = _bounded_text(name[1:] if isinstance(name, str) and name.startswith("/") else name or candidate.names, "display_name")
    image = _bounded_text(config.get("Image", candidate.image), "image")
    lifecycle = _bounded_text(state.get("Status", candidate.state), "lifecycle_state", 64).lower()
    base: dict[str, object] = {
        "contract_id": CONTRACT_ID,
        "container_id": candidate.container_id,
        "display_name": display_name,
        "gateway_enabled": False,
        "image": image,
        "lifecycle_state": lifecycle,
        "observation_only": True,
        "schema_version": SCHEMA_VERSION,
    }
    return {**base, "enrollment_digest": _digest_record(base)}


def default_runner(arguments: Sequence[str], timeout: int) -> CommandResult:
    completed = subprocess.run(
        ("docker", *arguments),
        capture_output=True,
        check=False,
        shell=False,
        text=True,
        timeout=timeout,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)

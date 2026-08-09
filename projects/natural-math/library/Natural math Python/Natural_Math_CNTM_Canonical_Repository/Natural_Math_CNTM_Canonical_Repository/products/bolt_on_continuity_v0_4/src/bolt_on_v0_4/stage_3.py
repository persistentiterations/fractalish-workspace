"""Bounded Stage 3 container discovery and observation-only enrollment."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
import subprocess
from typing import Mapping, Protocol, Sequence

PRODUCT = "Bolt-On Continuity v0.4"
STAGE = 3
SCHEMA_VERSION = 1
QUALIFIED_STAGE_2_HEAD = "15e29c94d81e5e5eae3ddf384eb8fa6af8ffcdc4"
STAGE_2_QUALIFICATION_RECORD_SHA256 = "97b92c58c6bf342c44dd793bfe0a78401b9c606ecaccd27ca1f9c48cd2d6141e"
STAGE_2_VERIFIER_MANIFEST_SHA256 = "6f1c6c119c8114ed20e84c6d28dc1e9de9000e6df861939e5775373e4d957192"

PROBE_TIMEOUT_SECONDS = 5
MAX_DISCOVERY_BYTES = 1_048_576
MAX_INSPECTION_BYTES = 16_384
MAX_CANDIDATES = 1024
MAX_METADATA_LENGTH = 256
MAX_STATE_LENGTH = 64

FULL_CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_STATES = frozenset(
    {"created", "restarting", "running", "removing", "paused", "exited", "dead"}
)

DISCOVERY_ARGS = (
    "container",
    "ls",
    "--all",
    "--no-trunc",
    "--format",
    "{{json .}}",
)
INSPECTION_TEMPLATE = (
    '{"Id":{{json .Id}},"Name":{{json .Name}},'
    '"Image":{{json .Config.Image}},"State":{{json .State.Status}},'
    '"Platform":{{json .Platform}}}'
)
INSPECTION_PREFIX = (
    "container",
    "inspect",
    "--format",
    INSPECTION_TEMPLATE,
)

AUTHORITY = {
    "docker_prerequisite_probe": True,
    "local_docker_daemon_contact": True,
    "container_enumeration": True,
    "single_container_inspection": True,
    "enrollment_record_construction": True,
    "docker_mutation": False,
    "container_start_stop_restart": False,
    "container_exec": False,
    "container_create_remove": False,
    "container_logs_or_events": False,
    "direct_socket_access": False,
    "filesystem_mutation": False,
    "installer_execution": False,
    "background_service": False,
    "network_contact": False,
    "automatic_recovery": False,
    "attach_or_distribute_packages": False,
    "publish_release": False,
    "production_claims": False,
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class EnrollmentError(ValueError):
    """Stable fail-closed Stage 3 error."""


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class ProbeResult:
    returncode: int
    stdout: str
    stderr: str = ""
    timed_out: bool = False


class DockerRunner(Protocol):
    def run(
        self,
        executable: str,
        args: tuple[str, ...],
        timeout: int,
    ) -> ProbeResult: ...


class SubprocessDockerRunner:
    """Execute only the fixed discovery vector or exact full-ID inspection."""

    def run(
        self,
        executable: str,
        args: tuple[str, ...],
        timeout: int,
    ) -> ProbeResult:
        inspection_allowed = (
            len(args) == len(INSPECTION_PREFIX) + 1
            and args[: len(INSPECTION_PREFIX)] == INSPECTION_PREFIX
            and bool(FULL_CONTAINER_ID.fullmatch(args[-1]))
        )
        if args != DISCOVERY_ARGS and not inspection_allowed:
            raise ValueError("unsupported Stage 3 Docker vector")
        if timeout != PROBE_TIMEOUT_SECONDS:
            raise ValueError("unsupported Stage 3 timeout")
        try:
            completed = subprocess.run(
                [executable, *args],
                capture_output=True,
                text=True,
                shell=False,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ProbeResult(124, "", "timeout", True)
        return ProbeResult(
            completed.returncode,
            completed.stdout,
            completed.stderr,
            False,
        )


@dataclass(frozen=True)
class ContainerCandidate:
    container_id: str
    display_name: str
    image: str
    state: str

    def body(self) -> dict[str, str]:
        return {
            "container_id": self.container_id,
            "display_name": self.display_name,
            "image": self.image,
            "state": self.state,
        }


@dataclass(frozen=True)
class DiscoveryReport:
    product: str
    stage: int
    schema_version: int
    qualified_stage_2_head: str
    stage_2_qualification_record_sha256: str
    stage_2_verifier_manifest_sha256: str
    candidates: tuple[ContainerCandidate, ...]
    authority: Mapping[str, bool]
    status: str
    report_digest: str

    def body_without_digest(self) -> dict[str, object]:
        return {
            "authority": dict(self.authority),
            "candidate_count": len(self.candidates),
            "candidates": [candidate.body() for candidate in self.candidates],
            "product": self.product,
            "qualified_stage_2_head": self.qualified_stage_2_head,
            "schema_version": self.schema_version,
            "stage": self.stage,
            "stage_2_qualification_record_sha256": self.stage_2_qualification_record_sha256,
            "stage_2_verifier_manifest_sha256": self.stage_2_verifier_manifest_sha256,
            "status": self.status,
        }

    def body(self) -> dict[str, object]:
        return {**self.body_without_digest(), "report_digest": self.report_digest}

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.body())

    def canonical_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")


@dataclass(frozen=True)
class EnrollmentRecord:
    product: str
    stage: int
    schema_version: int
    qualified_stage_2_head: str
    stage_2_qualification_record_sha256: str
    stage_2_verifier_manifest_sha256: str
    container_id: str
    display_name: str
    image: str
    observed_state: str
    platform: str
    authority: Mapping[str, bool]
    status: str
    record_digest: str

    def body_without_digest(self) -> dict[str, object]:
        return {
            "authority": dict(self.authority),
            "container_id": self.container_id,
            "display_name": self.display_name,
            "image": self.image,
            "observed_state": self.observed_state,
            "platform": self.platform,
            "product": self.product,
            "qualified_stage_2_head": self.qualified_stage_2_head,
            "schema_version": self.schema_version,
            "stage": self.stage,
            "stage_2_qualification_record_sha256": self.stage_2_qualification_record_sha256,
            "stage_2_verifier_manifest_sha256": self.stage_2_verifier_manifest_sha256,
            "status": self.status,
        }

    def body(self) -> dict[str, object]:
        return {**self.body_without_digest(), "record_digest": self.record_digest}

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.body())

    def canonical_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")


def _bounded_string(
    raw: Mapping[str, object],
    key: str,
    *,
    limit: int = MAX_METADATA_LENGTH,
    allow_empty: bool = False,
) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise EnrollmentError("MALFORMED_METADATA")
    value = value.strip()
    if (not value and not allow_empty) or len(value) > limit:
        raise EnrollmentError("AMBIGUOUS_METADATA")
    return value


def parse_discovery(text: str) -> tuple[ContainerCandidate, ...]:
    if len(text.encode("utf-8")) > MAX_DISCOVERY_BYTES:
        raise EnrollmentError("DISCOVERY_OUTPUT_TOO_LARGE")
    found: dict[str, ContainerCandidate] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EnrollmentError("MALFORMED_DISCOVERY") from exc
        if not isinstance(raw, dict):
            raise EnrollmentError("MALFORMED_DISCOVERY")
        container_id = raw.get("ID")
        if not isinstance(container_id, str) or not FULL_CONTAINER_ID.fullmatch(
            container_id
        ):
            raise EnrollmentError("INVALID_CONTAINER_ID")
        if container_id in found:
            raise EnrollmentError("DUPLICATE_CONTAINER_ID")
        display_name = _bounded_string(raw, "Names")
        image = _bounded_string(raw, "Image")
        state = _bounded_string(raw, "State", limit=MAX_STATE_LENGTH).lower()
        if state not in ALLOWED_STATES:
            raise EnrollmentError("UNSUPPORTED_CONTAINER_STATE")
        found[container_id] = ContainerCandidate(
            container_id,
            display_name,
            image,
            state,
        )
        if len(found) > MAX_CANDIDATES:
            raise EnrollmentError("TOO_MANY_CANDIDATES")
    return tuple(found[key] for key in sorted(found))


def build_discovery_report(
    candidates: Sequence[ContainerCandidate],
) -> DiscoveryReport:
    ordered = tuple(sorted(candidates, key=lambda candidate: candidate.container_id))
    body = {
        "authority": dict(AUTHORITY),
        "candidate_count": len(ordered),
        "candidates": [candidate.body() for candidate in ordered],
        "product": PRODUCT,
        "qualified_stage_2_head": QUALIFIED_STAGE_2_HEAD,
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "stage_2_qualification_record_sha256": STAGE_2_QUALIFICATION_RECORD_SHA256,
        "stage_2_verifier_manifest_sha256": STAGE_2_VERIFIER_MANIFEST_SHA256,
        "status": "STAGE_3_DISCOVERY_READY",
    }
    return DiscoveryReport(
        product=PRODUCT,
        stage=STAGE,
        schema_version=SCHEMA_VERSION,
        qualified_stage_2_head=QUALIFIED_STAGE_2_HEAD,
        stage_2_qualification_record_sha256=STAGE_2_QUALIFICATION_RECORD_SHA256,
        stage_2_verifier_manifest_sha256=STAGE_2_VERIFIER_MANIFEST_SHA256,
        candidates=ordered,
        authority=dict(AUTHORITY),
        status="STAGE_3_DISCOVERY_READY",
        report_digest=sha256(canonical_bytes(body)),
    )


def discover_candidates(
    executable: str,
    runner: DockerRunner | None = None,
) -> DiscoveryReport:
    if not executable:
        raise EnrollmentError("DOCKER_CLI_MISSING")
    active_runner = runner or SubprocessDockerRunner()
    try:
        result = active_runner.run(
            executable,
            DISCOVERY_ARGS,
            PROBE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EnrollmentError("DISCOVERY_UNAVAILABLE") from exc
    if result.timed_out:
        raise EnrollmentError("DISCOVERY_TIMEOUT")
    if result.returncode != 0:
        raise EnrollmentError("DISCOVERY_UNAVAILABLE")
    return build_discovery_report(parse_discovery(result.stdout))


def select_candidate(
    candidates: Sequence[ContainerCandidate],
    selected_id: str,
    confirmation_id: str,
) -> ContainerCandidate:
    if not FULL_CONTAINER_ID.fullmatch(selected_id):
        raise EnrollmentError("INVALID_SELECTION")
    if confirmation_id != selected_id:
        raise EnrollmentError("CONFIRMATION_MISMATCH")
    matches = [
        candidate
        for candidate in candidates
        if candidate.container_id == selected_id
    ]
    if len(matches) != 1:
        raise EnrollmentError("UNKNOWN_SELECTION")
    return matches[0]


def _parse_inspection(
    text: str,
    candidate: ContainerCandidate,
) -> tuple[str, str, str, str, str]:
    if len(text.encode("utf-8")) > MAX_INSPECTION_BYTES:
        raise EnrollmentError("INSPECTION_OUTPUT_TOO_LARGE")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EnrollmentError("MALFORMED_INSPECTION") from exc
    if not isinstance(raw, dict):
        raise EnrollmentError("MALFORMED_INSPECTION")

    container_id = _bounded_string(raw, "Id", limit=64)
    if container_id != candidate.container_id:
        raise EnrollmentError("INSPECTION_IDENTITY_MISMATCH")
    name = _bounded_string(raw, "Name")
    if name.startswith("/"):
        name = name[1:]
    if not name or name != candidate.display_name:
        raise EnrollmentError("INSPECTION_NAME_MISMATCH")
    image = _bounded_string(raw, "Image")
    if image != candidate.image:
        raise EnrollmentError("INSPECTION_IMAGE_MISMATCH")
    state = _bounded_string(raw, "State", limit=MAX_STATE_LENGTH).lower()
    if state not in ALLOWED_STATES:
        raise EnrollmentError("UNSUPPORTED_CONTAINER_STATE")
    platform = _bounded_string(raw, "Platform", limit=MAX_STATE_LENGTH).lower()
    if platform != "linux":
        raise EnrollmentError("UNSUPPORTED_PLATFORM")
    return container_id, name, image, state, platform


def inspect_and_enroll(
    executable: str,
    candidate: ContainerCandidate,
    runner: DockerRunner | None = None,
) -> EnrollmentRecord:
    if not executable:
        raise EnrollmentError("DOCKER_CLI_MISSING")
    active_runner = runner or SubprocessDockerRunner()
    args = (*INSPECTION_PREFIX, candidate.container_id)
    try:
        result = active_runner.run(
            executable,
            args,
            PROBE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EnrollmentError("INSPECTION_UNAVAILABLE") from exc
    if result.timed_out:
        raise EnrollmentError("INSPECTION_TIMEOUT")
    if result.returncode != 0:
        raise EnrollmentError("INSPECTION_UNAVAILABLE")
    container_id, name, image, state, platform = _parse_inspection(
        result.stdout,
        candidate,
    )
    body = {
        "authority": dict(AUTHORITY),
        "container_id": container_id,
        "display_name": name,
        "image": image,
        "observed_state": state,
        "platform": platform,
        "product": PRODUCT,
        "qualified_stage_2_head": QUALIFIED_STAGE_2_HEAD,
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "stage_2_qualification_record_sha256": STAGE_2_QUALIFICATION_RECORD_SHA256,
        "stage_2_verifier_manifest_sha256": STAGE_2_VERIFIER_MANIFEST_SHA256,
        "status": "STAGE_3_ENROLLED",
    }
    return EnrollmentRecord(
        product=PRODUCT,
        stage=STAGE,
        schema_version=SCHEMA_VERSION,
        qualified_stage_2_head=QUALIFIED_STAGE_2_HEAD,
        stage_2_qualification_record_sha256=STAGE_2_QUALIFICATION_RECORD_SHA256,
        stage_2_verifier_manifest_sha256=STAGE_2_VERIFIER_MANIFEST_SHA256,
        container_id=container_id,
        display_name=name,
        image=image,
        observed_state=state,
        platform=platform,
        authority=dict(AUTHORITY),
        status="STAGE_3_ENROLLED",
        record_digest=sha256(canonical_bytes(body)),
    )


def render_discovery_human(report: DiscoveryReport) -> str:
    lines = [
        f"CANDIDATE {candidate.container_id} "
        f"name={candidate.display_name} image={candidate.image} "
        f"state={candidate.state}"
        for candidate in report.candidates
    ]
    if not lines:
        lines.append("NO CONTAINERS DISCOVERED")
    lines.append(report.status)
    lines.append(f"REPORT SHA-256 {report.report_digest}")
    return "\n".join(lines)


def render_enrollment_human(record: EnrollmentRecord) -> str:
    lines = [
        f"PASS stage2.binding: {record.qualified_stage_2_head}",
        f"PASS container.id: {record.container_id}",
        f"PASS container.name: {record.display_name}",
        f"PASS container.image: {record.image}",
        f"PASS container.state: {record.observed_state}",
        f"PASS container.platform: {record.platform}",
        "PASS authority.boundary: OBSERVATION_ONLY_ENROLLMENT",
        record.status,
        f"RECORD SHA-256 {record.record_digest}",
    ]
    return "\n".join(lines)

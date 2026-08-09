"""Bounded Stage 2 Docker prerequisite qualification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from typing import Mapping, Protocol

PRODUCT = "Bolt-On Continuity v0.4"
STAGE = 2
SCHEMA_VERSION = 1
MINIMUM_PYTHON = (3, 11, 0)
QUALIFIED_STAGE_1_HEAD = "5cfc92e205d99e34ef02376ff0c560a62bbbf435"
STAGE_1_QUALIFICATION_RECORD_SHA256 = "9fcd999f9d1e3817f53a60ff9b61193ec0576d808b14bdbbb7d806e86a83da2b"
STAGE_1_VERIFIER_MANIFEST_SHA256 = "d94edb9ada5857f56d2785ae81dcf58768791fda46e7c1fc6e13c74ac57eaf18"
PROBE_TIMEOUT_SECONDS = 5
VERSION_ARGS = ("version", "--format", "{{json .}}")
INFO_ARGS = ("info", "--format", "{{json .}}")
CONTEXT_ARGS = ("context", "inspect", "--format", "{{json .}}")
ALLOWED_PROBE_VECTORS = (CONTEXT_ARGS, VERSION_ARGS, INFO_ARGS)
REMOTE_OVERRIDE_KEYS = (
    "DOCKER_HOST",
    "DOCKER_CONTEXT",
    "DOCKER_TLS_VERIFY",
    "DOCKER_CERT_PATH",
)
AUTHORITY = {
    "docker_prerequisite_probe": True,
    "local_docker_daemon_contact": True,
    "docker_mutation": False,
    "container_enumeration": False,
    "container_inspection": False,
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


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class ProbeResult:
    returncode: int
    stdout: str
    stderr: str = ""
    timed_out: bool = False


class ProbeRunner(Protocol):
    def run(
        self,
        executable: str,
        args: tuple[str, ...],
        timeout: int,
    ) -> ProbeResult: ...


class SubprocessProbeRunner:
    """Execute only the fixed Stage 2 read-only Docker vectors."""

    def run(
        self,
        executable: str,
        args: tuple[str, ...],
        timeout: int,
    ) -> ProbeResult:
        if args not in ALLOWED_PROBE_VECTORS:
            raise ValueError("unsupported Docker prerequisite probe vector")
        if timeout != PROBE_TIMEOUT_SECONDS:
            raise ValueError("unsupported Docker prerequisite probe timeout")
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
class QualificationInput:
    python_implementation: str
    python_version: tuple[int, int, int]
    platform_system: str
    docker_cli_present: bool
    remote_override_present: bool
    context_result: ProbeResult | None
    version_result: ProbeResult | None
    info_result: ProbeResult | None


@dataclass(frozen=True)
class QualificationCheck:
    check_id: str
    status: CheckStatus
    summary: str
    detail: str

    def body(self) -> dict[str, str]:
        return {
            "check_id": self.check_id,
            "detail": self.detail,
            "status": self.status.value,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class PrerequisiteReport:
    product: str
    stage: int
    schema_version: int
    qualified_stage_1_head: str
    stage_1_qualification_record_sha256: str
    stage_1_verifier_manifest_sha256: str
    probe_timeout_seconds: int
    probe_vectors: tuple[tuple[str, ...], ...]
    checks: tuple[QualificationCheck, ...]
    reason_codes: tuple[str, ...]
    status: str
    authority: Mapping[str, bool]
    report_digest: str

    def body_without_digest(self) -> dict[str, object]:
        return {
            "authority": dict(self.authority),
            "checks": [check.body() for check in self.checks],
            "probe_timeout_seconds": self.probe_timeout_seconds,
            "probe_vectors": [list(vector) for vector in self.probe_vectors],
            "product": self.product,
            "qualified_stage_1_head": self.qualified_stage_1_head,
            "reason_codes": list(self.reason_codes),
            "schema_version": self.schema_version,
            "stage": self.stage,
            "stage_1_qualification_record_sha256": self.stage_1_qualification_record_sha256,
            "stage_1_verifier_manifest_sha256": self.stage_1_verifier_manifest_sha256,
            "status": self.status,
        }

    def body(self) -> dict[str, object]:
        return {**self.body_without_digest(), "report_digest": self.report_digest}

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.body())

    def canonical_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")

    @property
    def eligible(self) -> bool:
        return self.status == "STAGE_2_ELIGIBLE"


def _parse_json_object(result: ProbeResult | None) -> Mapping[str, object] | None:
    if result is None or result.timed_out or result.returncode != 0:
        return None
    try:
        value = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _context_endpoint(context: Mapping[str, object] | None) -> str | None:
    if context is None:
        return None
    endpoints = context.get("Endpoints")
    if not isinstance(endpoints, dict):
        return None
    docker_endpoint = endpoints.get("docker")
    if not isinstance(docker_endpoint, dict):
        return None
    host = docker_endpoint.get("Host")
    return host if isinstance(host, str) and host else None


def _local_endpoint(endpoint: str | None) -> bool:
    if endpoint is None:
        return False
    normalized = endpoint.strip().lower()
    return normalized.startswith("unix://") or normalized.startswith("npipe://")


def _version_value(
    version: Mapping[str, object] | None,
    section: str,
) -> str | None:
    if version is None:
        return None
    value = version.get(section)
    if not isinstance(value, dict):
        return None
    candidate = value.get("Version")
    return candidate if isinstance(candidate, str) and candidate else None


def qualify_prerequisites(data: QualificationInput) -> PrerequisiteReport:
    context = _parse_json_object(data.context_result)
    version = _parse_json_object(data.version_result)
    info = _parse_json_object(data.info_result)
    endpoint = _context_endpoint(context)
    local_context = _local_endpoint(endpoint)
    client_version = _version_value(version, "Client")
    server_version = _version_value(version, "Server")
    engine_os = info.get("OSType") if isinstance(info, dict) else None
    engine_linux = isinstance(engine_os, str) and engine_os.lower() == "linux"
    python_ok = (
        data.python_implementation == "CPython"
        and data.python_version >= MINIMUM_PYTHON
    )
    platform_ok = data.platform_system.strip().lower() in {"windows", "linux"}

    results = (
        (True, "STAGE_1_BINDING_MISMATCH"),
        (python_ok, "UNSUPPORTED_PYTHON"),
        (platform_ok, "UNSUPPORTED_PLATFORM"),
        (data.docker_cli_present, "DOCKER_CLI_MISSING"),
        (not data.remote_override_present, "REMOTE_OVERRIDE_PRESENT"),
        (context is not None, "CONTEXT_PROBE_UNAVAILABLE"),
        (local_context, "REMOTE_OR_AMBIGUOUS_CONTEXT"),
        (client_version is not None, "DOCKER_CLIENT_UNAVAILABLE"),
        (server_version is not None, "DOCKER_SERVER_UNAVAILABLE"),
        (info is not None, "DOCKER_INFO_UNAVAILABLE"),
        (engine_linux, "ENGINE_NOT_LINUX"),
    )
    reason_codes = tuple(code for passed, code in results if not passed)

    checks = (
        QualificationCheck(
            "stage1.binding",
            CheckStatus.PASS,
            "Qualified Stage 1 binding",
            QUALIFIED_STAGE_1_HEAD,
        ),
        QualificationCheck(
            "python.version",
            CheckStatus.PASS if python_ok else CheckStatus.FAIL,
            "Python implementation and version",
            f"{data.python_implementation} "
            + ".".join(str(part) for part in data.python_version),
        ),
        QualificationCheck(
            "platform.system",
            CheckStatus.PASS if platform_ok else CheckStatus.FAIL,
            "Operating-system family",
            data.platform_system.strip() or "unknown",
        ),
        QualificationCheck(
            "docker.cli",
            CheckStatus.PASS if data.docker_cli_present else CheckStatus.FAIL,
            "Docker CLI availability",
            "PRESENT" if data.docker_cli_present else "MISSING",
        ),
        QualificationCheck(
            "docker.environment_override",
            CheckStatus.PASS if not data.remote_override_present else CheckStatus.FAIL,
            "Remote Docker environment overrides",
            "CLEAR" if not data.remote_override_present else "BLOCKED",
        ),
        QualificationCheck(
            "docker.context",
            CheckStatus.PASS if local_context else CheckStatus.FAIL,
            "Current Docker context endpoint class",
            "LOCAL" if local_context else "UNAVAILABLE_OR_REMOTE",
        ),
        QualificationCheck(
            "docker.client_version",
            CheckStatus.PASS if client_version else CheckStatus.FAIL,
            "Docker client response",
            client_version or "unavailable",
        ),
        QualificationCheck(
            "docker.server_version",
            CheckStatus.PASS if server_version else CheckStatus.FAIL,
            "Docker server response",
            server_version or "unavailable",
        ),
        QualificationCheck(
            "docker.engine_os",
            CheckStatus.PASS if engine_linux else CheckStatus.FAIL,
            "Docker engine operating system",
            engine_os if isinstance(engine_os, str) else "unavailable",
        ),
        QualificationCheck(
            "authority.boundary",
            CheckStatus.PASS,
            "Stage 2 authority",
            "BOUNDED_LOCAL_PREREQUISITE_PROBE_ONLY",
        ),
    )
    body = {
        "authority": dict(AUTHORITY),
        "checks": [check.body() for check in checks],
        "probe_timeout_seconds": PROBE_TIMEOUT_SECONDS,
        "probe_vectors": [list(vector) for vector in ALLOWED_PROBE_VECTORS],
        "product": PRODUCT,
        "qualified_stage_1_head": QUALIFIED_STAGE_1_HEAD,
        "reason_codes": list(reason_codes),
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "stage_1_qualification_record_sha256": STAGE_1_QUALIFICATION_RECORD_SHA256,
        "stage_1_verifier_manifest_sha256": STAGE_1_VERIFIER_MANIFEST_SHA256,
        "status": "STAGE_2_ELIGIBLE" if not reason_codes else "NOT_ELIGIBLE",
    }
    digest = sha256(canonical_bytes(body))
    return PrerequisiteReport(
        product=PRODUCT,
        stage=STAGE,
        schema_version=SCHEMA_VERSION,
        qualified_stage_1_head=QUALIFIED_STAGE_1_HEAD,
        stage_1_qualification_record_sha256=STAGE_1_QUALIFICATION_RECORD_SHA256,
        stage_1_verifier_manifest_sha256=STAGE_1_VERIFIER_MANIFEST_SHA256,
        probe_timeout_seconds=PROBE_TIMEOUT_SECONDS,
        probe_vectors=ALLOWED_PROBE_VECTORS,
        checks=checks,
        reason_codes=reason_codes,
        status=body["status"],
        authority=dict(AUTHORITY),
        report_digest=digest,
    )


def collect_and_qualify(
    runner: ProbeRunner | None = None,
    environment: Mapping[str, str] | None = None,
) -> PrerequisiteReport:
    active_environment = os.environ if environment is None else environment
    remote_override_present = any(
        bool(active_environment.get(key)) for key in REMOTE_OVERRIDE_KEYS
    )
    executable = shutil.which("docker")
    active_runner = runner or SubprocessProbeRunner()

    context_result: ProbeResult | None = None
    version_result: ProbeResult | None = None
    info_result: ProbeResult | None = None

    if executable and not remote_override_present:
        context_result = active_runner.run(
            executable,
            CONTEXT_ARGS,
            PROBE_TIMEOUT_SECONDS,
        )
        context = _parse_json_object(context_result)
        if _local_endpoint(_context_endpoint(context)):
            version_result = active_runner.run(
                executable,
                VERSION_ARGS,
                PROBE_TIMEOUT_SECONDS,
            )
            info_result = active_runner.run(
                executable,
                INFO_ARGS,
                PROBE_TIMEOUT_SECONDS,
            )

    return qualify_prerequisites(
        QualificationInput(
            python_implementation=platform.python_implementation(),
            python_version=(
                sys.version_info.major,
                sys.version_info.minor,
                sys.version_info.micro,
            ),
            platform_system=platform.system(),
            docker_cli_present=executable is not None,
            remote_override_present=remote_override_present,
            context_result=context_result,
            version_result=version_result,
            info_result=info_result,
        )
    )


def render_human(report: PrerequisiteReport) -> str:
    lines = [
        f"{check.status.value:4} {check.check_id}: {check.detail}"
        for check in report.checks
    ]
    if report.reason_codes:
        lines.append("REASON CODES " + ",".join(report.reason_codes))
    lines.append(report.status)
    lines.append(f"REPORT SHA-256 {report.report_digest}")
    return "\n".join(lines)

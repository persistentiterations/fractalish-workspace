"""Deterministic, read-only Stage 1 prerequisite doctor."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import PurePath, PurePosixPath, PureWindowsPath
from typing import Mapping

PRODUCT = "Bolt-On Continuity v0.4"
STAGE = 1
SCHEMA_VERSION = 1
MINIMUM_PYTHON = (3, 11, 0)
QUALIFIED_STAGE_0_HEAD = "3ffbaa56b7cf8bb8d74cd33b2f0ca6008ce79018"
STAGE_0_QUALIFICATION_RECORD_SHA256 = "fbe8043e56285446a4b07ef4cdf011e08b9ea772813fc20a37f8118f743e9f69"
STAGE_0_VERIFIER_MANIFEST_SHA256 = "650c4e222f6554bd6c67188478a464f92dd884ea3e1949a7b7b27311997c7279"
AUTHORITY = {
    "installer_execution": False,
    "background_service": False,
    "native_execution": False,
    "docker_contact": False,
    "docker_mutation": False,
    "filesystem_mutation": False,
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


class CheckStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class EnvironmentSnapshot:
    python_version: tuple[int, int, int]
    platform_system: str
    environment: Mapping[str, str]
    docker_cli_path: str | None


@dataclass(frozen=True)
class DoctorCheck:
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
class DoctorReport:
    product: str
    stage: int
    schema_version: int
    qualified_stage_0_head: str
    stage_0_qualification_record_sha256: str
    stage_0_verifier_manifest_sha256: str
    checks: tuple[DoctorCheck, ...]
    status: str
    authority: Mapping[str, bool]
    report_digest: str

    def body_without_digest(self) -> dict[str, object]:
        return {
            "authority": dict(self.authority),
            "checks": [check.body() for check in self.checks],
            "product": self.product,
            "qualified_stage_0_head": self.qualified_stage_0_head,
            "schema_version": self.schema_version,
            "stage": self.stage,
            "stage_0_qualification_record_sha256": self.stage_0_qualification_record_sha256,
            "stage_0_verifier_manifest_sha256": self.stage_0_verifier_manifest_sha256,
            "status": self.status,
        }

    def body(self) -> dict[str, object]:
        return {**self.body_without_digest(), "report_digest": self.report_digest}

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.body())

    def canonical_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")

    @property
    def ready(self) -> bool:
        return self.status == "STAGE_1_READY"


def recommended_data_directory(snapshot: EnvironmentSnapshot) -> PurePath:
    system = snapshot.platform_system.strip().lower()
    environment = snapshot.environment
    if system == "windows":
        base = (
            environment.get("LOCALAPPDATA")
            or environment.get("APPDATA")
            or environment.get("USERPROFILE")
            or "C:/Users/Default/AppData/Local"
        )
        return PureWindowsPath(base) / "BoltOn" / "Continuity" / "v0.4"
    if system == "linux":
        state_home = environment.get("XDG_STATE_HOME")
        if state_home:
            return PurePosixPath(state_home) / "bolt-on-continuity" / "v0.4"
        home = environment.get("HOME") or "/tmp"
        return PurePosixPath(home) / ".local" / "state" / "bolt-on-continuity" / "v0.4"
    home = environment.get("HOME") or "/tmp"
    return PurePosixPath(home) / ".bolt-on-continuity" / "v0.4"


def build_doctor_report(snapshot: EnvironmentSnapshot) -> DoctorReport:
    python_ok = snapshot.python_version >= MINIMUM_PYTHON
    system = snapshot.platform_system.strip().lower()
    platform_supported = system in {"windows", "linux"}
    docker_found = bool(snapshot.docker_cli_path)
    data_path = recommended_data_directory(snapshot)

    checks = (
        DoctorCheck(
            "stage0.binding",
            CheckStatus.PASS,
            "Qualified Stage 0 binding",
            QUALIFIED_STAGE_0_HEAD,
        ),
        DoctorCheck(
            "python.version",
            CheckStatus.PASS if python_ok else CheckStatus.FAIL,
            "Python version",
            ".".join(str(part) for part in snapshot.python_version),
        ),
        DoctorCheck(
            "platform.system",
            CheckStatus.PASS if platform_supported else CheckStatus.WARN,
            "Operating-system family",
            snapshot.platform_system.strip() or "unknown",
        ),
        DoctorCheck(
            "docker.cli",
            CheckStatus.PASS if docker_found else CheckStatus.WARN,
            "Docker CLI path discovery",
            snapshot.docker_cli_path or "not found on PATH",
        ),
        DoctorCheck(
            "storage.recommended_path",
            CheckStatus.PASS,
            "Recommended future data path",
            str(data_path),
        ),
        DoctorCheck(
            "authority.boundary",
            CheckStatus.PASS,
            "Operational and release authority",
            "ALL_DENIED",
        ),
    )
    ready = all(check.status is not CheckStatus.FAIL for check in checks)
    body = {
        "authority": dict(AUTHORITY),
        "checks": [check.body() for check in checks],
        "product": PRODUCT,
        "qualified_stage_0_head": QUALIFIED_STAGE_0_HEAD,
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "stage_0_qualification_record_sha256": STAGE_0_QUALIFICATION_RECORD_SHA256,
        "stage_0_verifier_manifest_sha256": STAGE_0_VERIFIER_MANIFEST_SHA256,
        "status": "STAGE_1_READY" if ready else "NOT_READY",
    }
    digest = sha256(canonical_bytes(body))
    return DoctorReport(
        product=PRODUCT,
        stage=STAGE,
        schema_version=SCHEMA_VERSION,
        qualified_stage_0_head=QUALIFIED_STAGE_0_HEAD,
        stage_0_qualification_record_sha256=STAGE_0_QUALIFICATION_RECORD_SHA256,
        stage_0_verifier_manifest_sha256=STAGE_0_VERIFIER_MANIFEST_SHA256,
        checks=checks,
        status=body["status"],
        authority=dict(AUTHORITY),
        report_digest=digest,
    )


def render_human(report: DoctorReport) -> str:
    lines = [
        f"{check.status.value:4} {check.check_id}: {check.detail}"
        for check in report.checks
    ]
    lines.append(report.status)
    lines.append(f"REPORT SHA-256 {report.report_digest}")
    return "\n".join(lines)

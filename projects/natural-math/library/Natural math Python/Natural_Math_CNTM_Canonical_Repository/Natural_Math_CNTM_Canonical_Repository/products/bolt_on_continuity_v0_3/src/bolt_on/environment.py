"""Read-only prerequisite and environment detection."""

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import PurePath, PurePosixPath, PureWindowsPath
from typing import Mapping, Sequence

from .core import AuthorityClass
from .receipts import canonical_json_bytes


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


@dataclass(frozen=True)
class DoctorReport:
    schema_version: int
    authority_class: str
    checks: tuple[DoctorCheck, ...]

    def body(self) -> dict[str, object]:
        return {
            "authority_class": self.authority_class,
            "checks": [
                {
                    "check_id": check.check_id,
                    "detail": check.detail,
                    "status": check.status.value,
                    "summary": check.summary,
                }
                for check in self.checks
            ],
            "schema_version": self.schema_version,
        }

    def canonical_json(self) -> str:
        return canonical_json_bytes(self.body()).decode("utf-8")

    @property
    def ready(self) -> bool:
        return all(check.status is not CheckStatus.FAIL for check in self.checks)


def recommended_data_directory(snapshot: EnvironmentSnapshot) -> PurePath:
    system = snapshot.platform_system.lower()
    env = snapshot.environment
    if system == "windows":
        base = env.get("LOCALAPPDATA") or env.get("APPDATA") or env.get("USERPROFILE") or "C:/Users/Default"
        return PureWindowsPath(base) / "BoltOn" / "Continuity"
    home = env.get("XDG_STATE_HOME") or env.get("HOME") or "/tmp"
    if env.get("XDG_STATE_HOME"):
        return PurePosixPath(home) / "bolt-on" / "continuity"
    return PurePosixPath(home) / ".local" / "state" / "bolt-on" / "continuity"


def build_doctor_report(snapshot: EnvironmentSnapshot) -> DoctorReport:
    py_ok = snapshot.python_version >= (3, 11, 0)
    system = snapshot.platform_system.lower()
    os_ok = system in {"windows", "linux"}
    docker_found = snapshot.docker_cli_path is not None
    data_path = recommended_data_directory(snapshot)
    checks = (
        DoctorCheck("python.version", CheckStatus.PASS if py_ok else CheckStatus.FAIL, "Python version", ".".join(map(str, snapshot.python_version))),
        DoctorCheck("platform.system", CheckStatus.PASS if os_ok else CheckStatus.WARN, "Operating system", snapshot.platform_system or "unknown"),
        DoctorCheck("docker.cli", CheckStatus.PASS if docker_found else CheckStatus.WARN, "Docker CLI discovery", snapshot.docker_cli_path or "not found on PATH"),
        DoctorCheck("storage.recommended_path", CheckStatus.PASS, "Recommended local data path", str(data_path)),
        DoctorCheck("authority.mode", CheckStatus.PASS, "Authority mode", AuthorityClass.OBSERVATION_ONLY.value),
    )
    return DoctorReport(1, AuthorityClass.OBSERVATION_ONLY.value, checks)

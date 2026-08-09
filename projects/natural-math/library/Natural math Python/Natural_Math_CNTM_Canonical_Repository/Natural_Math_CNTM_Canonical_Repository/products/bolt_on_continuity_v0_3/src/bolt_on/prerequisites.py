"""Bounded, read-only Docker prerequisite qualification."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from .receipts import canonical_json_bytes

VERSION_ARGS = ("version", "--format", "{{json .}}")
INFO_ARGS = ("info", "--format", "{{json .}}")
PROBE_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class ProbeResult:
    returncode: int
    stdout: str
    stderr: str = ""
    timed_out: bool = False


class ProbeRunner(Protocol):
    def run(self, executable: str, args: tuple[str, ...], timeout: int) -> ProbeResult: ...


class SubprocessProbeRunner:
    def run(self, executable: str, args: tuple[str, ...], timeout: int) -> ProbeResult:
        if args not in {VERSION_ARGS, INFO_ARGS}:
            raise ValueError("unsupported Docker probe vector")
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
        return ProbeResult(completed.returncode, completed.stdout, completed.stderr, False)


@dataclass(frozen=True)
class QualificationInput:
    python_implementation: str
    python_version: tuple[int, int, int]
    host_family: str
    machine: str
    docker_cli_present: bool
    version_result: ProbeResult | None
    info_result: ProbeResult | None


@dataclass(frozen=True)
class PrerequisiteReport:
    schema_version: int
    stage: str
    eligible: bool
    reason_codes: tuple[str, ...]
    details: Mapping[str, object]

    def body(self) -> dict[str, object]:
        return {
            "details": dict(self.details),
            "eligible": self.eligible,
            "reason_codes": list(self.reason_codes),
            "schema_version": self.schema_version,
            "stage": self.stage,
        }

    def canonical_json(self) -> str:
        return canonical_json_bytes(self.body()).decode("utf-8")


def _parse_json(result: ProbeResult | None) -> Mapping[str, object] | None:
    if result is None or result.timed_out or result.returncode != 0:
        return None
    try:
        value = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def qualify_host(data: QualificationInput) -> PrerequisiteReport:
    reasons: list[str] = []
    host = data.host_family.lower()
    supported_host = host in {"windows", "linux"}
    python_ok = data.python_implementation == "CPython" and data.python_version >= (3, 11, 0)
    version = _parse_json(data.version_result)
    info = _parse_json(data.info_result)
    client_version = None
    server_version = None
    engine_os = None
    local_engine = False

    if version:
        client = version.get("Client")
        server = version.get("Server")
        if isinstance(client, dict):
            client_version = client.get("Version")
        if isinstance(server, dict):
            server_version = server.get("Version")
    if info:
        engine_os = info.get("OSType")
        context = info.get("Name")
        remote = info.get("DockerRootDir") is None and info.get("Name") not in {None, "default", "desktop-linux"}
        local_engine = not remote and context in {None, "default", "desktop-linux"}

    checks = (
        (supported_host, "UNSUPPORTED_HOST"),
        (python_ok, "UNSUPPORTED_PYTHON"),
        (data.docker_cli_present, "DOCKER_CLI_MISSING"),
        (client_version is not None, "DOCKER_CLIENT_UNAVAILABLE"),
        (server_version is not None, "DOCKER_SERVER_UNAVAILABLE"),
        (engine_os == "linux", "ENGINE_NOT_LINUX"),
        (local_engine, "REMOTE_OR_AMBIGUOUS_ENGINE"),
    )
    for passed, code in checks:
        if not passed:
            reasons.append(code)

    details = {
        "docker_cli_present": data.docker_cli_present,
        "docker_client_version": client_version,
        "docker_server_version": server_version,
        "engine_os_type": engine_os,
        "gateway_enabled": False,
        "host_family": data.host_family,
        "local_engine": local_engine,
        "machine": data.machine,
        "observation_only": True,
        "python_implementation": data.python_implementation,
        "python_version": ".".join(map(str, data.python_version)),
    }
    return PrerequisiteReport(1, "v0.3-stage-2", not reasons, tuple(reasons), details)


def collect_and_qualify(runner: ProbeRunner | None = None) -> PrerequisiteReport:
    executable = shutil.which("docker")
    active_runner = runner or SubprocessProbeRunner()
    version_result = active_runner.run(executable, VERSION_ARGS, PROBE_TIMEOUT_SECONDS) if executable else None
    info_result = active_runner.run(executable, INFO_ARGS, PROBE_TIMEOUT_SECONDS) if executable else None
    data = QualificationInput(
        platform.python_implementation(),
        (sys.version_info.major, sys.version_info.minor, sys.version_info.micro),
        platform.system(),
        platform.machine(),
        executable is not None,
        version_result,
        info_result,
    )
    return qualify_host(data)

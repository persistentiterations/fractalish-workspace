"""Read-only prerequisite checker for Bolt-On Continuity for Docker v0.2."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

SCHEMA_VERSION = "1"
PRODUCT = "Bolt-On Continuity for Docker"
PRODUCT_VERSION = "0.2"
STAGE = "2"
MINIMUM_PYTHON = (3, 11)
PROBE_TIMEOUT_SECONDS = 10
VERSION_ARGS = ("version", "--format", "{{json .}}")
INFO_ARGS = ("info", "--format", "{{json .}}")
ALLOWED_PROBES = (VERSION_ARGS, INFO_ARGS)


@dataclass(frozen=True)
class ProbeResult:
    returncode: int
    stdout: str
    stderr: str = ""
    timed_out: bool = False


Runner = Callable[[str, Sequence[str], int], ProbeResult]


def _default_runner(executable: str, args: Sequence[str], timeout: int) -> ProbeResult:
    if tuple(args) not in ALLOWED_PROBES:
        raise ValueError("probe argument vector is not allowlisted")
    try:
        completed = subprocess.run(
            [executable, *args],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ProbeResult(returncode=124, stdout="", stderr="timeout", timed_out=True)
    return ProbeResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _check(identifier: str, passed: bool, reason: str) -> dict[str, object]:
    return {"check": identifier, "passed": bool(passed), "reason": reason}


def _parse_object(text: str) -> Mapping[str, object] | None:
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _version_triplet(version_info: Sequence[int]) -> list[int]:
    padded = list(version_info[:3])
    while len(padded) < 3:
        padded.append(0)
    return [int(part) for part in padded]


def evaluate_prerequisites(
    *,
    system_name: str,
    machine: str,
    python_implementation: str,
    python_version: Sequence[int],
    docker_executable: str | None,
    runner: Runner,
    environment: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Evaluate normalized host inputs and return a canonical JSON-compatible report."""

    checks: list[dict[str, object]] = []
    host_family = system_name.strip().lower()
    host_supported = host_family in {"windows", "linux"}
    checks.append(_check("host_family", host_supported, "SUPPORTED_HOST" if host_supported else "UNSUPPORTED_HOST"))

    implementation_ok = python_implementation.strip().lower() == "cpython"
    version = _version_triplet(python_version)
    version_ok = tuple(version[:2]) >= MINIMUM_PYTHON
    python_ok = implementation_ok and version_ok
    python_reason = "SUPPORTED_PYTHON" if python_ok else "UNSUPPORTED_PYTHON"
    checks.append(_check("python_runtime", python_ok, python_reason))

    docker_found = bool(docker_executable)
    checks.append(_check("docker_cli", docker_found, "DOCKER_CLI_FOUND" if docker_found else "DOCKER_CLI_MISSING"))

    env = environment or {}
    remote_endpoint_present = bool(env.get("DOCKER_HOST", "").strip())
    checks.append(
        _check(
            "local_endpoint",
            not remote_endpoint_present,
            "LOCAL_ENDPOINT" if not remote_endpoint_present else "REMOTE_ENDPOINT_REJECTED",
        )
    )

    client_version: str | None = None
    server_version: str | None = None
    engine_os_type: str | None = None

    if docker_found and not remote_endpoint_present:
        version_probe = runner(str(docker_executable), VERSION_ARGS, PROBE_TIMEOUT_SECONDS)
        if version_probe.timed_out:
            checks.append(_check("docker_version_probe", False, "DOCKER_VERSION_TIMEOUT"))
        elif version_probe.returncode != 0:
            checks.append(_check("docker_version_probe", False, "DOCKER_VERSION_FAILED"))
        else:
            version_object = _parse_object(version_probe.stdout)
            if version_object is None:
                checks.append(_check("docker_version_probe", False, "DOCKER_VERSION_MALFORMED"))
            else:
                client = version_object.get("Client")
                server = version_object.get("Server")
                client_version = client.get("Version") if isinstance(client, dict) and isinstance(client.get("Version"), str) else None
                server_version = server.get("Version") if isinstance(server, dict) and isinstance(server.get("Version"), str) else None
                version_valid = bool(client_version and server_version)
                checks.append(
                    _check(
                        "docker_version_probe",
                        version_valid,
                        "DOCKER_CLIENT_AND_SERVER_RESPONSIVE" if version_valid else "DOCKER_VERSION_INCOMPLETE",
                    )
                )

        info_probe = runner(str(docker_executable), INFO_ARGS, PROBE_TIMEOUT_SECONDS)
        if info_probe.timed_out:
            checks.append(_check("docker_info_probe", False, "DOCKER_INFO_TIMEOUT"))
        elif info_probe.returncode != 0:
            checks.append(_check("docker_info_probe", False, "DOCKER_INFO_FAILED"))
        else:
            info_object = _parse_object(info_probe.stdout)
            if info_object is None:
                checks.append(_check("docker_info_probe", False, "DOCKER_INFO_MALFORMED"))
            else:
                raw_os_type = info_object.get("OSType")
                engine_os_type = raw_os_type.strip().lower() if isinstance(raw_os_type, str) else None
                linux_mode = engine_os_type == "linux"
                checks.append(
                    _check(
                        "docker_info_probe",
                        linux_mode,
                        "LINUX_CONTAINER_ENGINE" if linux_mode else "LINUX_CONTAINER_ENGINE_REQUIRED",
                    )
                )
    else:
        checks.append(_check("docker_version_probe", False, "DOCKER_PROBE_NOT_RUN"))
        checks.append(_check("docker_info_probe", False, "DOCKER_PROBE_NOT_RUN"))

    observation_only = True
    gateway_enabled = False
    checks.append(_check("safe_defaults", observation_only and not gateway_enabled, "SAFE_DEFAULTS_ENFORCED"))

    eligible = all(bool(item["passed"]) for item in checks)
    reason_codes = [str(item["reason"]) for item in checks if not bool(item["passed"])]
    if not reason_codes:
        reason_codes = ["ELIGIBLE"]

    return {
        "schema_version": SCHEMA_VERSION,
        "product": PRODUCT,
        "product_version": PRODUCT_VERSION,
        "stage": STAGE,
        "host_family": host_family,
        "machine": machine.strip().lower(),
        "python_implementation": python_implementation.strip().lower(),
        "python_version": version,
        "docker_cli_present": docker_found,
        "docker_client_version": client_version,
        "docker_server_version": server_version,
        "docker_engine_os_type": engine_os_type,
        "local_engine": not remote_endpoint_present,
        "observation_only": observation_only,
        "gateway_enabled": gateway_enabled,
        "checks": checks,
        "eligible": eligible,
        "reason_codes": reason_codes,
    }


def canonical_report_bytes(report: Mapping[str, object]) -> bytes:
    return (json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def run_local_check() -> dict[str, object]:
    executable = shutil.which("docker")
    return evaluate_prerequisites(
        system_name=platform.system(),
        machine=platform.machine(),
        python_implementation=platform.python_implementation(),
        python_version=sys.version_info[:3],
        docker_executable=executable,
        runner=_default_runner,
        environment={"DOCKER_HOST": os.environ.get("DOCKER_HOST", "")},
    )


def main() -> int:
    report = run_local_check()
    sys.stdout.buffer.write(canonical_report_bytes(report))
    return 0 if report["eligible"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

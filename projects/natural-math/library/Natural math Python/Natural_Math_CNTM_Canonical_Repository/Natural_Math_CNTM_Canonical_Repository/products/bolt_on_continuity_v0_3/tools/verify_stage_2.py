"""Deterministic Stage 2 verifier."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.prerequisites import INFO_ARGS, VERSION_ARGS, ProbeResult, QualificationInput, qualify_host

AUTHORITY_FILES = (
    "docs/STAGE_2_CONTRACT.md",
    "docs/STAGE_2_GATES.md",
    "src/bolt_on/prerequisites.py",
    "src/bolt_on/cli/main.py",
    "tests/test_stage_2.py",
    "tools/verify_stage_2.py",
)


def fail(message: str) -> None:
    raise SystemExit(f"STAGE 2 VERIFICATION FAILED: {message}")


def verify_vectors() -> None:
    if VERSION_ARGS != ("version", "--format", "{{json .}}") or INFO_ARGS != ("info", "--format", "{{json .}}"):
        fail("Docker probe vectors changed")
    data = QualificationInput(
        "CPython", (3, 14, 6), "Windows", "AMD64", True,
        ProbeResult(0, '{"Client":{"Version":"29.0.0"},"Server":{"Version":"29.0.0"}}'),
        ProbeResult(0, '{"DockerRootDir":"/var/lib/docker","Name":"desktop-linux","OSType":"linux"}'),
    )
    report = qualify_host(data)
    expected = {
        "details": {
            "docker_cli_present": True,
            "docker_client_version": "29.0.0",
            "docker_server_version": "29.0.0",
            "engine_os_type": "linux",
            "gateway_enabled": False,
            "host_family": "Windows",
            "local_engine": True,
            "machine": "AMD64",
            "observation_only": True,
            "python_implementation": "CPython",
            "python_version": "3.14.6",
        },
        "eligible": True,
        "reason_codes": [],
        "schema_version": 1,
        "stage": "v0.3-stage-2",
    }
    if report.body() != expected:
        fail("canonical qualification vector mismatch")
    if json.loads(report.canonical_json()) != expected:
        fail("canonical JSON mismatch")


def verify_subprocess_contract() -> None:
    path = SRC / "bolt_on" / "prerequisites.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    text = path.read_text(encoding="utf-8")
    if "shell=False" not in text or "timeout=timeout" not in text:
        fail("bounded subprocess contract missing")
    if "os.system" in text or "shell=True" in text:
        fail("forbidden shell execution present")
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    if not any(isinstance(call.func, ast.Attribute) and call.func.attr == "run" for call in calls):
        fail("probe runner missing")


def manifest_digest() -> str:
    entries = []
    for relative in AUTHORITY_FILES:
        data = (ROOT / relative).read_bytes()
        entries.append({"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run() -> None:
    missing = [path for path in AUTHORITY_FILES if not (ROOT / path).is_file()]
    if missing:
        fail(f"missing files: {missing}")
    verify_vectors()
    verify_subprocess_contract()
    print(f"STAGE 2 MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 STAGE 2 VERIFICATION PASSED")


if __name__ == "__main__":
    run()

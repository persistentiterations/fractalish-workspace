#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 Stage 1."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
STAGE_0_PATHS = (
    "docs/STAGE_0_PRODUCT_SCOPE_CONTRACT.md",
    "pyproject.toml",
    "src/bolt_on_v0_4/__init__.py",
    "src/bolt_on_v0_4/stage_0.py",
    "tests/test_stage_0.py",
    "tools/verify_stage_0.py",
)
STAGE_1_PATHS = (
    "docs/STAGE_1_ACCEPTANCE_GATES.md",
    "docs/STAGE_1_PREREQUISITE_DOCTOR_CONTRACT.md",
    "src/bolt_on_v0_4/__main__.py",
    "src/bolt_on_v0_4/cli.py",
    "src/bolt_on_v0_4/stage_1.py",
    "tests/test_stage_1.py",
    "tools/verify_stage_1.py",
)
STAGE_1_SOURCE_PATHS = (
    "src/bolt_on_v0_4/__main__.py",
    "src/bolt_on_v0_4/cli.py",
    "src/bolt_on_v0_4/stage_1.py",
    "tools/verify_stage_1.py",
)
EXPECTED_STAGE_0_HEAD = "3ffbaa56b7cf8bb8d74cd33b2f0ca6008ce79018"
EXPECTED_STAGE_0_RECORD_SHA256 = "fbe8043e56285446a4b07ef4cdf011e08b9ea772813fc20a37f8118f743e9f69"
EXPECTED_STAGE_0_MANIFEST_SHA256 = "650c4e222f6554bd6c67188478a464f92dd884ea3e1949a7b7b27311997c7279"
ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "argparse",
    "ast",
    "collections",
    "dataclasses",
    "enum",
    "hashlib",
    "json",
    "os",
    "pathlib",
    "platform",
    "runpy",
    "shutil",
    "sys",
    "typing",
}
FORBIDDEN_CALL_NAMES = {
    "bind",
    "check_call",
    "check_output",
    "chmod",
    "chown",
    "connect",
    "install",
    "listen",
    "mkdir",
    "open",
    "popen",
    "recv",
    "remove",
    "rename",
    "rmdir",
    "run",
    "send",
    "touch",
    "unlink",
    "write",
    "write_bytes",
    "write_text",
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


def fail(message: str) -> None:
    raise SystemExit(
        f"BOLT-ON CONTINUITY v0.4 STAGE 1 VERIFICATION FAILED: {message}"
    )


def verify_required_files() -> None:
    for relative in (*STAGE_0_PATHS, *STAGE_1_PATHS):
        if not (ROOT / relative).is_file():
            fail(f"missing required file: {relative}")


def verify_read_only_policy() -> None:
    for relative in STAGE_1_SOURCE_PATHS:
        path = ROOT / relative
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=path.as_posix(),
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {
                    alias.name.split(".", 1)[0]
                    for alias in node.names
                }
                unauthorized = roots - ALLOWED_IMPORT_ROOTS
                if unauthorized:
                    fail(
                        f"unauthorized import in {relative}: "
                        f"{sorted(unauthorized)}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    continue
                root = (node.module or "").split(".", 1)[0]
                if root not in ALLOWED_IMPORT_ROOTS:
                    fail(f"unauthorized import in {relative}: {root}")
            elif isinstance(node, ast.Call):
                function = node.func
                if isinstance(function, ast.Attribute):
                    name = function.attr
                elif isinstance(function, ast.Name):
                    name = function.id
                else:
                    name = ""
                if (
                    isinstance(function, ast.Attribute)
                    and isinstance(function.value, ast.Name)
                    and function.value.id == "os"
                    and function.attr == "system"
                ):
                    fail(
                        "process, socket, installation, network, or mutation "
                        f"call in {relative}: os.system"
                    )
                if name in FORBIDDEN_CALL_NAMES:
                    fail(
                        "process, socket, installation, network, or mutation "
                        f"call in {relative}: {name}"
                    )


def manifest_hash(paths: tuple[str, ...]) -> str:
    entries = []
    for relative in paths:
        data = (ROOT / relative).read_bytes()
        entries.append(
            {
                "path": relative,
                "bytes": len(data),
                "sha256": sha256(data),
            }
        )
    return sha256(canonical_bytes(entries))


def verify_stage_zero_binding() -> None:
    observed_manifest = manifest_hash(STAGE_0_PATHS)
    if observed_manifest != EXPECTED_STAGE_0_MANIFEST_SHA256:
        fail(
            "Stage 0 verifier manifest changed: "
            f"{observed_manifest}"
        )

    namespace = runpy.run_path(
        (ROOT / "src" / "bolt_on_v0_4" / "stage_0.py").as_posix()
    )
    Evidence = namespace["AcceptanceEvidence"]
    qualify = namespace["qualify_stage_zero"]
    evidence = Evidence(True, True, True, True, True)
    record = qualify(evidence)
    observed_record = sha256(record.canonical_bytes())
    if observed_record != EXPECTED_STAGE_0_RECORD_SHA256:
        fail(
            "Stage 0 qualification record changed: "
            f"{observed_record}"
        )


def verify_stage_one_vectors() -> object:
    namespace = runpy.run_path(
        (ROOT / "src" / "bolt_on_v0_4" / "stage_1.py").as_posix()
    )
    if namespace["QUALIFIED_STAGE_0_HEAD"] != EXPECTED_STAGE_0_HEAD:
        fail("qualified Stage 0 head binding mismatch")
    if (
        namespace["STAGE_0_QUALIFICATION_RECORD_SHA256"]
        != EXPECTED_STAGE_0_RECORD_SHA256
    ):
        fail("Stage 0 qualification hash binding mismatch")
    if (
        namespace["STAGE_0_VERIFIER_MANIFEST_SHA256"]
        != EXPECTED_STAGE_0_MANIFEST_SHA256
    ):
        fail("Stage 0 manifest hash binding mismatch")

    Snapshot = namespace["EnvironmentSnapshot"]
    CheckStatus = namespace["CheckStatus"]
    build = namespace["build_doctor_report"]
    snapshot = Snapshot(
        (3, 11, 9),
        "Windows",
        {"LOCALAPPDATA": "C:/Users/Example/AppData/Local"},
        "C:/Program Files/Docker/docker.exe",
    )
    report = build(snapshot)
    if not report.ready or report.status != "STAGE_1_READY":
        fail("qualified vector was not ready")
    if set(report.authority.values()) != {False}:
        fail("operational or release authority was enabled")
    expected_checks = [
        {
            "check_id": "stage0.binding",
            "detail": EXPECTED_STAGE_0_HEAD,
            "status": "PASS",
            "summary": "Qualified Stage 0 binding",
        },
        {
            "check_id": "python.version",
            "detail": "3.11.9",
            "status": "PASS",
            "summary": "Python version",
        },
        {
            "check_id": "platform.system",
            "detail": "Windows",
            "status": "PASS",
            "summary": "Operating-system family",
        },
        {
            "check_id": "docker.cli",
            "detail": "C:/Program Files/Docker/docker.exe",
            "status": "PASS",
            "summary": "Docker CLI path discovery",
        },
        {
            "check_id": "storage.recommended_path",
            "detail": (
                "C:\\Users\\Example\\AppData\\Local\\"
                "BoltOn\\Continuity\\v0.4"
            ),
            "status": "PASS",
            "summary": "Recommended future data path",
        },
        {
            "check_id": "authority.boundary",
            "detail": "ALL_DENIED",
            "status": "PASS",
            "summary": "Operational and release authority",
        },
    ]
    if report.body()["checks"] != expected_checks:
        fail("canonical doctor check vector mismatch")
    body = report.body_without_digest()
    if report.report_digest != sha256(canonical_bytes(body)):
        fail("doctor report digest mismatch")
    if report.canonical_bytes() != canonical_bytes(report.body()):
        fail("doctor canonical serialization mismatch")

    missing_docker = build(
        Snapshot(
            (3, 11, 9),
            "Windows",
            {"LOCALAPPDATA": "C:/Users/Example/AppData/Local"},
            None,
        )
    )
    docker_check = next(
        check
        for check in missing_docker.checks
        if check.check_id == "docker.cli"
    )
    if docker_check.status is not CheckStatus.WARN:
        fail("missing Docker CLI was not a warning")
    if not missing_docker.ready:
        fail("missing Docker CLI incorrectly blocked readiness")

    old_python = build(
        Snapshot(
            (3, 10, 14),
            "Linux",
            {"HOME": "/home/example"},
            None,
        )
    )
    if old_python.status != "NOT_READY":
        fail("unsupported Python did not fail closed")

    tests = (
        ROOT / "tests" / "test_stage_1.py"
    ).read_text(encoding="utf-8")
    if tests.count("def test_") != 12:
        fail("Stage 1 test inventory mismatch")

    return report


def main() -> int:
    verify_required_files()
    verify_read_only_policy()
    verify_stage_zero_binding()
    report = verify_stage_one_vectors()

    record_hash = sha256(report.canonical_bytes())
    stage_one_manifest = manifest_hash(STAGE_1_PATHS)
    print(f"Stage 1 qualification record SHA-256: {record_hash}")
    print(
        "Stage 1 verifier manifest SHA-256: "
        f"{stage_one_manifest}"
    )
    print(
        "BOLT-ON CONTINUITY v0.4 STAGE 1 VERIFICATION PASSED: "
        f"{len(STAGE_1_PATHS)} files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

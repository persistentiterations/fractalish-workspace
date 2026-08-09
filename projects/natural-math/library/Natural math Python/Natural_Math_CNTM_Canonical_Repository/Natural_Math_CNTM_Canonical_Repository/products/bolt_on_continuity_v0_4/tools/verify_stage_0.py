#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 Stage 0 scope."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "STAGE_0_PRODUCT_SCOPE_CONTRACT.md"
PYPROJECT = ROOT / "pyproject.toml"
PACKAGE_INIT = ROOT / "src" / "bolt_on_v0_4" / "__init__.py"
STAGE_SOURCE = ROOT / "src" / "bolt_on_v0_4" / "stage_0.py"
TEST_SOURCE = ROOT / "tests" / "test_stage_0.py"
THIS_FILE = Path(__file__).resolve()

MANIFEST_PATHS = (
    "docs/STAGE_0_PRODUCT_SCOPE_CONTRACT.md",
    "pyproject.toml",
    "src/bolt_on_v0_4/__init__.py",
    "src/bolt_on_v0_4/stage_0.py",
    "tests/test_stage_0.py",
    "tools/verify_stage_0.py",
)
EXPECTED_CAPABILITIES = (
    "single_documented_local_launch_path",
    "single_bounded_demonstration_workflow",
    "deterministic_replayable_receipts",
    "observation_only_default",
    "clear_success_hold_failure_output",
    "second_machine_qualification_before_release",
)
EXPECTED_AUTHORITY = {
    "installer_execution": False,
    "background_service": False,
    "native_execution": False,
    "docker_mutation": False,
    "automatic_recovery": False,
    "attach_or_distribute_packages": False,
    "publish_release": False,
    "production_claims": False,
}
ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "ast",
    "hashlib",
    "json",
    "pathlib",
    "runpy",
}
PROHIBITED_CALL_NAMES = {
    "bind",
    "check_call",
    "check_output",
    "chmod",
    "chown",
    "connect",
    "install",
    "listen",
    "mkdir",
    "popen",
    "recv",
    "remove",
    "rename",
    "rmdir",
    "run",
    "send",
    "system",
    "touch",
    "unlink",
    "write_bytes",
    "write_text",
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"BOLT-ON CONTINUITY v0.4 STAGE 0 VERIFICATION FAILED: {message}")


def verify_read_only_source_policy(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".", 1)[0] for alias in node.names}
            if not roots <= ALLOWED_IMPORT_ROOTS:
                fail(f"unauthorized import in {path.name}: {sorted(roots - ALLOWED_IMPORT_ROOTS)}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root not in ALLOWED_IMPORT_ROOTS:
                fail(f"unauthorized import in {path.name}: {root}")
        elif isinstance(node, ast.Call):
            function = node.func
            name = function.attr if isinstance(function, ast.Attribute) else function.id if isinstance(function, ast.Name) else ""
            if name in PROHIBITED_CALL_NAMES:
                fail(f"mutation, process, installation, or network call in {path.name}: {name}")


def main() -> int:
    for relative in MANIFEST_PATHS:
        if not (ROOT / relative).is_file():
            fail(f"missing required file: {relative}")

    verify_read_only_source_policy(THIS_FILE)

    contract = CONTRACT.read_text(encoding="utf-8")
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    package_init = PACKAGE_INIT.read_text(encoding="utf-8")
    tests = TEST_SOURCE.read_text(encoding="utf-8")
    stage_namespace = runpy.run_path(STAGE_SOURCE.as_posix())

    if stage_namespace["PRODUCT"] != "Bolt-On Continuity v0.4":
        fail("product identity mismatch")
    if stage_namespace["BASE_MAIN"] != "9e69a9edb61f0812a312502aabc8377c7aabf62a":
        fail("main-base binding mismatch")
    if stage_namespace["FOUNDATION_TAG"] != "bolt-on-continuity-v0.3":
        fail("foundation tag mismatch")
    if stage_namespace["FOUNDATION_TARGET"] != "1c95a1ff8ead30675d4d26f7d77720097c5b9129":
        fail("foundation target mismatch")
    if tuple(stage_namespace["REQUIRED_CAPABILITIES"]) != EXPECTED_CAPABILITIES:
        fail("required capability set mismatch")

    evidence_values = {
        "scope_defined": all(marker in contract for marker in ("## Purpose", "## Product goal")),
        "capabilities_defined": all(
            marker in contract
            for marker in (
                "One documented local launch path.",
                "One bounded demonstration workflow.",
                "Deterministic, replayable receipts.",
                "Explicit observation-only behavior by default.",
                "Clear success, hold, and failure output.",
                "Qualification on a second machine before release consideration.",
            )
        ),
        "exclusions_defined": all(
            marker in contract
            for marker in (
                "## Explicit exclusions",
                "installer execution;",
                "background observers or services;",
                "native gateways;",
                "Docker or host mutation;",
                "automatic recovery actions;",
                "uploaded binaries or packages;",
                "publication;",
                "production-readiness, universal-compatibility, zero-drift, or security-certification claims.",
            )
        ),
        "evidence_requirements_defined": (
            "## Stage 0 acceptance criteria" in contract
            and "evidence requirements" in contract
            and "encoded deterministically and tested" in contract
        ),
        "authority_denied": (
            "## Authority boundary" in contract
            and "All operational and release authorities remain false." in contract
        ),
    }
    if not all(evidence_values.values()):
        fail(f"scope evidence incomplete: {evidence_values}")

    if 'pythonpath = ["src"]' not in pyproject or 'testpaths = ["tests"]' not in pyproject:
        fail("pytest path configuration mismatch")
    if "AcceptanceEvidence" not in package_init or "qualify_stage_zero" not in package_init:
        fail("package export mismatch")
    if tests.count("def test_") != 6:
        fail("Stage 0 test inventory mismatch")

    Evidence = stage_namespace["AcceptanceEvidence"]
    qualify = stage_namespace["qualify_stage_zero"]
    evidence = Evidence(**evidence_values)
    record = qualify(evidence)

    if record.status != "STAGE_0_QUALIFIED":
        fail("qualified evidence did not qualify")
    if record.authority != EXPECTED_AUTHORITY:
        fail("authority boundary mismatch")

    record_object = json.loads(record.canonical_bytes())
    embedded_digest = record_object.pop("record_digest")
    if embedded_digest != sha256(canonical_bytes(record_object)):
        fail("record digest mismatch")

    for field in evidence_values:
        rejected = dict(evidence_values)
        rejected[field] = False
        if qualify(Evidence(**rejected)).status != "NOT_READY":
            fail(f"missing evidence was not rejected: {field}")

    entries = []
    for relative in MANIFEST_PATHS:
        data = (ROOT / relative).read_bytes()
        entries.append({"path": relative, "bytes": len(data), "sha256": sha256(data)})

    record_hash = sha256(record.canonical_bytes())
    manifest_hash = sha256(canonical_bytes(entries))
    print(f"Stage 0 qualification record SHA-256: {record_hash}")
    print(f"Stage 0 verifier manifest SHA-256: {manifest_hash}")
    print(f"BOLT-ON CONTINUITY v0.4 STAGE 0 VERIFICATION PASSED: {len(entries)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

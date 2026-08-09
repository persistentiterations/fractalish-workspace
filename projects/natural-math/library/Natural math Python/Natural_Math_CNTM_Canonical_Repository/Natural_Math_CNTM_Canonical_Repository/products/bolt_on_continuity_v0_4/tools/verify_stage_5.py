#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 Stage 5."""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.as_posix() not in sys.path:
    sys.path.insert(0, SRC.as_posix())

STAGE_4_PATHS = (
    "docs/STAGE_4_ACCEPTANCE_GATES.md",
    "docs/STAGE_4_CANONICAL_CONFIGURATION_CONTRACT.md",
    "src/bolt_on_v0_4/stage_4.py",
    "src/bolt_on_v0_4/stage_4_cli.py",
    "tests/test_stage_4.py",
    "tools/verify_stage_4.py",
)
EXPECTED_STAGE_4_BLOBS = {
    "docs/STAGE_4_ACCEPTANCE_GATES.md": "02394648b3ff3d884ed9efa98fa34a894e472828",
    "docs/STAGE_4_CANONICAL_CONFIGURATION_CONTRACT.md": "8bc908bf8442f9505e838cced3475e3ebe909d9e",
    "src/bolt_on_v0_4/stage_4.py": "9c228444938ee8dbe345136ff1a43d39adc185cd",
    "src/bolt_on_v0_4/stage_4_cli.py": "8624ed1d06cdf4b714abe6fb2585563154d995e7",
    "tests/test_stage_4.py": "9273a83d2e515b97620668464adb4119465ec2ab",
    "tools/verify_stage_4.py": "cd0f60b584db92863968523c3d8903e99e8bb545",
}
STAGE_5_PATHS = (
    "docs/STAGE_5_ACCEPTANCE_GATES.md",
    "docs/STAGE_5_OBSERVATION_LIFECYCLE_CONTRACT.md",
    "src/bolt_on_v0_4/stage_5.py",
    "src/bolt_on_v0_4/stage_5_cli.py",
    "tests/test_stage_5.py",
    "tools/verify_stage_5.py",
)
EXPECTED_STAGE_4_HEAD = "9e05306ebbbd235beb2af8cf91c2b4c4d96c9ddc"
EXPECTED_STAGE_4_RECORD = "8ac44c29c207f6bf047f5291abc16b99394d1bfc139a15e57c35d0a37e2cebe9"
EXPECTED_STAGE_4_MANIFEST = "3628499eacbb59d457ccfd8333adb0ebcbfa4b0542891d4a26b24fdc2079ef8f"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_blob_sha(value: bytes) -> str:
    return hashlib.sha1(f"blob {len(value)}\0".encode("ascii") + value).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"BOLT-ON CONTINUITY v0.4 STAGE 5 VERIFICATION FAILED: {message}")


def manifest_hash(paths: tuple[str, ...]) -> str:
    entries = []
    for relative in paths:
        data = (ROOT / relative).read_bytes()
        entries.append({"bytes": len(data), "path": relative, "sha256": sha256(data)})
    return sha256(canonical_bytes(entries))


def verify_files_and_binding() -> None:
    for relative in (*STAGE_4_PATHS, *STAGE_5_PATHS):
        if not (ROOT / relative).is_file():
            fail(f"missing required file: {relative}")
    for relative, expected in EXPECTED_STAGE_4_BLOBS.items():
        observed = git_blob_sha((ROOT / relative).read_bytes())
        if observed != expected:
            fail(f"qualified Stage 4 file changed: {relative}: {observed}")


def verify_source_policy() -> None:
    forbidden_imports = {"subprocess", "socket", "threading", "docker", "pathlib", "os"}
    forbidden_calls = {"open", "write", "write_text", "write_bytes", "run", "popen", "start", "stop", "connect", "mkdir", "unlink", "remove"}
    for relative in ("src/bolt_on_v0_4/stage_5.py", "src/bolt_on_v0_4/stage_5_cli.py"):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"), filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
                if roots & forbidden_imports:
                    fail(f"forbidden import in {relative}: {sorted(roots & forbidden_imports)}")
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                root = (node.module or "").split(".", 1)[0]
                if root in forbidden_imports:
                    fail(f"forbidden import in {relative}: {root}")
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ""
                if name in forbidden_calls:
                    fail(f"forbidden operational call in {relative}: {name}")


def fixture_configuration(stage4: object) -> bytes:
    base = {
        "action_vocabulary": ["NO_ACTION", "HOLD", "RELEASE"],
        "authority": dict(stage4.AUTHORITY),
        "mode": {"approval_required": True, "autonomous_actions": False, "gateway_enabled": False, "observation_only": True},
        "product": "Bolt-On Continuity v0.4",
        "qualified_stage_3_head": "c6aa6590b46e802b1e59d05f3af94c2ce9ed58a0",
        "retention": {"maximum_incidents": 1000, "mode": "retain_until_operator_deletes"},
        "schema_version": 1,
        "stage": 4,
        "stage_3_qualification_record_sha256": "1715c97822c5639b4850a46f28f5620b09c19a981e1b32e93ecb4f9bbc741bf0",
        "stage_3_verifier_manifest_sha256": "f68cee14b5c47572e84b839cd2b2917f7c2c3f706bc87a7f83c0937b5e5fdbc9",
        "storage": {"data_directory": "data/bolt-on-continuity", "maximum_receipt_bytes_per_incident": 1048576, "persistence_authorized": False},
        "subject": {"container_id": "a" * 64, "display_name": "alpha", "image": "alpine:3.20", "platform": "linux"},
    }
    body = {**base, "configuration_digest": sha256(canonical_bytes(base))}
    return canonical_bytes(body) + b"\n"


def verify_vectors() -> object:
    stage4 = importlib.import_module("bolt_on_v0_4.stage_4")
    stage5 = importlib.import_module("bolt_on_v0_4.stage_5")
    if stage5.QUALIFIED_STAGE_4_HEAD != EXPECTED_STAGE_4_HEAD:
        fail("Stage 4 head binding mismatch")
    if stage5.STAGE_4_QUALIFICATION_RECORD_SHA256 != EXPECTED_STAGE_4_RECORD:
        fail("Stage 4 record binding mismatch")
    if stage5.STAGE_4_VERIFIER_MANIFEST_SHA256 != EXPECTED_STAGE_4_MANIFEST:
        fail("Stage 4 manifest binding mismatch")
    if stage5.COMMANDS != {"config-check", "status", "start", "stop"}:
        fail("command vocabulary changed")
    configuration = fixture_configuration(stage4)
    results = {command: stage5.execute(command, configuration) for command in sorted(stage5.COMMANDS)}
    if results["start"].body()["lifecycle_state"] != "OBSERVATION_PLAN_READY":
        fail("start plan state changed")
    if results["stop"].body()["lifecycle_state"] != "STOP_PLAN_READY":
        fail("stop plan state changed")
    for command, result in results.items():
        body = result.body()
        if body["accepted"] is not True or body["safety"] != stage5.SAFETY:
            fail(f"unsafe accepted result: {command}")
        base = {key: value for key, value in body.items() if key != "result_digest"}
        if body["result_digest"] != sha256(canonical_bytes(base)):
            fail(f"result digest mismatch: {command}")
        if result.canonical_bytes() != stage5.execute(command, configuration).canonical_bytes():
            fail(f"nondeterministic result: {command}")
    rejected = stage5.execute("launch", configuration).body()
    if rejected["accepted"] is not False or rejected["reason_code"] != "UNKNOWN_COMMAND":
        fail("unknown command did not fail closed")
    invalid = stage5.execute("start", b"not-json").body()
    if invalid["accepted"] is not False or invalid["reason_code"] != "CONFIGURATION_INVALID":
        fail("invalid configuration did not fail closed")
    enabled = {key for key, value in stage5.AUTHORITY.items() if value}
    if enabled != {"stage_4_configuration_consumption", "configuration_validation", "lifecycle_plan_construction"}:
        fail(f"authority set changed: {sorted(enabled)}")
    tests = (ROOT / "tests" / "test_stage_5.py").read_text(encoding="utf-8")
    if tests.count("def test_") != 20:
        fail("Stage 5 test inventory mismatch")
    return results["start"]


def main() -> int:
    verify_files_and_binding()
    verify_source_policy()
    record = verify_vectors()
    print(f"Stage 5 qualification record SHA-256: {sha256(record.canonical_bytes())}")
    print(f"Stage 5 verifier manifest SHA-256: {manifest_hash(STAGE_5_PATHS)}")
    print(f"BOLT-ON CONTINUITY v0.4 STAGE 5 VERIFICATION PASSED: {len(STAGE_5_PATHS)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

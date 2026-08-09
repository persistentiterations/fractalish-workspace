"""Deterministic Stage 9 verifier."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.configuration_stage4 import build_configuration
from bolt_on.discovery import EnrollmentRecord
from bolt_on.installation_stage9 import DELETE_CONFIRMATION, plan_install, plan_uninstall
from bolt_on.receipts import canonical_json_bytes

AUTHORITY_FILES = (
    "docs/STAGE_9_CONTRACT.md",
    "docs/STAGE_9_GATES.md",
    "src/bolt_on/installation_stage9.py",
    "tests/test_stage_9.py",
    "tools/verify_stage_9.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "os", "pathlib", "shutil", "threading", "multiprocessing"}
CID = "a" * 64


def fail(message: str) -> None:
    raise SystemExit(f"STAGE 9 VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/installation_stage9.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = {node.module.split(".")[0]}
        else:
            continue
        forbidden = names & FORBIDDEN_IMPORTS
        if forbidden:
            fail(f"forbidden import {sorted(forbidden)}")


def configuration():
    base = {
        "container_id": CID,
        "contract": "bolt-on-continuity-v0.3-stage-3",
        "display_name": "demo",
        "gateway_enabled": False,
        "image": "example:1",
        "observation_only": True,
        "observed_state": "running",
        "schema_version": 1,
    }
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    return build_configuration(EnrollmentRecord(CID, "demo", "example:1", "running", digest))


def verify_vectors() -> None:
    install = plan_install(configuration(), "ABSENT")
    repeat = plan_install(configuration(), "ABSENT")
    if install.canonical_bytes() != repeat.canonical_bytes():
        fail("install plan nondeterministic")
    if install.body["outcome"] != "PLAN_INSTALL" or install.body["execution_performed"] is not False:
        fail("install plan vector mismatch")
    if install.body["protected_subject"] != {"container_id": CID}:
        fail("protected subject mismatch")
    if any(CID in item for item in install.body["product_owned_paths"]):
        fail("subject used as operation target")
    remove_plan = plan_uninstall(configuration(), "INSTALLED", "DELETE_DATA", DELETE_CONFIRMATION)
    if remove_plan.body["outcome"] != "PLAN_UNINSTALL_DELETE_DATA":
        fail("uninstall plan vector mismatch")
    if remove_plan.body["deletion_performed"] is not False:
        fail("uninstall represented as executed")
    for plan in (install, remove_plan):
        if plan.body["native_execution_authorized"] is not False or plan.body["container_mutation_authorized"] is not False:
            fail("unsafe authority field")


def manifest_digest() -> str:
    entries = []
    for relative in AUTHORITY_FILES:
        data = (ROOT / relative).read_bytes()
        entries.append({"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run() -> None:
    verify_files()
    verify_source_boundary()
    verify_vectors()
    print(f"STAGE 9 MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 STAGE 9 VERIFICATION PASSED")


if __name__ == "__main__":
    run()

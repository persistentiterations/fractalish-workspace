"""Deterministic Stage 10 verifier."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.qualification_stage10 import REQUIRED_STAGES, qualify
from bolt_on.receipts import canonical_json_bytes

AUTHORITY_FILES = (
    "docs/STAGE_10_CONTRACT.md",
    "docs/STAGE_10_GATES.md",
    "src/bolt_on/qualification_stage10.py",
    "tests/test_stage_10.py",
    "tools/verify_stage_10.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "os", "threading", "multiprocessing"}


def fail(message: str) -> None:
    raise SystemExit(f"STAGE 10 VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/qualification_stage10.py"
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


def evidence() -> dict[str, object]:
    return {
        stage: {
            "stage": stage,
            "status": "PASS",
            "evidence_digest": f"{index + 1:064x}",
            "frozen_regression_passed": True,
            "authority_expanded": False,
        }
        for index, stage in enumerate(REQUIRED_STAGES)
    }


def verify_vectors() -> None:
    one = qualify(evidence())
    two = qualify(dict(reversed(list(evidence().items()))))
    if one.canonical_bytes() != two.canonical_bytes():
        fail("mapping-order determinism mismatch")
    parsed = json.loads(one.canonical_bytes())
    if parsed["readiness"] != "RELEASE_CANDIDATE_READY":
        fail("readiness mismatch")
    safety = parsed["safety"]
    expected_safety = {
        "container_mutation_authorized": False,
        "gateway_enabled": False,
        "merge_authorized": False,
        "native_execution_authorized": False,
        "observation_only": True,
        "production_readiness_claim_authorized": False,
        "publication_authorized": False,
        "release_freeze_authorized": False,
    }
    if safety != expected_safety:
        fail("authority boundary mismatch")
    base = dict(parsed)
    digest = base.pop("report_digest")
    expected = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    if digest != expected:
        fail("report digest mismatch")
    if [item["stage"] for item in parsed["stage_evidence"]] != list(REQUIRED_STAGES):
        fail("ordered evidence mismatch")


def manifest_digest() -> str:
    entries = []
    for relative in AUTHORITY_FILES:
        data = (ROOT / relative).read_bytes()
        entries.append({"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def run() -> None:
    verify_files()
    verify_source_boundary()
    verify_vectors()
    print(f"STAGE 10 MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 STAGE 10 VERIFICATION PASSED")


if __name__ == "__main__":
    run()

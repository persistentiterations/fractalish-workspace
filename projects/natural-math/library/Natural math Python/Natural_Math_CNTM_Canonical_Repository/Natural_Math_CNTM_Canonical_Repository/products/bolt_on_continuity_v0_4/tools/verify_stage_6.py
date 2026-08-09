#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 Stage 6."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.as_posix() not in sys.path:
    sys.path.insert(0, SRC.as_posix())

from bolt_on_v0_4.stage_6 import (  # noqa: E402
    AUTHORITY,
    QUALIFIED_STAGE_5_HEAD,
    STAGE_5_QUALIFICATION_RECORD_SHA256,
    STAGE_5_VERIFIER_MANIFEST_SHA256,
    canonical_bytes,
    export_incident,
    explain_incident,
    list_incidents,
    replay_incident,
    sha256,
)

EXPECTED_STAGE_5_HEAD = "818aa1bccd89bc9ba79bd48a7190ff3b6f61b06c"
EXPECTED_STAGE_5_RECORD = "6b1deab138bd52643ed797fc1195cf5d8a5fbcc2ea8a72c95ec871847f0e3ffc"
EXPECTED_STAGE_5_MANIFEST = "58ec59fdb6aa87ed934cea48581c7cdb3c790c39b7f980e10444aaff007e5e2f"

STAGE_5_PATHS = (
    "docs/STAGE_5_ACCEPTANCE_GATES.md",
    "docs/STAGE_5_OBSERVATION_LIFECYCLE_CONTRACT.md",
    "src/bolt_on_v0_4/stage_5.py",
    "src/bolt_on_v0_4/stage_5_cli.py",
    "tests/test_stage_5.py",
    "tools/verify_stage_5.py",
)
EXPECTED_STAGE_5_BLOBS = {
    "docs/STAGE_5_ACCEPTANCE_GATES.md": "41f939381c6383f02d3f4942c23c435a4738b722",
    "docs/STAGE_5_OBSERVATION_LIFECYCLE_CONTRACT.md": "463462bd7bb1a2d372adf3b15414e11d6b95d1f8",
    "src/bolt_on_v0_4/stage_5.py": "ccc4cd25b5599dfd77d1c9ce871a7ce15fce63e9",
    "src/bolt_on_v0_4/stage_5_cli.py": "2b3139054e4338b28ddd2bd5f03fb573eacb1642",
    "tests/test_stage_5.py": "890597a74e156349f84fbb7c9a181f1e1c500493",
    "tools/verify_stage_5.py": "e650348c1d4682e03f4fa56696afecaad1bb7f6e",
}
STAGE_6_PATHS = (
    "docs/STAGE_6_ACCEPTANCE_GATES.md",
    "docs/STAGE_6_INCIDENT_REVIEW_EXPORT_CONTRACT.md",
    "src/bolt_on_v0_4/stage_6.py",
    "src/bolt_on_v0_4/stage_6_cli.py",
    "tests/test_stage_6.py",
    "tools/verify_stage_6.py",
)
SOURCE_PATHS = (
    "src/bolt_on_v0_4/stage_6.py",
    "src/bolt_on_v0_4/stage_6_cli.py",
    "tools/verify_stage_6.py",
)
ALLOWED_IMPORTS = {"__future__","argparse","ast","collections","dataclasses","hashlib","json","pathlib","re","sys","typing","bolt_on_v0_4"}
FORBIDDEN_IMPORTS = {"docker","socket","subprocess","threading","multiprocessing","os"}
FORBIDDEN_CALLS = {"open","write","write_text","write_bytes","mkdir","touch","unlink","remove","rename","replace","system","popen","run","start","stop","connect","send","recv","approve","deny"}

def fail(message: str) -> None:
    raise SystemExit(f"BOLT-ON CONTINUITY v0.4 STAGE 6 VERIFICATION FAILED: {message}")

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()

def manifest_hash(paths: tuple[str, ...]) -> str:
    entries = []
    for relative in paths:
        data = (ROOT / relative).read_bytes()
        entries.append({"bytes": len(data), "path": relative, "sha256": hashlib.sha256(data).hexdigest()})
    return sha256(canonical_bytes(entries))

def verify_files() -> None:
    for relative in (*STAGE_5_PATHS, *STAGE_6_PATHS):
        if not (ROOT / relative).is_file():
            fail(f"missing required file: {relative}")
    for relative in STAGE_5_PATHS:
        observed = git_blob_sha((ROOT / relative).read_bytes())
        if observed != EXPECTED_STAGE_5_BLOBS[relative]:
            fail(f"qualified Stage 5 file changed: {relative}")
    if QUALIFIED_STAGE_5_HEAD != EXPECTED_STAGE_5_HEAD:
        fail("Stage 5 head binding changed")
    if STAGE_5_QUALIFICATION_RECORD_SHA256 != EXPECTED_STAGE_5_RECORD:
        fail("Stage 5 record binding changed")
    if STAGE_5_VERIFIER_MANIFEST_SHA256 != EXPECTED_STAGE_5_MANIFEST:
        fail("Stage 5 manifest binding changed")

def import_roots(node: ast.Import | ast.ImportFrom) -> set[str]:
    if isinstance(node, ast.Import):
        return {item.name.split(".", 1)[0] for item in node.names}
    if node.level:
        return set()
    return {(node.module or "").split(".", 1)[0]}

def verify_source_policy() -> None:
    for relative in SOURCE_PATHS:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"), filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                roots = import_roots(node)
                if roots & FORBIDDEN_IMPORTS:
                    fail(f"forbidden import in {relative}: {sorted(roots & FORBIDDEN_IMPORTS)}")
                unexpected = roots - ALLOWED_IMPORTS
                if unexpected:
                    fail(f"unexpected import in {relative}: {sorted(unexpected)}")
            elif isinstance(node, ast.Call):
                fn = node.func
                name = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""
                if name in FORBIDDEN_CALLS:
                    fail(f"forbidden operational call in {relative}: {name}")

def receipt(sequence: int, event_type: str, payload: object, previous: str) -> dict[str, object]:
    base = {"sequence": sequence, "event_type": event_type, "payload": payload, "previous_digest": previous}
    return {**base, "receipt_digest": sha256(canonical_bytes(base))}

def fixture(seed: str = "a", updated: int = 2, status: str = "PROJECTED") -> dict[str, object]:
    first = receipt(1, "OBSERVED", {"state": "running"}, "0" * 64)
    second = receipt(updated, "DECIDED", {"decision": "HOLD"}, first["receipt_digest"])
    return {
        "incident_id": "inc-" + seed * 64,
        "container_id": "c" * 64,
        "configuration_digest": "sha256:" + "d" * 64,
        "opened_sequence": 1,
        "updated_sequence": updated,
        "decision": "HOLD",
        "reason_code": "THRESHOLD_REACHED",
        "action_status": status,
        "receipts": [first, second],
    }

def qualify() -> object:
    incident = fixture()
    listing = list_incidents([fixture("b", 3), incident], 2)
    if [item["updated_sequence"] for item in listing.body()["items"]] != [3, 2]:
        fail("listing order changed")
    explanation = explain_incident(incident)
    if explanation.body()["explanation"]["native_execution_evidenced"] is not False:
        fail("projected action represented as executed")
    accepted = explain_incident(fixture(status="DOCKER_ACCEPTED"))
    if accepted.body()["explanation"]["native_execution_evidenced"] is not True:
        fail("Docker accepted status did not evidence execution")
    replay = replay_incident(incident)
    if replay.body()["replay"]["receipt_count"] != 2:
        fail("replay receipt count changed")
    export = export_incident(incident)
    package = export.body()["export"]
    base = dict(package)
    digest = base.pop("package_digest")
    if digest != sha256(canonical_bytes(base)):
        fail("export package digest mismatch")
    enabled = {key for key, value in AUTHORITY.items() if value}
    expected = {"stage_5_result_consumption","incident_validation","incident_listing","incident_explanation","offline_replay","in_memory_export"}
    if enabled != expected:
        fail(f"Stage 6 authority changed: {sorted(enabled)}")
    if (ROOT / "tests" / "test_stage_6.py").read_text(encoding="utf-8").count("def test_") != 18:
        fail("Stage 6 test inventory changed")
    return export

def main() -> int:
    verify_files()
    verify_source_policy()
    record = qualify()
    record_hash = sha256(record.canonical_bytes())
    manifest = manifest_hash(STAGE_6_PATHS)
    print(f"Stage 6 qualification record SHA-256: {record_hash}")
    print(f"Stage 6 verifier manifest SHA-256: {manifest}")
    print(f"BOLT-ON CONTINUITY v0.4 STAGE 6 VERIFICATION PASSED: {len(STAGE_6_PATHS)} files")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

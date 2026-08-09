#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 Stage 4."""
from __future__ import annotations
import ast
import hashlib
import importlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
STAGE_3_PATHS = (
    "docs/STAGE_3_ACCEPTANCE_GATES.md",
    "docs/STAGE_3_DISCOVERY_ENROLLMENT_CONTRACT.md",
    "src/bolt_on_v0_4/stage_3.py",
    "src/bolt_on_v0_4/stage_3_cli.py",
    "tests/test_stage_3.py",
    "tools/verify_stage_3.py",
)
EXPECTED_STAGE_3_BLOBS = {
    "docs/STAGE_3_ACCEPTANCE_GATES.md": "2d2c46254fe82c1ef9dba8fb24fac1e5443d86fa",
    "docs/STAGE_3_DISCOVERY_ENROLLMENT_CONTRACT.md": "7f01043b519df2445665a37cf18c6a9dd6f6d6b5",
    "src/bolt_on_v0_4/stage_3.py": "8fe32b254ea3fed41329188542b0f1b7c5b54f7c",
    "src/bolt_on_v0_4/stage_3_cli.py": "4d876cf5be37e0a1f31e7852e33c26b2103e321b",
    "tests/test_stage_3.py": "c79828fd4597695957fe2234a060da0216530e00",
    "tools/verify_stage_3.py": "f1958a9763d005c87deb578ffd99f5b601f3e818",
}
STAGE_4_PATHS = (
    "docs/STAGE_4_ACCEPTANCE_GATES.md",
    "docs/STAGE_4_CANONICAL_CONFIGURATION_CONTRACT.md",
    "src/bolt_on_v0_4/stage_4.py",
    "src/bolt_on_v0_4/stage_4_cli.py",
    "tests/test_stage_4.py",
    "tools/verify_stage_4.py",
)
STAGE_4_SOURCE_PATHS = (
    "src/bolt_on_v0_4/stage_4.py",
    "src/bolt_on_v0_4/stage_4_cli.py",
    "tools/verify_stage_4.py",
)
EXPECTED_STAGE_3_HEAD = "c6aa6590b46e802b1e59d05f3af94c2ce9ed58a0"
EXPECTED_STAGE_3_RECORD_SHA256 = "1715c97822c5639b4850a46f28f5620b09c19a981e1b32e93ecb4f9bbc741bf0"
EXPECTED_STAGE_3_MANIFEST_SHA256 = "f68cee14b5c47572e84b839cd2b2917f7c2c3f706bc87a7f83c0937b5e5fdbc9"
ALLOWED_IMPORT_ROOTS = {"__future__","argparse","ast","collections","dataclasses","hashlib","importlib","json","pathlib","re","runpy","sys","typing"}
FORBIDDEN_IMPORT_ROOTS = {"docker","socket","subprocess"}
FORBIDDEN_CALL_NAMES = {"bind","check_call","check_output","chmod","chown","connect","install","listen","mkdir","open","popen","recv","remove","rename","rmdir","send","start","stop","restart","kill","pause","unpause","touch","unlink","write","write_bytes","write_text"}

def canonical_bytes(value: object) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
def sha256(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def git_blob_sha(data: bytes) -> str: return hashlib.sha1(f"blob {len(data)}\0".encode("ascii")+data).hexdigest()
def fail(message: str) -> None: raise SystemExit(f"BOLT-ON CONTINUITY v0.4 STAGE 4 VERIFICATION FAILED: {message}")
def manifest_hash(paths: tuple[str,...]) -> str:
    entries=[]
    for relative in paths:
        data=(ROOT/relative).read_bytes(); entries.append({"path":relative,"bytes":len(data),"sha256":sha256(data)})
    return sha256(canonical_bytes(entries))
def verify_required_files() -> None:
    for relative in (*STAGE_3_PATHS,*STAGE_4_PATHS):
        if not (ROOT/relative).is_file(): fail(f"missing required file: {relative}")
def verify_stage_three_binding() -> None:
    for relative in STAGE_3_PATHS:
        observed=git_blob_sha((ROOT/relative).read_bytes())
        if observed != EXPECTED_STAGE_3_BLOBS[relative]: fail(f"qualified Stage 3 file changed: {relative}")
    manifest=manifest_hash(STAGE_3_PATHS)
    if manifest != EXPECTED_STAGE_3_MANIFEST_SHA256: fail(f"Stage 3 verifier manifest changed: {manifest}")
    namespace=runpy.run_path((ROOT/"tools"/"verify_stage_3.py").as_posix())
    if "main" not in namespace: fail("Stage 3 verifier entry point missing")
def _roots(node: ast.Import|ast.ImportFrom) -> set[str]:
    if isinstance(node,ast.Import): return {alias.name.split(".",1)[0] for alias in node.names}
    if node.level: return set()
    return {(node.module or "").split(".",1)[0]}
def verify_source_policy() -> None:
    for relative in STAGE_4_SOURCE_PATHS:
        tree=ast.parse((ROOT/relative).read_text(encoding="utf-8"),filename=relative)
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                roots=_roots(node); forbidden=roots & FORBIDDEN_IMPORT_ROOTS
                if forbidden: fail(f"forbidden import in {relative}: {sorted(forbidden)}")
                unauthorized=roots-ALLOWED_IMPORT_ROOTS
                if unauthorized: fail(f"unauthorized import in {relative}: {sorted(unauthorized)}")
            elif isinstance(node,ast.Call):
                function=node.func
                name=function.attr if isinstance(function,ast.Attribute) else function.id if isinstance(function,ast.Name) else ""
                if name in FORBIDDEN_CALL_NAMES: fail(f"operational or persistence call in {relative}: {name}")
def verify_vectors() -> object:
    stage3=importlib.import_module("bolt_on_v0_4.stage_3")
    stage4=importlib.import_module("bolt_on_v0_4.stage_4")
    if stage4.QUALIFIED_STAGE_3_HEAD != EXPECTED_STAGE_3_HEAD: fail("Stage 3 head binding mismatch")
    if stage4.STAGE_3_QUALIFICATION_RECORD_SHA256 != EXPECTED_STAGE_3_RECORD_SHA256: fail("Stage 3 qualification binding mismatch")
    if stage4.STAGE_3_VERIFIER_MANIFEST_SHA256 != EXPECTED_STAGE_3_MANIFEST_SHA256: fail("Stage 3 manifest binding mismatch")
    base={"authority":dict(stage3.AUTHORITY),"container_id":"a"*64,"display_name":"bolt-on-v0-4-fixture","image":"alpine:3.20","observed_state":"created","platform":"linux","product":"Bolt-On Continuity v0.4","qualified_stage_2_head":"15e29c94d81e5e5eae3ddf384eb8fa6af8ffcdc4","schema_version":1,"stage":3,"stage_2_qualification_record_sha256":"97b92c58c6bf342c44dd793bfe0a78401b9c606ecaccd27ca1f9c48cd2d6141e","stage_2_verifier_manifest_sha256":"6f1c6c119c8114ed20e84c6d28dc1e9de9000e6df861939e5775373e4d957192","status":"STAGE_3_ENROLLED"}
    record=stage3.EnrollmentRecord(**base,record_digest=sha256(canonical_bytes(base)))
    result=stage4.build_configuration(record)
    body=result.body()
    if body["mode"] != {"approval_required":True,"autonomous_actions":False,"gateway_enabled":False,"observation_only":True}: fail("safe mode changed")
    if body["action_vocabulary"] != ["NO_ACTION","HOLD","RELEASE"]: fail("action vocabulary changed")
    enabled={key for key,value in body["authority"].items() if value}
    if enabled != {"configuration_construction","configuration_validation","enrollment_record_consumption"}: fail(f"Stage 4 authority set changed: {sorted(enabled)}")
    if body["storage"]["persistence_authorized"] is not False: fail("persistence authority enabled")
    if result.configuration_digest != sha256(canonical_bytes({key:value for key,value in body.items() if key != "configuration_digest"})): fail("configuration digest mismatch")
    if not result.canonical_bytes().endswith(b"\n") or result.canonical_bytes().endswith(b"\n\n"): fail("canonical newline boundary changed")
    tests=(ROOT/"tests"/"test_stage_4.py").read_text(encoding="utf-8")
    if tests.count("def test_") != 28: fail("Stage 4 test inventory mismatch")
    return result
def main() -> int:
    verify_required_files(); verify_stage_three_binding(); verify_source_policy(); result=verify_vectors()
    print(f"Stage 4 qualification record SHA-256: {sha256(result.canonical_bytes())}")
    print(f"Stage 4 verifier manifest SHA-256: {manifest_hash(STAGE_4_PATHS)}")
    print(f"BOLT-ON CONTINUITY v0.4 STAGE 4 VERIFICATION PASSED: {len(STAGE_4_PATHS)} files")
    return 0
if __name__ == "__main__": raise SystemExit(main())

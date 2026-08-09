#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 Stage 7."""
from __future__ import annotations
import ast, hashlib, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from bolt_on_v0_4.stage_7 import AUTHORITY, GatewayState, canonical_bytes, create_request, record_decision
EXPECTED_HEAD="01dbfdc0ba8da3203be6ffcb759ef74edbd7d255"
EXPECTED_RECORD="cd45ee04b1f872f6a98cbc2c52995ebdfcf4eb64feb9a1a6bb912072ef78af7d"
EXPECTED_MANIFEST="6a6df9fcae5fbcd8ea3987c8bdeed5ae959cef631820de3d4fdc0b2a653dd6bc"
PATHS=("docs/STAGE_7_ACCEPTANCE_GATES.md","docs/STAGE_7_APPROVAL_BOUNDARY_CONTRACT.md","src/bolt_on_v0_4/stage_7.py","src/bolt_on_v0_4/stage_7_cli.py","tests/test_stage_7.py","tools/verify_stage_7.py")
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def manifest()->str:
    rows=[{"bytes":len((ROOT/p).read_bytes()),"path":p,"sha256":sha((ROOT/p).read_bytes())} for p in PATHS]
    return sha(canonical_bytes(rows))
def fail(msg:str): raise SystemExit(msg)
def main()->int:
    for p in PATHS:
        if not (ROOT/p).is_file(): fail(f"missing Stage 7 file: {p}")
    import bolt_on_v0_4.stage_7 as s
    if s.QUALIFIED_STAGE_6_HEAD!=EXPECTED_HEAD or s.STAGE_6_QUALIFICATION_RECORD_SHA256!=EXPECTED_RECORD or s.STAGE_6_VERIFIER_MANIFEST_SHA256!=EXPECTED_MANIFEST: fail("Stage 6 binding mismatch")
    enabled={k for k,v in AUTHORITY.items() if v}
    expected={"projected_request_construction","projected_request_validation","gateway_state_transition","operator_decision_recording","duplicate_conflict_detection"}
    if enabled!=expected: fail("Stage 7 authority mismatch")
    forbidden={"subprocess","socket","threading","docker","requests","urllib"}
    for rel in ("src/bolt_on_v0_4/stage_7.py","src/bolt_on_v0_4/stage_7_cli.py"):
        tree=ast.parse((ROOT/rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node,ast.Import) and any(a.name.split('.')[0] in forbidden for a in node.names): fail(f"forbidden import in {rel}")
            if isinstance(node,ast.ImportFrom) and (node.module or '').split('.')[0] in forbidden: fail(f"forbidden import in {rel}")
    req=create_request("req-"+"a"*64,"b"*64,"HOLD","sha256:"+"c"*64,"sha256:"+"d"*64,10,20)
    dec=record_decision(req.body(),GatewayState("ENABLED",11),"APPROVE","OPERATOR_APPROVED",12)
    record={"authority":dict(AUTHORITY),"decision":dec.body(),"gateway":GatewayState("ENABLED",11).body(),"product":s.PRODUCT,"qualified_stage_6_head":s.QUALIFIED_STAGE_6_HEAD,"request":req.body(),"schema_version":1,"stage":7,"stage_6_qualification_record_sha256":s.STAGE_6_QUALIFICATION_RECORD_SHA256,"stage_6_verifier_manifest_sha256":s.STAGE_6_VERIFIER_MANIFEST_SHA256}
    tests=(ROOT/"tests/test_stage_7.py").read_text(encoding="utf-8")
    if tests.count("def test_")!=15: fail("Stage 7 test inventory mismatch")
    print(f"Stage 7 qualification record SHA-256: {sha(canonical_bytes(record))}")
    print(f"Stage 7 verifier manifest SHA-256: {manifest()}")
    print(f"BOLT-ON CONTINUITY v0.4 STAGE 7 VERIFICATION PASSED: {len(PATHS)} files")
    return 0
if __name__=="__main__": raise SystemExit(main())

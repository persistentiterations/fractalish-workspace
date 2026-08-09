#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 Stage 8."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"src"
sys.path.insert(0,str(SRC))
from bolt_on_v0_4.stage_8 import AUTHORITY,QUALIFIED_STAGE_7_HEAD,STAGE_7_QUALIFICATION_RECORD_SHA256,STAGE_7_VERIFIER_MANIFEST_SHA256,classify_recovery
FILES=["docs/STAGE_8_ACCEPTANCE_GATES.md","docs/STAGE_8_RECOVERY_CLASSIFICATION_CONTRACT.md","src/bolt_on_v0_4/stage_8.py","src/bolt_on_v0_4/stage_8_cli.py","tests/test_stage_8.py","tools/verify_stage_8.py"]
def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def digest(value): return hashlib.sha256(value).hexdigest()
def main():
    assert QUALIFIED_STAGE_7_HEAD=="ddb7a2430a709705d91142742bd6ad3b61c24653"
    assert STAGE_7_QUALIFICATION_RECORD_SHA256=="cb8705634db07520a3bb2063cb0c1e34860e425486bc9b7043bb94eb889ea658"
    assert STAGE_7_VERIFIER_MANIFEST_SHA256=="4b2b9bddf658e53fa8488d29eb621adbf278d402dc8261b4b2072d5364db05d1"
    assert {key for key,value in AUTHORITY.items() if value}=={"recovery_classification","subject_evidence_validation","store_evidence_validation","duplicate_suppression","stage_7_record_consumption"}
    sample={"enrolled_id":"a"*64,"enrolled_name":"subject","current_subjects":[{"container_id":"a"*64,"display_name":"subject","state":"running"}],"store_classification":"STORE_HEALTHY","prior_requests":[]}
    body=classify_recovery(sample).body()
    assert body["disposition"]=="RESUME_OBSERVATION_ONLY"
    assert body["native_execution_authorized"] is False
    manifest={path:digest((ROOT/path).read_bytes()) for path in FILES}
    record={"files":FILES,"qualified_stage_7_head":QUALIFIED_STAGE_7_HEAD,"stage":8,"stage_7_qualification_record_sha256":STAGE_7_QUALIFICATION_RECORD_SHA256,"stage_7_verifier_manifest_sha256":STAGE_7_VERIFIER_MANIFEST_SHA256}
    print("Stage 8 qualification record SHA-256:",digest(canonical(record)))
    print("Stage 8 verifier manifest SHA-256:",digest(canonical(manifest)))
    print("BOLT-ON CONTINUITY v0.4 STAGE 8 VERIFICATION PASSED: 6 files")
if __name__=="__main__": main()

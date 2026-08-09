#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 Stage 9."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on_v0_4.stage_9 import (
    AUTHORITY,
    QUALIFIED_STAGE_8_HEAD,
    STAGE_8_QUALIFICATION_RECORD_SHA256,
    STAGE_8_VERIFIER_MANIFEST_SHA256,
    plan_install,
)

FILES = [
    "docs/STAGE_9_ACCEPTANCE_GATES.md",
    "docs/STAGE_9_INSTALLATION_UNINSTALL_PLANNING_CONTRACT.md",
    "src/bolt_on_v0_4/stage_9.py",
    "src/bolt_on_v0_4/stage_9_cli.py",
    "tests/test_stage_9.py",
    "tools/verify_stage_9.py",
]

CONFIG = json.loads(r'''{"action_vocabulary":["NO_ACTION","HOLD","RELEASE"],"authority":{"attach_or_distribute_packages":false,"automatic_recovery":false,"background_service":false,"configuration_construction":true,"configuration_validation":true,"container_create_remove":false,"container_enumeration":false,"container_exec":false,"container_inspection":false,"container_start_stop_restart":false,"docker_contact":false,"docker_mutation":false,"enrollment_record_consumption":true,"filesystem_mutation":false,"installer_execution":false,"network_contact":false,"production_claims":false,"publish_release":false},"configuration_digest":"30a66283d7c7d0e775a0de417201e1ba8bee2c96a980cf62da68d58e2dfdb883","mode":{"approval_required":true,"autonomous_actions":false,"gateway_enabled":false,"observation_only":true},"product":"Bolt-On Continuity v0.4","qualified_stage_3_head":"c6aa6590b46e802b1e59d05f3af94c2ce9ed58a0","retention":{"maximum_incidents":1000,"mode":"retain_until_operator_deletes"},"schema_version":1,"stage":4,"stage_3_qualification_record_sha256":"1715c97822c5639b4850a46f28f5620b09c19a981e1b32e93ecb4f9bbc741bf0","stage_3_verifier_manifest_sha256":"f68cee14b5c47572e84b839cd2b2917f7c2c3f706bc87a7f83c0937b5e5fdbc9","storage":{"data_directory":"data/bolt-on-continuity","maximum_receipt_bytes_per_incident":1048576,"persistence_authorized":false},"subject":{"container_id":"e9bb79a0afa1913de3604814cfe26e77c67b7c8cdc74ce31eb0584128b116ea3","display_name":"bolt-on-v0-4-stage4-fixture","image":"alpine:3.20","platform":"linux"}}''')

def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def main() -> None:
    assert QUALIFIED_STAGE_8_HEAD == "c31c0101e8bc97957f225f9a1892aba648a78e70"
    assert STAGE_8_QUALIFICATION_RECORD_SHA256 == "b8c371184857f2c5d5d024562caca9e9195d16ca82115c467a774762ecb467b8"
    assert STAGE_8_VERIFIER_MANIFEST_SHA256 == "09949caf33f16bbae695612fc4bd086f28d973a4277933f8f523c322e9bea6c0"
    assert {key for key, value in AUTHORITY.items() if value} == {
        "stage_4_configuration_consumption",
        "stage_8_record_binding",
        "installation_plan_construction",
        "uninstall_plan_construction",
        "retention_choice_validation",
        "deletion_confirmation_validation",
    }
    sample = plan_install(CONFIG, "ABSENT").body()
    assert sample["outcome"] == "PLAN_INSTALL"
    assert sample["native_execution_authorized"] is False
    assert sample["filesystem_mutation_performed"] is False
    assert sample["container_mutation_authorized"] is False

    manifest = {path: digest((ROOT / path).read_bytes()) for path in FILES}
    record = {
        "files": FILES,
        "qualified_stage_8_head": QUALIFIED_STAGE_8_HEAD,
        "stage": 9,
        "stage_8_qualification_record_sha256": STAGE_8_QUALIFICATION_RECORD_SHA256,
        "stage_8_verifier_manifest_sha256": STAGE_8_VERIFIER_MANIFEST_SHA256,
    }
    print("Stage 9 qualification record SHA-256:", digest(canonical(record)))
    print("Stage 9 verifier manifest SHA-256:", digest(canonical(manifest)))
    print("BOLT-ON CONTINUITY v0.4 STAGE 9 VERIFICATION PASSED: 6 files")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, sys, unittest
from dataclasses import replace
from pathlib import Path

HERE=Path(__file__).resolve(); PROJECT=HERE.parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
rc=load("v04_stage6_rc_manifest",PROJECT/"release_candidate"/"release_candidate_manifest.py")
stage=load("v04_stage6_pilot",PROJECT/"integration"/"external_pilot_qualification.py")

class Stage6QualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q=stage.qualify()
        cls.manifest=cls.q["manifest"]
        cls.receipts=cls.q["receipts"]
        cls.attacks=stage.tamper_campaign(cls.receipts,cls.manifest)

# 24 core tests
def core_test(index):
    def test(self):
        q=self.q
        checks=(
            stage.STAGE_VERSION=="0.4.6",stage.MODE=="EXTERNAL_PILOT_RELEASE_CANDIDATE",
            stage.RELEASE_STATUS=="RELEASE_CANDIDATE",stage.BOLT_ON_EXECUTION_AUTHORITY=="NONE",
            stage.HOST_EXECUTION_BOUNDARY=="NATIVE_HOST_ONLY",len(stage.STAGE_PATHS)==5,
            len(stage.STAGE_MARKERS)==5,len(q["stage_hashes"])==5,len(self.manifest)==25,
            q["manifest_digest"]==stage.digest(self.manifest),len(self.receipts)==11,
            q["replay"] is True,q["replay_digest"]==q["receipt_digest"],q["deterministic"] is True,
            q["tamper_cases"]==64,q["tamper_safe"]==64,len(self.attacks)==64,
            all(ok for _,ok in self.attacks),self.receipts[-1].kind=="RC_VERDICT",
            '"freeze_performed":false' in self.receipts[-1].payload,
            tuple(x[0] for x in self.manifest)==tuple(sorted(x[0] for x in self.manifest)),
            len({x[0] for x in self.manifest})==25,
            all(len(x[1])==64 for x in self.manifest),
            all(all(c in "0123456789abcdef" for c in x[1]) for x in self.manifest),
        )
        self.assertTrue(checks[index])
    return test
for i in range(24): setattr(Stage6QualificationTests,f"test_core_{i+1:03d}",core_test(i))

# 64 attack-specific tests
def attack_test(index):
    def test(self): self.assertTrue(self.attacks[index][1])
    return test
for i in range(64): setattr(Stage6QualificationTests,f"test_attack_{i+1:03d}",attack_test(i))

# 16 receipt mutation tests
def receipt_test(index):
    def test(self):
        r=self.receipts[index%len(self.receipts)]
        bad=replace(r,payload=r.payload+str(index))
        rows=list(self.receipts); rows[index%len(rows)]=bad
        self.assertFalse(stage.replay(rows)[0])
    return test
for i in range(16): setattr(Stage6QualificationTests,f"test_receipt_mutation_{i+1:03d}",receipt_test(i))

# 16 manifest helper tests
def manifest_test(index):
    def test(self):
        rows=((f"p{index:02d}",f"{index%16:x}"*64),(f"q{index:02d}",f"{(index+1)%16:x}"*64))
        m=rc.build_manifest(rows,"a"*64); ok,reason=rc.validate_manifest(m)
        self.assertTrue(ok); self.assertEqual(reason,"PASS"); self.assertEqual(m.status,"RELEASE_CANDIDATE")
    return test
for i in range(16): setattr(Stage6QualificationTests,f"test_manifest_{i+1:03d}",manifest_test(i))

if __name__=="__main__":unittest.main()

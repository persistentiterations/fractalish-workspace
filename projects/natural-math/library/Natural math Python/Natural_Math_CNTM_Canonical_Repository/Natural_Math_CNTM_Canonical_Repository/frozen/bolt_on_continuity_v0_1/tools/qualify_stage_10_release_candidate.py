from __future__ import annotations
import importlib.util,json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
P=BASE/"release"/"release_candidate_verifier.py"
s=importlib.util.spec_from_file_location("_rc10",P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
r=m.ReleaseCandidateVerifier(BASE).qualify()
print(json.dumps(r,sort_keys=True,separators=(",",":")))
assert r["qualified"] is True
assert r["controlled_native_operations"]==["inspect","pause","unpause"]
assert r["production_use_qualified"] is False
print("BOLT-ON CONTINUITY FOR DOCKER v0.1 RELEASE CANDIDATE: PASS")

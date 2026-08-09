from __future__ import annotations
import importlib.util, json, sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
MODULE = BASE / "src" / "bolt_on_continuity" / "integration" / "controlled_live_pipeline.py"
spec = importlib.util.spec_from_file_location("_stage8_fixture", MODULE)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

CID = "a" * 64
class FakeTransport:
    def __init__(self):
        self.running = True
        self.paused = False
    def invoke(self, args):
        op = args[1]
        if op == "inspect":
            payload = [{"Id": CID, "State": {"Running": self.running, "Paused": self.paused}}]
            return {"args": args, "returncode": 0, "stdout": json.dumps(payload), "stderr": ""}
        if op == "pause":
            self.paused = True
            return {"args": args, "returncode": 0, "stdout": CID + "\\n", "stderr": ""}
        if op == "unpause":
            self.paused = False
            return {"args": args, "returncode": 0, "stdout": CID + "\\n", "stderr": ""}
        return {"args": args, "returncode": 1, "stdout": "", "stderr": "rejected"}

result = module.ControlledLivePipeline(BASE, CID, FakeTransport()).qualify(7317)
print(json.dumps(result, sort_keys=True, separators=(",", ":")))
assert result["qualified"] is True
assert result["continuity_verification_pass"] is True
assert result["final_state"]["running"] is True
assert result["final_state"]["paused"] is False
assert result["recovery_attempted"] is False
print("STAGE 8 CONTROLLED LIVE PIPELINE FIXTURE: PASS")

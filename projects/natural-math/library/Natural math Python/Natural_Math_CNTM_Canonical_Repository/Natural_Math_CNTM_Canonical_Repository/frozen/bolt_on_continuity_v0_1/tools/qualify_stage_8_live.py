from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
HARNESS = BASE / "src" / "bolt_on_continuity" / "integration" / "controlled_live_pipeline.py"
EXECUTOR = BASE / "src" / "bolt_on_continuity" / "execution" / "controlled_native_executor.py"

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

parser = argparse.ArgumentParser()
parser.add_argument("--container-id", required=True)
parser.add_argument("--acknowledge-disposable-container", action="store_true")
parser.add_argument("--issued-at-epoch", type=int, default=7317)
args = parser.parse_args()

if not args.acknowledge_disposable_container:
    raise SystemExit("Refused: --acknowledge-disposable-container is required")

harness = load(HARNESS, "_stage8_live_harness")
executor = load(EXECUTOR, "_stage8_live_executor")
transport = executor.DockerSubprocessTransport()
result = harness.ControlledLivePipeline(BASE, args.container_id, transport).qualify(args.issued_at_epoch)
print(json.dumps(result, sort_keys=True, separators=(",", ":")))
if not result["qualified"]:
    raise SystemExit("Stage 8 qualification did not qualify")
if result["final_state"]["running"] is not True or result["final_state"]["paused"] is not False:
    raise SystemExit("Stage 8 terminal state invalid")
print("STAGE 8 CONTROLLED LIVE END-TO-END QUALIFICATION: PASS")

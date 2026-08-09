"""Standard-input CLI for Stage 8 recovery classification."""
from __future__ import annotations
import argparse,json,sys
from collections.abc import Sequence
from .stage_8 import RecoveryError,classify_recovery,render_human

def main(argv:Sequence[str]|None=None)->int:
    parser=argparse.ArgumentParser(prog="bolt-continuity-stage-8")
    parser.add_argument("--json",action="store_true",dest="as_json")
    args=parser.parse_args(argv)
    try:
        raw=sys.stdin.read()
        if not raw.strip(): raise RecoveryError("RECOVERY_INPUT_REQUIRED")
        result=classify_recovery(json.loads(raw))
        print(result.canonical_json() if args.as_json else render_human(result))
        return 0
    except (RecoveryError,json.JSONDecodeError) as exc:
        print(f"STAGE_8_ERROR {exc}")
        return 2
if __name__=="__main__": raise SystemExit(main())

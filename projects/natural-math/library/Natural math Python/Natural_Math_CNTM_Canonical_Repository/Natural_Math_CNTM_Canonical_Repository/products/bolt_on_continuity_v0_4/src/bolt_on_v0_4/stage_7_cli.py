"""Standard-input CLI for Stage 7 data-only operator control."""
from __future__ import annotations
import argparse, json, sys
from collections.abc import Sequence
from .stage_7 import ApprovalError, GatewayState, create_request, record_decision, render_human, result, transition_gateway, validate_decision, validate_request

def build_parser()->argparse.ArgumentParser:
    p=argparse.ArgumentParser(prog="bolt-continuity-stage-7")
    p.add_argument("operation",choices=("request","gateway","decide","validate-request","validate-decision"))
    p.add_argument("--json",action="store_true",dest="as_json")
    return p

def main(argv:Sequence[str]|None=None)->int:
    args=build_parser().parse_args(argv)
    try:
        raw=json.loads(sys.stdin.read())
        if args.operation=="request": item=create_request(**raw).body()
        elif args.operation=="gateway": item=transition_gateway(GatewayState(raw["current_state"],raw["current_sequence"]),raw["target_state"],raw["sequence"]).body()
        elif args.operation=="decide": item=record_decision(raw["request"],GatewayState(raw["gateway"]["state"],raw["gateway"]["sequence"]),raw["decision"],raw["reason_code"],raw["decision_sequence"],raw.get("prior",())).body()
        elif args.operation=="validate-request": item=validate_request(raw,raw.get("expiry_sequence")).body()
        else: item=validate_decision(raw).body()
        out=result(args.operation,item); print(out.canonical_json() if args.as_json else render_human(out)); return 0
    except (ApprovalError,json.JSONDecodeError,KeyError,TypeError) as exc:
        print(f"STAGE_7_ERROR {exc}"); return 2
if __name__=="__main__": raise SystemExit(main())

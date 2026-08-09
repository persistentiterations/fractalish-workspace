"""Standard-input CLI for Stage 6 incident review and in-memory export."""
from __future__ import annotations
import argparse
from collections.abc import Sequence
import json
import sys
from .stage_6 import IncidentError, export_incident, explain_incident, list_incidents, render_human, replay_incident

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bolt-continuity-stage-6", description="Review supplied incidents without runtime or Docker authority")
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list")
    listing.add_argument("--limit", type=int, default=100)
    listing.add_argument("--json", action="store_true", dest="as_json")
    for command in ("explain", "replay", "export"):
        child = sub.add_parser(command)
        child.add_argument("--json", action="store_true", dest="as_json")
    return parser

def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            raise IncidentError("INCIDENT_INPUT_REQUIRED")
        value = json.loads(raw)
        if args.command == "list":
            result = list_incidents(value, args.limit)
        elif args.command == "explain":
            result = explain_incident(value)
        elif args.command == "replay":
            result = replay_incident(value)
        else:
            result = export_incident(value)
        print(result.canonical_json() if args.as_json else render_human(result))
        return 0
    except (IncidentError, json.JSONDecodeError) as exc:
        print(f"STAGE_6_ERROR {exc}")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())

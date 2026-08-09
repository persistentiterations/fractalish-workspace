"""Standard-input CLI for deterministic RC1 preparation."""
from __future__ import annotations
import argparse
import json
import sys
from .rc1 import QUALIFIED_STAGE_10_HEAD, prepare_rc1, render_human


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        value = json.load(sys.stdin)
        evidence = value["evidence"] if isinstance(value, dict) else value
        source_head = value.get("source_head", QUALIFIED_STAGE_10_HEAD) if isinstance(value, dict) else QUALIFIED_STAGE_10_HEAD
        report = prepare_rc1(evidence, source_head)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        report = prepare_rc1([], "")
    print(report.canonical_json() if args.json else render_human(report))
    return 0 if report.body()["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

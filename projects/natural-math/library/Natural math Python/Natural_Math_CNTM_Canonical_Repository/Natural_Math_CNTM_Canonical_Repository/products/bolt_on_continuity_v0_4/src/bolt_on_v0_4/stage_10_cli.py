"""Standard-input CLI for Stage 10 evidence qualification."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .stage_10 import QualificationError, qualify_evidence, render_human


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bolt-on-v0-4-stage-10")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        value = json.load(sys.stdin)
        report = qualify_evidence(value)
    except (json.JSONDecodeError, QualificationError, TypeError, ValueError) as exc:
        print(f"STAGE_10_REJECTED: {exc}", file=sys.stderr)
        return 2
    print(report.canonical_json() if args.json else render_human(report))
    return 0 if report.body()["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

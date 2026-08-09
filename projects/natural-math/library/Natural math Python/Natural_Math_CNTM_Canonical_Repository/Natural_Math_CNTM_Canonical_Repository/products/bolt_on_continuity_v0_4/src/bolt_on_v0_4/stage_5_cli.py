"""Standard-input CLI for Stage 5 observation-only lifecycle planning."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import sys

from .stage_5 import COMMANDS, execute, render_human


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bolt-continuity-stage-5",
        description="Validate Stage 4 configuration and construct lifecycle plans only",
    )
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configuration_bytes = sys.stdin.buffer.read()
    result = execute(args.command, configuration_bytes)
    print(result.canonical_json() if args.as_json else render_human(result))
    return 0 if result.body()["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

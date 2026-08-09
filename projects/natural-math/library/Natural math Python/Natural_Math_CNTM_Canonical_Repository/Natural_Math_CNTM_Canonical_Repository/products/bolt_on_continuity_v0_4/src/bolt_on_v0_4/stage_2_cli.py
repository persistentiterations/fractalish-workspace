"""Command-line entry point for the bounded Stage 2 Docker probe."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .stage_2 import collect_and_qualify, render_human


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bolt-continuity-stage-2",
        description="Run the bounded local Docker prerequisite probe",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="emit canonical JSON",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    report = collect_and_qualify()
    print(report.canonical_json() if arguments.as_json else render_human(report))
    return 0 if report.eligible else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Command-line interface for Stage 3 discovery and enrollment."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import shutil

from .stage_2 import collect_and_qualify, render_human as render_stage_two_human
from .stage_3 import (
    EnrollmentError,
    discover_candidates,
    inspect_and_enroll,
    render_discovery_human,
    render_enrollment_human,
    select_candidate,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bolt-continuity-stage-3",
        description="Bounded observation-only Docker container enrollment",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    discover = subcommands.add_parser(
        "discover",
        help="list existing local containers without modifying Docker",
    )
    discover.add_argument("--json", action="store_true", dest="as_json")

    enroll = subcommands.add_parser(
        "enroll",
        help="enroll one exact discovered container as observation-only data",
    )
    enroll.add_argument("--select", required=True, dest="selected_id")
    enroll.add_argument("--confirm", required=True, dest="confirmation_id")
    enroll.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    stage_two = collect_and_qualify()
    if not stage_two.eligible:
        if arguments.as_json:
            print(stage_two.canonical_json())
        else:
            print(render_stage_two_human(stage_two))
        return 3

    executable = shutil.which("docker")
    if not executable:
        print("STAGE_3_ERROR DOCKER_CLI_MISSING")
        return 2

    try:
        discovery = discover_candidates(executable)
        if arguments.command == "discover":
            print(
                discovery.canonical_json()
                if arguments.as_json
                else render_discovery_human(discovery)
            )
            return 0

        candidate = select_candidate(
            discovery.candidates,
            arguments.selected_id,
            arguments.confirmation_id,
        )
        record = inspect_and_enroll(executable, candidate)
        print(
            record.canonical_json()
            if arguments.as_json
            else render_enrollment_human(record)
        )
        return 0
    except EnrollmentError as exc:
        print(f"STAGE_3_ERROR {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

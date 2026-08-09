"""Read-only command-line entry point for the Stage 1 prerequisite doctor."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import os
import platform
import shutil
import sys

from .stage_1 import EnvironmentSnapshot, build_doctor_report, render_human

ENVIRONMENT_PATH_KEYS = (
    "LOCALAPPDATA",
    "APPDATA",
    "USERPROFILE",
    "XDG_STATE_HOME",
    "HOME",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bolt-continuity",
        description="Bolt-On Continuity v0.4 bounded product demonstrator",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    doctor = subcommands.add_parser(
        "doctor",
        help="inspect prerequisites without contacting or mutating Docker",
    )
    doctor.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="emit canonical JSON",
    )
    return parser


def current_snapshot() -> EnvironmentSnapshot:
    selected_environment = {
        key: os.environ[key]
        for key in ENVIRONMENT_PATH_KEYS
        if key in os.environ
    }
    return EnvironmentSnapshot(
        python_version=(
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        ),
        platform_system=platform.system(),
        environment=selected_environment,
        docker_cli_path=shutil.which("docker"),
    )


def render_doctor(snapshot: EnvironmentSnapshot, *, as_json: bool) -> str:
    report = build_doctor_report(snapshot)
    return report.canonical_json() if as_json else render_human(report)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command != "doctor":
        return 2
    report = build_doctor_report(current_snapshot())
    print(report.canonical_json() if arguments.as_json else render_human(report))
    return 0 if report.ready else 1

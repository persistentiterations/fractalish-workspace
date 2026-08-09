"""Safe Stage 0 through Stage 5 command-line interface."""

import argparse
import os
import platform
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

from bolt_on.discovery import DiscoveryError, discover, inspect_and_enroll, select
from bolt_on.environment import EnvironmentSnapshot, build_doctor_report
from bolt_on.lifecycle_stage5 import execute as execute_lifecycle
from bolt_on.prerequisites import collect_and_qualify
from bolt_on.receipts import canonical_json_bytes
from bolt_on.version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bolt", description="Bolt-On Continuity for Docker")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("version", help="display the product version")
    doctor = subcommands.add_parser("doctor", help="check local prerequisites without contacting Docker")
    doctor.add_argument("--json", action="store_true", dest="as_json", help="emit canonical JSON")
    prerequisites = subcommands.add_parser("prerequisites", help="run bounded read-only Docker prerequisite probes")
    prerequisites.add_argument("--json", action="store_true", dest="as_json", help="emit canonical JSON")
    discovery = subcommands.add_parser("discover", help="list local containers using one fixed read-only probe")
    discovery.add_argument("--json", action="store_true", dest="as_json", help="emit canonical JSON")
    enroll = subcommands.add_parser("enroll", help="construct one observation-only enrollment record")
    enroll.add_argument("container_id", help="exact full lowercase 64-character container ID")
    enroll.add_argument("confirmation_id", help="repeat the exact full container ID")
    enroll.add_argument("--json", action="store_true", dest="as_json", help="emit canonical JSON")
    for name in ("config-check", "status", "start", "stop"):
        lifecycle = subcommands.add_parser(name, help=f"Stage 5 {name} plan; no execution")
        lifecycle.add_argument("configuration", help="path to canonical Stage 4 configuration JSON")
    return parser


def current_snapshot() -> EnvironmentSnapshot:
    return EnvironmentSnapshot(
        python_version=(sys.version_info.major, sys.version_info.minor, sys.version_info.micro),
        platform_system=platform.system(),
        environment=dict(os.environ),
        docker_cli_path=shutil.which("docker"),
    )


def _print_doctor(as_json: bool) -> int:
    report = build_doctor_report(current_snapshot())
    if as_json:
        print(report.canonical_json())
    else:
        for check in report.checks:
            print(f"{check.status.value:4} {check.check_id}: {check.detail}")
        print("READY" if report.ready else "NOT READY")
    return 0 if report.ready else 1


def _print_prerequisites(as_json: bool) -> int:
    report = collect_and_qualify()
    if as_json:
        print(report.canonical_json())
    else:
        for key, value in report.details.items():
            print(f"{key}: {value}")
        if report.reason_codes:
            print("reason_codes: " + ",".join(report.reason_codes))
        print("ELIGIBLE" if report.eligible else "NOT ELIGIBLE")
    return 0 if report.eligible else 1


def _print_discovery(as_json: bool) -> int:
    try:
        candidates = discover()
    except DiscoveryError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if as_json:
        print(canonical_json_bytes({"containers": [item.body() for item in candidates], "schema_version": 1}).decode("utf-8"))
    else:
        for item in candidates:
            print(f"{item.container_id} {item.names} {item.image} {item.state} {item.status}")
        print(f"DISCOVERED {len(candidates)}")
    return 0


def _print_enrollment(container_id: str, confirmation_id: str, as_json: bool) -> int:
    try:
        candidate = select(discover(), container_id, confirmation_id)
        record = inspect_and_enroll(candidate)
    except DiscoveryError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if as_json:
        print(record.canonical_json())
    else:
        for key, value in record.body().items():
            print(f"{key}: {value}")
        print("ENROLLMENT RECORD CREATED; NOT PERSISTED")
    return 0


def _print_lifecycle(command: str, configuration: str) -> int:
    try:
        payload = Path(configuration).read_bytes()
    except OSError:
        result = execute_lifecycle(command, b"")
    else:
        result = execute_lifecycle(command, payload)
    print(result.canonical_json())
    return 0 if result.body["accepted"] else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "version":
        print(f"bolt {__version__}")
        return 0
    if args.command == "doctor":
        return _print_doctor(args.as_json)
    if args.command == "prerequisites":
        return _print_prerequisites(args.as_json)
    if args.command == "discover":
        return _print_discovery(args.as_json)
    if args.command == "enroll":
        return _print_enrollment(args.container_id, args.confirmation_id, args.as_json)
    if args.command in {"config-check", "status", "start", "stop"}:
        return _print_lifecycle(args.command, args.configuration)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

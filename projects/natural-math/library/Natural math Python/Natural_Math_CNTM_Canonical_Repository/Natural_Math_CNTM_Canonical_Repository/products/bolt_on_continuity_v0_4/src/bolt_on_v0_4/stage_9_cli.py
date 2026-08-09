"""Standard-input CLI for Stage 9 lifecycle planning."""
from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import sys

from .stage_9 import InstallationPlanError, plan_install, plan_uninstall, render_human


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bolt-continuity-stage-9")
    parser.add_argument("operation", choices=("install", "uninstall"))
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        raw = json.loads(sys.stdin.read())
        if not isinstance(raw, dict):
            raise InstallationPlanError("INPUT_OBJECT_REQUIRED")
        configuration = raw.get("configuration")
        installation_state = raw.get("installation_state")
        if args.operation == "install":
            plan = plan_install(configuration, installation_state)
        else:
            plan = plan_uninstall(
                configuration,
                installation_state,
                raw.get("retention_choice", "RETAIN_DATA"),
                raw.get("confirmation_token", ""),
            )
        if args.as_json:
            print(plan.canonical_json())
        else:
            print(render_human(plan))
        return 0
    except (json.JSONDecodeError, InstallationPlanError) as exc:
        print(f"STAGE_9_ERROR {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

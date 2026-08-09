"""Standard-input CLI for Stage 4 in-memory configuration construction."""
from __future__ import annotations
import argparse
from collections.abc import Sequence
import json
import sys
from .stage_4 import ConfigurationError, ConfigurationOptions, build_configuration, enrollment_from_mapping

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bolt-continuity-stage-4", description="Build a non-persistent canonical configuration from a Stage 3 enrollment receipt")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--data-directory", default="data/bolt-on-continuity")
    parser.add_argument("--maximum-incidents", type=int, default=1000)
    parser.add_argument("--maximum-receipt-bytes", type=int, default=1_048_576)
    parser.add_argument("--retention-mode", default="retain_until_operator_deletes")
    return parser

def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            raise ConfigurationError("ENROLLMENT_INPUT_REQUIRED")
        record = enrollment_from_mapping(json.loads(raw))
        configuration = build_configuration(record, ConfigurationOptions(args.data_directory, args.maximum_incidents, args.maximum_receipt_bytes, args.retention_mode))
        if args.as_json:
            print(configuration.canonical_json(), end="")
        else:
            body = configuration.body()
            print(f"PASS stage3.binding: {body['qualified_stage_3_head']}")
            print(f"PASS subject.id: {body['subject']['container_id']}")
            print("PASS mode: OBSERVATION_ONLY_APPROVAL_REQUIRED")
            print("PASS persistence: DENIED")
            print("PASS docker.contact: DENIED")
            print("STAGE_4_CONFIGURATION_READY")
            print(f"CONFIGURATION SHA-256 {configuration.configuration_digest}")
        return 0
    except (ConfigurationError, json.JSONDecodeError) as exc:
        print(f"STAGE_4_ERROR {exc}")
        return 2
if __name__ == "__main__": raise SystemExit(main())

"""Standard-input CLI for deterministic v0.4 release review."""
from __future__ import annotations
import argparse
import json
import sys
from .release_review import render_human, review_release


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("MALFORMED_REVIEW_INPUT", file=sys.stderr)
        return 2
    result = review_release(value)
    print(result.canonical_json() if args.json else render_human(result))
    return 0 if result.body()["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

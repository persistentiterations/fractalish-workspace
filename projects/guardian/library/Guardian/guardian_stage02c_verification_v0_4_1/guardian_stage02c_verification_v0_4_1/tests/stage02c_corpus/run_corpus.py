#!/usr/bin/env python3
"""Run the Stage 02C corpus and compare results with expected.json."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
GUARDIAN = ROOT / "guardian.py"
EXPECTED = json.loads((Path(__file__).parent / "expected.json").read_text())

failed = 0
for item in EXPECTED:
    target = ROOT / item["file"]
    with tempfile.TemporaryDirectory() as temp:
        ledger = Path(temp) / "ledger.jsonl"
        proc = subprocess.run(
            [sys.executable, "-S", str(GUARDIAN), "--ledger", str(ledger),
             "scan", str(target), "--json"],
            capture_output=True, text=True,
        )
        slip = json.loads(proc.stdout)
        actual = slip["intake_outcome"]
        ok = actual == item["expected"]
        print(f"{'PASS' if ok else 'FAIL'} {target.name}: expected={item['expected']} actual={actual}")
        failed += 0 if ok else 1

raise SystemExit(1 if failed else 0)

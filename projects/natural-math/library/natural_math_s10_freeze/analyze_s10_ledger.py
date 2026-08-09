#!/usr/bin/env python3
"""S10-9 Ledger Analyzer -- read CSV and produce summary report."""

import csv
import os
from collections import Counter

CSV_PATH = "/mnt/agents/output/s10_9_exact_ledger.csv"

def analyze():
    if not os.path.exists(CSV_PATH):
        print("Ledger not found: " + CSV_PATH)
        return

    rows = []
    with open(CSV_PATH, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    total = len(rows)
    passed = sum(1 for r in rows if r["Pass"] == "True")
    failed = total - passed

    fail_reasons = Counter(r["FailReason"] for r in rows if r["Pass"] == "False")

    fixture_counts = {}
    for r in rows:
        f = r["Fixture"]
        if f not in fixture_counts:
            fixture_counts[f] = {"total": 0, "pass": 0}
        fixture_counts[f]["total"] += 1
        if r["Pass"] == "True":
            fixture_counts[f]["pass"] += 1

    r_counts = {}
    for r in rows:
        R = int(r["R"])
        if R not in r_counts:
            r_counts[R] = {"total": 0, "pass": 0}
        r_counts[R]["total"] += 1
        if r["Pass"] == "True":
            r_counts[R]["pass"] += 1

    scream_on_success = sum(int(r["ScreamOnSuccessEdges"]) for r in rows)
    foll_contam = sum(1 for r in rows if r["FailReason"] == "FOLLOWER_CONTAMINATION")
    audit_fail_after_scout = sum(1 for r in rows if r["ScoutRC"] != "0" and r["FailReason"] in ("AUDIT_OUT_FAIL", "AUDIT_HOME_FAIL"))

    print("=" * 80)
    print("S10-9 Exact Ledger Analysis")
    print("=" * 80)
    print("\nTotal rows: " + str(total))
    print("Passed: " + str(passed) + " (" + str(round(passed/total*100, 1)) + "%)" if total > 0 else "Passed: 0")
    print("Failed: " + str(failed) + " (" + str(round(failed/total*100, 1)) + "%)" if total > 0 else "Failed: 0")
    print("\nFailure reasons:")
    for reason, count in fail_reasons.most_common():
        print("  " + reason + ": " + str(count))
    print("\nBy fixture:")
    for f, c in sorted(fixture_counts.items()):
        print("  " + f + ": " + str(c["pass"]) + "/" + str(c["total"]) + " pass")
    print("\nBy R:")
    for R in sorted(r_counts.keys()):
        c = r_counts[R]
        print("  R=" + str(R) + ": " + str(c["pass"]) + "/" + str(c["total"]) + " pass")
    print("\nScreamOnSuccessEdges total: " + str(scream_on_success))
    print("Follower contamination cases: " + str(foll_contam))
    print("Audit failures after ScoutRC>0: " + str(audit_fail_after_scout))
    print("=" * 80)


if __name__ == "__main__":
    analyze()

#!/usr/bin/env python3
"""S10-9 Ledger Runner -- append-only batch execution with deduplication."""

import sys
import os
import csv
import importlib.util

# Load control base
CONTROL_BASE = "/mnt/agents/output/s10_control_base.py"
spec = importlib.util.spec_from_file_location("s10_control_base", CONTROL_BASE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

run_seed_s10_5 = mod.run_seed_s10_5

CSV_PATH = "/mnt/agents/output/s10_9_exact_ledger.csv"

# Fixture map
FIXTURES = {
    "F1_close_original": ((0, 0), (9, 9), (5, 3)),
    "F2_close_swapped": ((0, 0), (9, 9), (5, 3)),
    "F3_close_corner": ((0, 0), (10, 10), (10, 0)),
}


def load_existing_rows():
    """Load existing (Fixture, Seed, R) tuples from CSV."""
    existing = set()
    if not os.path.exists(CSV_PATH):
        return existing
    with open(CSV_PATH, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["Fixture"], int(row["Seed"]), int(row["R"]))
            existing.add(key)
    return existing


def run_case(fixture_name, seed, R):
    """Run a single case and return the result dict."""
    base, a, b = FIXTURES[fixture_name]
    result = run_seed_s10_5(seed, base, a, b, relocate_rounds=R)
    return {
        "Fixture": fixture_name,
        "Seed": seed,
        "R": R,
        "ScoutRC": result["scout_relocate_cycles"],
        "PosEdges": result["positive_out_edges"],
        "ScreamEdges": len(result.get("scream_edges", {})),
        "ScreamOnSuccessEdges": result.get("scream_on_success", 0),
        "BaseCompReachesB": result["reaches_b"],
        "AuditOut": result["audit_out"],
        "OutSteps": result["audit_out_steps"],
        "AuditHome": result["audit_home"],
        "HomeSteps": result["audit_home_steps"],
        "FollowerRecall": result["foll_rate"],
        "Pass": result["pass"],
        "FailReason": result["fail_reason"],
    }


def append_rows(rows):
    """Append rows to CSV. Create with header if file does not exist."""
    file_exists = os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0
    fieldnames = [
        "Fixture", "Seed", "R", "ScoutRC", "PosEdges", "ScreamEdges",
        "ScreamOnSuccessEdges", "BaseCompReachesB", "AuditOut", "OutSteps",
        "AuditHome", "HomeSteps", "FollowerRecall", "Pass", "FailReason"
    ]
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    if len(sys.argv) < 5:
        print("Usage: python run_s10_ledger.py <fixture> <seed_start> <seed_end> <R_list>")
        print("Example: python run_s10_ledger.py F1_close_original 0 49 5,10,20")
        sys.exit(1)

    fixture = sys.argv[1]
    seed_start = int(sys.argv[2])
    seed_end = int(sys.argv[3])
    R_list = [int(x.strip()) for x in sys.argv[4].split(",")]

    existing = load_existing_rows()
    print("Existing rows in ledger: " + str(len(existing)))

    new_rows = []
    skipped = 0
    for seed in range(seed_start, seed_end + 1):
        for R in R_list:
            key = (fixture, seed, R)
            if key in existing:
                skipped += 1
                continue
            print("Running " + fixture + " seed=" + str(seed) + " R=" + str(R) + " ...")
            try:
                row = run_case(fixture, seed, R)
                new_rows.append(row)
                status = "PASS" if row["Pass"] else "FAIL:" + row["FailReason"]
                msg = "  -> " + status + " | ScoutRC=" + str(row["ScoutRC"])
                msg += " | AuditOut=" + row["AuditOut"] + " | Recall=" + str(round(row["FollowerRecall"], 2))
                print(msg)
            except Exception as e:
                print("  -> ERROR: " + str(e))

    if new_rows:
        append_rows(new_rows)
        print("\nAppended " + str(len(new_rows)) + " new rows. Skipped " + str(skipped) + " existing rows.")
    else:
        print("\nNo new rows to append. Skipped " + str(skipped) + " existing rows.")

    print("Total rows in ledger: " + str(len(existing) + len(new_rows)))


if __name__ == "__main__":
    main()

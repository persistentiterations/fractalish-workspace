#!/usr/bin/env python3
"""Scale Gate 4 threshold mapping for Natural Math v5."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from natural_math_cluster_oracle_runner import DEFAULT_PARAMS, run_cluster_summary, sha256
from natural_math_scale_gate_runner import failure_reason


SPEC_PATH = Path(r"C:\Users\big_b\Downloads\Natural Math v5 - Status Frozen Int.txt")
SPEC_SHA256 = "E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B"
SEEDS = list(range(50))
STEPS = 140

THRESHOLD_MAPS = {
    "rest_gain": [80, 110, 140, 170, 200, 220, 260, 300, 360, 440],
    "decay_cost": [110, 160, 220, 280, 340, 400, 440],
    "max_bonds": [1, 2, 3, 4, 5, 6],
    "world_size": [15, 25, 35, 45, 60],
    "damage_energy_loss": [7000, 14000, 17000, 21000, 25000],
    "move_cost": [150, 300, 450, 600, 750],
}


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def row_for(parameter: str, value: int, seed: int, summary: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    metrics = summary["metrics"]
    return {
        "parameter": parameter,
        "value": value,
        "seed": seed,
        "steps": STEPS,
        "passed": summary["passed"],
        "alive_count": metrics["alive_count"],
        "component_count": metrics["component_count"],
        "average_energy": metrics["average_energy"],
        "min_energy": metrics["min_energy"],
        "resource_reached": summary["resource_reached"],
        "resource_left": summary["resource_left"],
        "success_distance_passed": metrics["success_distance_passed"],
        "gini_num": metrics["gini_num"],
        "gini_den": metrics["gini_den"],
        "gini_over_threshold": metrics["gini_over_threshold"],
        "rng_draw_count": summary["rng_ppm_draw_count"],
        "failure_reason": failure_reason(summary, params),
    }


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["parameter"], int(row["value"])), []).append(row)
    out = []
    for (parameter, value), items in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1])):
        pass_count = sum(1 for row in items if row["passed"])
        failures: dict[str, int] = {}
        for row in items:
            if row["failure_reason"] == "PASS":
                continue
            for reason in str(row["failure_reason"]).split(";"):
                failures[reason] = failures.get(reason, 0) + 1
        out.append(
            {
                "parameter": parameter,
                "value": value,
                "runs": len(items),
                "passes": pass_count,
                "pass_rate": f"{pass_count}/{len(items)}",
                "avg_alive_count": sum(int(row["alive_count"]) for row in items) // len(items),
                "avg_average_energy": sum(int(row["average_energy"]) for row in items) // len(items),
                "resource_reached": sum(1 for row in items if row["resource_reached"]),
                "success_distance_passed": sum(1 for row in items if row["success_distance_passed"]),
                "failure_counts": failures,
            }
        )
    return out


def classify_band(pass_count: int, runs: int) -> str:
    if pass_count == runs:
        return "stable"
    if pass_count == 0:
        return "failure"
    return "transition"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    out_dir = Path(__file__).resolve().parent
    if sha256(SPEC_PATH) != SPEC_SHA256:
        raise RuntimeError("spec hash mismatch")

    rows = []
    for parameter, values in THRESHOLD_MAPS.items():
        for value in values:
            params = dict(DEFAULT_PARAMS)
            params[parameter] = value
            for seed in SEEDS:
                summary = run_cluster_summary(seed, params, STEPS)
                rows.append(row_for(parameter, value, seed, summary, params))

    csv_path = out_dir / "natural_math_scale_gate_4_threshold_mapping.csv"
    write_csv(csv_path, rows)
    summary = summarize(rows)

    json_path = out_dir / "natural_math_scale_gate_4_summary.json"
    payload = {
        "suite": "Natural Math v5 Scale Gate 4 threshold mapping",
        "spec_path": str(SPEC_PATH),
        "spec_sha256": SPEC_SHA256,
        "seeds": [SEEDS[0], SEEDS[-1]],
        "seed_count": len(SEEDS),
        "steps": STEPS,
        "threshold_maps": THRESHOLD_MAPS,
        "summary": summary,
        "csv": str(csv_path),
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    md_path = out_dir / "natural_math_scale_gate_4_summary.md"
    lines = [
        "# Natural Math v5 Scale Gate 4 Threshold Mapping",
        "",
        f"Spec SHA256: `{SPEC_SHA256}`",
        f"Seeds: `{SEEDS[0]}-{SEEDS[-1]}`",
        f"Steps per run: `{STEPS}`",
        "",
        "## Threshold Results",
        "",
    ]
    current = None
    for item in summary:
        if item["parameter"] != current:
            current = item["parameter"]
            lines.extend(["", f"### {current}", ""])
        band = classify_band(item["passes"], item["runs"])
        lines.append(
            f"- `{item['value']}`: `{item['pass_rate']}` pass, band `{band}`, "
            f"avg alive `{item['avg_alive_count']}`, avg energy `{item['avg_average_energy']}`, "
            f"success distance `{item['success_distance_passed']}/{item['runs']}`"
        )
        if item["failure_counts"]:
            lines.append(f"  - failures: `{item['failure_counts']}`")
    lines.extend(
        [
            "",
            "## Artifact Hashes",
            "",
            f"- Threshold CSV SHA256: `{file_hash(csv_path)}`",
            f"- Summary JSON SHA256: `{file_hash(json_path)}`",
            "",
            "## Claim Boundary",
            "",
            "This maps one-parameter-at-a-time stability bands for the listed values only. It does not test interacting parameter changes.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"passed": True, "summary": str(md_path), "csv": str(csv_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

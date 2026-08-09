#!/usr/bin/env python3
"""Scale gates for Natural Math v5 frozen cluster benchmark."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from natural_math_cluster_oracle_runner import DEFAULT_PARAMS, run_cluster_summary, sha256


SPEC_PATH = Path(r"C:\Users\big_b\Downloads\Natural Math v5 - Status Frozen Int.txt")
SPEC_SHA256 = "E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B"
SEEDS = list(range(50))
STEP_SWEEP = [0, 1, 35, 70, 140, 210, 300]

PARAMETER_VARIANTS = {
    "damage_energy_loss": [7000, 21000],
    "resource_absorb_rate": [7000, 21000],
    "decay_cost": [110, 440],
    "move_cost": [150, 600],
    "rest_gain": [110, 440],
    "repair_cost": [175, 700],
    "max_bonds": [2, 6],
    "world_size": [15, 35],
}


def failure_reason(summary: dict[str, Any], params: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    reasons = []
    if metrics["alive_count"] < 24:
        reasons.append(f"alive_count<{24}")
    if metrics["component_count"] != 1:
        reasons.append("component_count!=1")
    if metrics["average_energy"] < params["low_energy_cutoff"]:
        reasons.append(f"average_energy<{params['low_energy_cutoff']}")
    if not summary["resource_reached"]:
        reasons.append("resource_reached=False")
    if not metrics["success_distance_passed"]:
        reasons.append("success_distance_passed=False")
    return "PASS" if not reasons else ";".join(reasons)


def gini_string(metrics: dict[str, Any]) -> str:
    return f"{metrics['gini_num']}/{metrics['gini_den']}"


def result_row(seed: int, steps: int, params: dict[str, Any], summary: dict[str, Any], group: str, variant: str) -> dict[str, Any]:
    metrics = summary["metrics"]
    return {
        "group": group,
        "variant": variant,
        "seed": seed,
        "steps": steps,
        "passed": summary["passed"],
        "alive_count": metrics["alive_count"],
        "component_count": metrics["component_count"],
        "average_energy": metrics["average_energy"],
        "min_energy": metrics["min_energy"],
        "resource_reached": summary["resource_reached"],
        "resource_left": summary["resource_left"],
        "success_distance_passed": metrics["success_distance_passed"],
        "gini": gini_string(metrics),
        "gini_num": metrics["gini_num"],
        "gini_den": metrics["gini_den"],
        "gini_over_threshold": metrics["gini_over_threshold"],
        "rng_draw_count": summary["rng_ppm_draw_count"],
        "failure_reason": failure_reason(summary, params),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarize_rows(rows: list[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row[group_key]), []).append(row)
    summaries = []
    for key in sorted(grouped, key=lambda item: (len(item), item)):
        items = grouped[key]
        pass_count = sum(1 for row in items if str(row["passed"]) == "True")
        avg_alive = sum(int(row["alive_count"]) for row in items) // len(items)
        avg_energy = sum(int(row["average_energy"]) for row in items) // len(items)
        resource_reached = sum(1 for row in items if str(row["resource_reached"]) == "True")
        common_failures: dict[str, int] = {}
        for row in items:
            if row["failure_reason"] != "PASS":
                for reason in str(row["failure_reason"]).split(";"):
                    common_failures[reason] = common_failures.get(reason, 0) + 1
        summaries.append(
            {
                group_key: key,
                "runs": len(items),
                "passes": pass_count,
                "pass_rate_num": pass_count,
                "pass_rate_den": len(items),
                "average_alive_count": avg_alive,
                "average_average_energy": avg_energy,
                "resource_reached_count": resource_reached,
                "failure_counts": common_failures,
            }
        )
    return summaries


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> int:
    out_dir = Path(__file__).resolve().parent
    params = dict(DEFAULT_PARAMS)
    if sha256(SPEC_PATH) != SPEC_SHA256:
        raise RuntimeError("spec hash mismatch")

    seed_rows = []
    for seed in SEEDS:
        summary = run_cluster_summary(seed, params, 140)
        seed_rows.append(result_row(seed, 140, params, summary, "default_seed_sweep", "default"))

    step_rows = []
    for steps in STEP_SWEEP:
        for seed in SEEDS:
            summary = run_cluster_summary(seed, params, steps)
            step_rows.append(result_row(seed, steps, params, summary, "default_steps_sweep", f"steps={steps}"))

    sensitivity_rows = []
    for parameter, values in PARAMETER_VARIANTS.items():
        for value in values:
            variant_params = dict(DEFAULT_PARAMS)
            variant_params[parameter] = value
            variant_name = f"{parameter}={value}"
            for seed in SEEDS:
                summary = run_cluster_summary(seed, variant_params, 140)
                sensitivity_rows.append(result_row(seed, 140, variant_params, summary, "parameter_sensitivity", variant_name))

    seed_csv = out_dir / "natural_math_scale_gate_seed_sweep.csv"
    step_csv = out_dir / "natural_math_scale_gate_steps_sweep.csv"
    sensitivity_csv = out_dir / "natural_math_scale_gate_parameter_sensitivity.csv"
    write_csv(seed_csv, seed_rows)
    write_csv(step_csv, step_rows)
    write_csv(sensitivity_csv, sensitivity_rows)

    seed_summary = summarize_rows(seed_rows, "variant")
    step_summary = summarize_rows(step_rows, "steps")
    sensitivity_summary = summarize_rows(sensitivity_rows, "variant")

    report = {
        "suite": "Natural Math v5 scale gates",
        "spec_path": str(SPEC_PATH),
        "spec_sha256": SPEC_SHA256,
        "seeds": [SEEDS[0], SEEDS[-1]],
        "seed_count": len(SEEDS),
        "step_sweep": STEP_SWEEP,
        "parameter_variants": PARAMETER_VARIANTS,
        "seed_sweep_summary": seed_summary,
        "steps_sweep_summary": step_summary,
        "parameter_sensitivity_summary": sensitivity_summary,
        "artifacts": {
            "seed_sweep_csv": str(seed_csv),
            "steps_sweep_csv": str(step_csv),
            "parameter_sensitivity_csv": str(sensitivity_csv),
        },
    }

    json_path = out_dir / "natural_math_scale_gate_summary.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    md_path = out_dir / "natural_math_scale_gate_summary.md"
    lines = [
        "# Natural Math v5 Scale Gate Summary",
        "",
        f"Spec SHA256: `{SPEC_SHA256}`",
        "",
        "## Scale Gate 1: Default Seed Sweep",
        "",
    ]
    for item in seed_summary:
        lines.append(f"- `{item['variant']}`: {item['passes']}/{item['runs']} pass, avg alive {item['average_alive_count']}, avg energy {item['average_average_energy']}")
        if item["failure_counts"]:
            lines.append(f"  - failures: `{item['failure_counts']}`")
    lines.extend(["", "## Scale Gate 2: Steps Sweep", ""])
    for item in step_summary:
        lines.append(f"- steps `{item['steps']}`: {item['passes']}/{item['runs']} pass, avg alive {item['average_alive_count']}, avg energy {item['average_average_energy']}, resource reached {item['resource_reached_count']}/{item['runs']}")
        if item["failure_counts"]:
            lines.append(f"  - failures: `{item['failure_counts']}`")
    lines.extend(["", "## Scale Gate 3: Parameter Sensitivity", ""])
    for item in sensitivity_summary:
        lines.append(f"- `{item['variant']}`: {item['passes']}/{item['runs']} pass, avg alive {item['average_alive_count']}, avg energy {item['average_average_energy']}, resource reached {item['resource_reached_count']}/{item['runs']}")
        if item["failure_counts"]:
            lines.append(f"  - failures: `{item['failure_counts']}`")
    lines.extend(
        [
            "",
            "## Artifact Hashes",
            "",
            f"- Seed sweep CSV SHA256: `{file_hash(seed_csv)}`",
            f"- Steps sweep CSV SHA256: `{file_hash(step_csv)}`",
            f"- Parameter sensitivity CSV SHA256: `{file_hash(sensitivity_csv)}`",
            f"- Summary JSON SHA256: `{file_hash(json_path)}`",
            "",
            "## Claim Boundary",
            "",
            "This is a scale behavior report over exact frozen-v5 integer runs. It supports claims about these listed seeds, steps, and one-at-a-time parameter variants only.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"passed": True, "summary": str(md_path), "json": str(json_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

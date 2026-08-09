#!/usr/bin/env python3
"""Scale Gates 7 and 8 for Natural Math v5 base validation."""

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

GATE7_SEEDS = list(range(500))
GATE7_STEPS = 140
GATE7_VARIANTS = [
    {"name": "default", "params": {}},
    {"name": "rest_gain=200", "params": {"rest_gain": 200}},
    {"name": "decay_cost=280", "params": {"decay_cost": 280}},
    {"name": "max_bonds=3", "params": {"max_bonds": 3}},
    {"name": "world_size=35", "params": {"world_size": 35}},
    {"name": "damage_energy_loss=17000", "params": {"damage_energy_loss": 17000}},
    {"name": "move_cost=450", "params": {"move_cost": 450}},
]

GATE8_SEEDS = list(range(200))
GATE8_STEPS = [140, 300, 600, 1000]
GATE8_VARIANTS = [
    {"name": "default", "params": {}},
    {"name": "stable_stressed_rest260_damage17000", "params": {"rest_gain": 260, "damage_energy_loss": 17000}},
    {"name": "stable_stressed_resource_absorb_rate=7000", "params": {"resource_absorb_rate": 7000}},
]


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def gini_string(metrics: dict[str, Any]) -> str:
    return f"{metrics['gini_num']}/{metrics['gini_den']}"


def result_row(gate: str, variant: str, seed: int, steps: int, params: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    metrics = summary["metrics"]
    return {
        "gate": gate,
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
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(tuple(row[key] for key in keys), []).append(row)

    out = []
    for key, items in sorted(grouped.items(), key=lambda item: item[0]):
        pass_count = sum(1 for row in items if row["passed"])
        failures: dict[str, int] = {}
        representative_failures: list[dict[str, Any]] = []
        for row in items:
            if row["failure_reason"] == "PASS":
                continue
            if len(representative_failures) < 5:
                representative_failures.append({"seed": row["seed"], "failure_reason": row["failure_reason"]})
            for reason in str(row["failure_reason"]).split(";"):
                failures[reason] = failures.get(reason, 0) + 1
        item = {keys[index]: key[index] for index in range(len(keys))}
        item.update(
            {
                "runs": len(items),
                "passes": pass_count,
                "pass_rate": f"{pass_count}/{len(items)}",
                "avg_alive_count": sum(int(row["alive_count"]) for row in items) // len(items),
                "avg_average_energy": sum(int(row["average_energy"]) for row in items) // len(items),
                "min_average_energy": min(int(row["average_energy"]) for row in items),
                "resource_reached": sum(1 for row in items if row["resource_reached"]),
                "success_distance_passed": sum(1 for row in items if row["success_distance_passed"]),
                "failure_counts": failures,
                "representative_failures": representative_failures,
            }
        )
        out.append(item)
    return out


def run_gate7() -> list[dict[str, Any]]:
    rows = []
    for variant in GATE7_VARIANTS:
        params = dict(DEFAULT_PARAMS)
        params.update(variant["params"])
        for seed in GATE7_SEEDS:
            summary = run_cluster_summary(seed, params, GATE7_STEPS)
            rows.append(result_row("gate7_larger_seed_sweep", variant["name"], seed, GATE7_STEPS, params, summary))
    return rows


def run_gate8() -> list[dict[str, Any]]:
    rows = []
    for variant in GATE8_VARIANTS:
        params = dict(DEFAULT_PARAMS)
        params.update(variant["params"])
        for steps in GATE8_STEPS:
            for seed in GATE8_SEEDS:
                summary = run_cluster_summary(seed, params, steps)
                rows.append(result_row("gate8_long_run_stability", variant["name"], seed, steps, params, summary))
    return rows


def markdown_summary(gate7_summary: list[dict[str, Any]], gate8_summary: list[dict[str, Any]], hashes: dict[str, str]) -> str:
    lines = [
        "# Natural Math v5 Scale Gates 7 and 8",
        "",
        f"Spec SHA256: `{SPEC_SHA256}`",
        "",
        "## Gate 7: Larger Seed Sweep",
        "",
        f"Seeds: `{GATE7_SEEDS[0]}-{GATE7_SEEDS[-1]}`",
        f"Steps: `{GATE7_STEPS}`",
        "",
    ]
    for item in gate7_summary:
        lines.append(
            f"- `{item['variant']}`: `{item['pass_rate']}` pass, avg alive `{item['avg_alive_count']}`, "
            f"avg energy `{item['avg_average_energy']}`, min avg energy `{item['min_average_energy']}`"
        )
        if item["failure_counts"]:
            lines.append(f"  - failures: `{item['failure_counts']}`")

    lines.extend(
        [
            "",
            "## Gate 8: Long-Run Stability",
            "",
            f"Seeds: `{GATE8_SEEDS[0]}-{GATE8_SEEDS[-1]}`",
            f"Steps: `{GATE8_STEPS}`",
            "",
        ]
    )
    for item in gate8_summary:
        lines.append(
            f"- `{item['variant']}`, steps `{item['steps']}`: `{item['pass_rate']}` pass, "
            f"avg alive `{item['avg_alive_count']}`, avg energy `{item['avg_average_energy']}`, "
            f"resource reached `{item['resource_reached']}/{item['runs']}`"
        )
        if item["failure_counts"]:
            lines.append(f"  - failures: `{item['failure_counts']}`")

    lines.extend(
        [
            "",
            "## Artifact Hashes",
            "",
        ]
    )
    for name, digest in hashes.items():
        lines.append(f"- {name} SHA256: `{digest}`")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "Gate 7 expands seed coverage for the default and listed boundary settings. Gate 8 checks long-run stability for the default and listed stable-stressed settings. These gates do not tune parameters, alter the model, or validate future extensions.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    out_dir = Path(__file__).resolve().parent
    if sha256(SPEC_PATH) != SPEC_SHA256:
        raise RuntimeError("spec hash mismatch")

    gate7_rows = run_gate7()
    gate8_rows = run_gate8()
    gate7_summary = summarize(gate7_rows, ["variant"])
    gate8_summary = summarize(gate8_rows, ["variant", "steps"])

    gate7_csv = out_dir / "natural_math_scale_gate_7_larger_seed_sweep.csv"
    gate8_csv = out_dir / "natural_math_scale_gate_8_long_run_stability.csv"
    write_csv(gate7_csv, gate7_rows)
    write_csv(gate8_csv, gate8_rows)

    json_path = out_dir / "natural_math_scale_gate_7_8_summary.json"
    payload = {
        "suite": "Natural Math v5 Scale Gates 7 and 8",
        "spec_path": str(SPEC_PATH),
        "spec_sha256": SPEC_SHA256,
        "gate7": {
            "seeds": [GATE7_SEEDS[0], GATE7_SEEDS[-1]],
            "seed_count": len(GATE7_SEEDS),
            "steps": GATE7_STEPS,
            "variants": GATE7_VARIANTS,
            "run_count": len(gate7_rows),
            "summary": gate7_summary,
            "csv": str(gate7_csv),
        },
        "gate8": {
            "seeds": [GATE8_SEEDS[0], GATE8_SEEDS[-1]],
            "seed_count": len(GATE8_SEEDS),
            "steps": GATE8_STEPS,
            "variants": GATE8_VARIANTS,
            "run_count": len(gate8_rows),
            "summary": gate8_summary,
            "csv": str(gate8_csv),
        },
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    hashes = {
        "Gate 7 CSV": file_hash(gate7_csv),
        "Gate 8 CSV": file_hash(gate8_csv),
        "Summary JSON": file_hash(json_path),
    }
    md_path = out_dir / "natural_math_scale_gate_7_8_summary.md"
    md_path.write_text(markdown_summary(gate7_summary, gate8_summary, hashes), encoding="utf-8")

    print(
        json.dumps(
            {
                "passed": True,
                "gate7_runs": len(gate7_rows),
                "gate8_runs": len(gate8_rows),
                "summary": str(md_path),
                "gate7_csv": str(gate7_csv),
                "gate8_csv": str(gate8_csv),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

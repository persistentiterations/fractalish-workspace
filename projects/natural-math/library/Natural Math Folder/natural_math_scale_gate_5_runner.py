#!/usr/bin/env python3
"""Scale Gate 5 two-parameter interaction mapping for Natural Math v5."""

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

PAIR_GRIDS = [
    {
        "name": "rest_gain_x_decay_cost",
        "a": "rest_gain",
        "a_values": [140, 170, 200, 220, 260],
        "b": "decay_cost",
        "b_values": [160, 220, 280, 340],
    },
    {
        "name": "rest_gain_x_damage_energy_loss",
        "a": "rest_gain",
        "a_values": [170, 200, 220, 260],
        "b": "damage_energy_loss",
        "b_values": [14000, 17000, 21000, 25000],
    },
    {
        "name": "move_cost_x_world_size",
        "a": "move_cost",
        "a_values": [300, 450, 600, 750],
        "b": "world_size",
        "b_values": [25, 35, 45, 60],
    },
    {
        "name": "max_bonds_x_damage_energy_loss",
        "a": "max_bonds",
        "a_values": [2, 3, 4, 5],
        "b": "damage_energy_loss",
        "b_values": [14000, 17000, 21000, 25000],
    },
    {
        "name": "max_bonds_x_world_size",
        "a": "max_bonds",
        "a_values": [2, 3, 4, 5],
        "b": "world_size",
        "b_values": [25, 35, 45, 60],
    },
    {
        "name": "resource_absorb_rate_x_world_size",
        "a": "resource_absorb_rate",
        "a_values": [7000, 14000, 21000],
        "b": "world_size",
        "b_values": [25, 35, 45, 60],
    },
    {
        "name": "repair_cost_x_max_bonds",
        "a": "repair_cost",
        "a_values": [175, 350, 700],
        "b": "max_bonds",
        "b_values": [2, 3, 4, 5],
    },
]


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def gini_string(metrics: dict[str, Any]) -> str:
    return f"{metrics['gini_num']}/{metrics['gini_den']}"


def classify(pass_count: int, runs: int) -> str:
    if pass_count == runs:
        return "stable"
    if pass_count == 0:
        return "collapse"
    return "transition"


def result_row(
    pair: dict[str, Any],
    a_value: int,
    b_value: int,
    seed: int,
    params: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    metrics = summary["metrics"]
    return {
        "pair": pair["name"],
        "parameter_a": pair["a"],
        "value_a": a_value,
        "parameter_b": pair["b"],
        "value_b": b_value,
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


def summarize_cell(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pass_count = sum(1 for row in rows if row["passed"])
    failures: dict[str, int] = {}
    for row in rows:
        if row["failure_reason"] == "PASS":
            continue
        for reason in str(row["failure_reason"]).split(";"):
            failures[reason] = failures.get(reason, 0) + 1
    return {
        "runs": len(rows),
        "passes": pass_count,
        "pass_rate": f"{pass_count}/{len(rows)}",
        "band": classify(pass_count, len(rows)),
        "avg_alive_count": sum(int(row["alive_count"]) for row in rows) // len(rows),
        "avg_average_energy": sum(int(row["average_energy"]) for row in rows) // len(rows),
        "resource_reached": sum(1 for row in rows if row["resource_reached"]),
        "success_distance_passed": sum(1 for row in rows if row["success_distance_passed"]),
        "failure_counts": failures,
    }


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
    pair_order = {pair["name"]: index for index, pair in enumerate(PAIR_GRIDS)}
    for row in rows:
        key = (row["pair"], int(row["value_a"]), int(row["value_b"]))
        grouped.setdefault(key, []).append(row)

    out = []
    for (pair_name, value_a, value_b), items in sorted(
        grouped.items(), key=lambda item: (pair_order[item[0][0]], item[0][1], item[0][2])
    ):
        cell = summarize_cell(items)
        first = items[0]
        out.append(
            {
                "pair": pair_name,
                "parameter_a": first["parameter_a"],
                "value_a": value_a,
                "parameter_b": first["parameter_b"],
                "value_b": value_b,
                **cell,
            }
        )
    return out


def pair_summaries(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for cell in cells:
        grouped.setdefault(cell["pair"], []).append(cell)
    out = []
    for pair in PAIR_GRIDS:
        items = grouped[pair["name"]]
        stable = [cell for cell in items if cell["band"] == "stable"]
        transition = [cell for cell in items if cell["band"] == "transition"]
        collapse = [cell for cell in items if cell["band"] == "collapse"]
        out.append(
            {
                "pair": pair["name"],
                "parameter_a": pair["a"],
                "parameter_b": pair["b"],
                "cells": len(items),
                "runs": sum(cell["runs"] for cell in items),
                "stable_cells": len(stable),
                "transition_cells": len(transition),
                "collapse_cells": len(collapse),
                "best_cells": [
                    {
                        "value_a": cell["value_a"],
                        "value_b": cell["value_b"],
                        "pass_rate": cell["pass_rate"],
                        "band": cell["band"],
                    }
                    for cell in sorted(items, key=lambda item: (-item["passes"], item["value_a"], item["value_b"]))[:5]
                ],
                "worst_cells": [
                    {
                        "value_a": cell["value_a"],
                        "value_b": cell["value_b"],
                        "pass_rate": cell["pass_rate"],
                        "band": cell["band"],
                    }
                    for cell in sorted(items, key=lambda item: (item["passes"], item["value_a"], item["value_b"]))[:5]
                ],
            }
        )
    return out


def matrix_lines(pair: dict[str, Any], cells: list[dict[str, Any]]) -> list[str]:
    by_value = {(cell["value_a"], cell["value_b"]): cell for cell in cells if cell["pair"] == pair["name"]}
    lines = [
        f"### {pair['name']}",
        "",
        f"Rows: `{pair['a']}`. Columns: `{pair['b']}`. Cells show pass rate and band.",
        "",
        "| value | " + " | ".join(f"`{value}`" for value in pair["b_values"]) + " |",
        "|---|" + "|".join("---" for _ in pair["b_values"]) + "|",
    ]
    for a_value in pair["a_values"]:
        row = [f"`{a_value}`"]
        for b_value in pair["b_values"]:
            cell = by_value[(a_value, b_value)]
            row.append(f"`{cell['pass_rate']}` {cell['band']}")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return lines


def main() -> int:
    out_dir = Path(__file__).resolve().parent
    if sha256(SPEC_PATH) != SPEC_SHA256:
        raise RuntimeError("spec hash mismatch")

    rows = []
    for pair in PAIR_GRIDS:
        for a_value in pair["a_values"]:
            for b_value in pair["b_values"]:
                params = dict(DEFAULT_PARAMS)
                params[pair["a"]] = a_value
                params[pair["b"]] = b_value
                for seed in SEEDS:
                    summary = run_cluster_summary(seed, params, STEPS)
                    rows.append(result_row(pair, a_value, b_value, seed, params, summary))

    csv_path = out_dir / "natural_math_scale_gate_5_two_parameter_interactions.csv"
    cell_csv_path = out_dir / "natural_math_scale_gate_5_two_parameter_cells.csv"
    write_csv(csv_path, rows)
    cells = summarize(rows)
    write_csv(cell_csv_path, cells)

    pair_summary = pair_summaries(cells)
    json_path = out_dir / "natural_math_scale_gate_5_summary.json"
    payload = {
        "suite": "Natural Math v5 Scale Gate 5 two-parameter interaction mapping",
        "spec_path": str(SPEC_PATH),
        "spec_sha256": SPEC_SHA256,
        "seeds": [SEEDS[0], SEEDS[-1]],
        "seed_count": len(SEEDS),
        "steps": STEPS,
        "pair_grids": PAIR_GRIDS,
        "total_runs": len(rows),
        "pair_summary": pair_summary,
        "cell_summary": cells,
        "artifacts": {
            "run_csv": str(csv_path),
            "cell_csv": str(cell_csv_path),
        },
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    md_path = out_dir / "natural_math_scale_gate_5_summary.md"
    lines = [
        "# Natural Math v5 Scale Gate 5 Two-Parameter Interaction Mapping",
        "",
        f"Spec SHA256: `{SPEC_SHA256}`",
        f"Seeds: `{SEEDS[0]}-{SEEDS[-1]}`",
        f"Steps per run: `{STEPS}`",
        f"Total runs: `{len(rows)}`",
        "",
        "## Pair Summary",
        "",
    ]
    for item in pair_summary:
        lines.append(
            f"- `{item['pair']}`: `{item['stable_cells']}` stable cells, "
            f"`{item['transition_cells']}` transition cells, `{item['collapse_cells']}` collapse cells "
            f"across `{item['cells']}` grid cells."
        )
    lines.extend(["", "## Interaction Matrices", ""])
    for pair in PAIR_GRIDS:
        lines.extend(matrix_lines(pair, cells))
    lines.extend(
        [
            "## Artifact Hashes",
            "",
            f"- Run CSV SHA256: `{file_hash(csv_path)}`",
            f"- Cell CSV SHA256: `{file_hash(cell_csv_path)}`",
            f"- Summary JSON SHA256: `{file_hash(json_path)}`",
            "",
            "## Claim Boundary",
            "",
            "This maps the listed two-parameter grids only. It tests interaction zones around known thresholds, not the full parameter space.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "passed": True,
                "runs": len(rows),
                "summary": str(md_path),
                "run_csv": str(csv_path),
                "cell_csv": str(cell_csv_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

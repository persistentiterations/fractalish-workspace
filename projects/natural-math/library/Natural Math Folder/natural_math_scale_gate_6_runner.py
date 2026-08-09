#!/usr/bin/env python3
"""Scale Gate 6 failure-mode diagnosis for Natural Math v5."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from natural_math_cluster_oracle_runner import (
    ClusterTraceRng,
    DEFAULT_PARAMS,
    cluster_step,
    compute_metrics,
    initialize_cluster,
    live_bond_pairs,
    passed_diagnostic,
    sha256,
)


SPEC_PATH = Path(r"C:\Users\big_b\Downloads\Natural Math v5 - Status Frozen Int.txt")
SPEC_SHA256 = "E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B"
SEEDS = list(range(50))
STEPS = 140
DAMAGE_STEP = 35


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def center_distance(metrics: dict[str, Any], resource_pos: tuple[int, int, int]) -> tuple[int, int]:
    if metrics["center_sum"] is None or metrics["center_denominator"] == 0:
        return 0, 1
    den = metrics["center_denominator"]
    dx_num = metrics["center_sum"][0] - resource_pos[0] * den
    dy_num = metrics["center_sum"][1] - resource_pos[1] * den
    dz_num = metrics["center_sum"][2] - resource_pos[2] * den
    return dx_num * dx_num + dy_num * dy_num + dz_num * dz_num, den * den


def snapshot(
    scenario: dict[str, Any],
    seed: int,
    step: int,
    state: dict[str, Any],
    params: dict[str, Any],
    selected_action: str,
    prior_bond_count: int,
    prior_component_count: int,
) -> dict[str, Any]:
    metrics = compute_metrics(state["nodes"], state["resource_pos"], params)
    bond_count = len(live_bond_pairs(state["nodes"]))
    dist_num, dist_den = center_distance(metrics, state["resource_pos"])
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_source": scenario["source"],
        "parameter_a": scenario["parameter_a"],
        "value_a": scenario["value_a"],
        "parameter_b": scenario.get("parameter_b", ""),
        "value_b": scenario.get("value_b", ""),
        "seed": seed,
        "step": step,
        "alive_count": metrics["alive_count"],
        "component_count": metrics["component_count"],
        "average_energy": metrics["average_energy"],
        "min_energy": metrics["min_energy"],
        "resource_reached": state["resource_reached"],
        "resource_left": state["resource_left"],
        "success_distance_passed": metrics["success_distance_passed"],
        "gini_num": metrics["gini_num"],
        "gini_den": metrics["gini_den"],
        "bond_count": bond_count,
        "center_distance_sq_num": dist_num,
        "center_distance_sq_den": dist_den,
        "selected_cluster_action": selected_action,
        "damage_event_status": "damage_step" if step == DAMAGE_STEP else ("pre_damage" if step < DAMAGE_STEP else "post_damage"),
        "repair_attempt": selected_action == "REPAIR",
        "repair_success_signal": selected_action == "REPAIR" and (bond_count > prior_bond_count or metrics["component_count"] < prior_component_count),
        "passed_diagnostic": passed_diagnostic(metrics, state["resource_reached"], params),
    }


def load_gate4_scenarios(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    scenarios = []
    for item in data["summary"]:
        if item["passes"] == item["runs"]:
            continue
        parameter = item["parameter"]
        value = int(item["value"])
        scenarios.append(
            {
                "source": "gate4_single_parameter",
                "scenario_id": f"gate4:{parameter}={value}",
                "parameter_a": parameter,
                "value_a": value,
                "params": {parameter: value},
                "prior_pass_rate": item["pass_rate"],
                "prior_band": "collapse" if item["passes"] == 0 else "transition",
            }
        )
    return scenarios


def load_gate5_scenarios(path: Path) -> list[dict[str, Any]]:
    scenarios = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["band"] == "stable":
                continue
            value_a = int(row["value_a"])
            value_b = int(row["value_b"])
            scenarios.append(
                {
                    "source": "gate5_two_parameter",
                    "scenario_id": f"gate5:{row['pair']}:{row['parameter_a']}={value_a}:{row['parameter_b']}={value_b}",
                    "pair": row["pair"],
                    "parameter_a": row["parameter_a"],
                    "value_a": value_a,
                    "parameter_b": row["parameter_b"],
                    "value_b": value_b,
                    "params": {row["parameter_a"]: value_a, row["parameter_b"]: value_b},
                    "prior_pass_rate": row["pass_rate"],
                    "prior_band": row["band"],
                }
            )
    return scenarios


def load_scenarios(out_dir: Path) -> list[dict[str, Any]]:
    scenarios = load_gate4_scenarios(out_dir / "natural_math_scale_gate_4_summary.json")
    scenarios.extend(load_gate5_scenarios(out_dir / "natural_math_scale_gate_5_two_parameter_cells.csv"))
    return scenarios


def replay(scenario: dict[str, Any], seed: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params = dict(DEFAULT_PARAMS)
    params.update(scenario["params"])
    rng = ClusterTraceRng(seed)
    state = initialize_cluster(seed, params, rng)
    history = []
    actions = []
    for step in range(1, STEPS + 1):
        prior_bond_count = len(live_bond_pairs(state["nodes"]))
        prior_metrics = compute_metrics(state["nodes"], state["resource_pos"], params)
        action = cluster_step(state, params, rng, step)
        actions.append(action)
        history.append(snapshot(scenario, seed, step, state, params, action, prior_bond_count, prior_metrics["component_count"]))
    final = history[-1]
    return history, {
        "scenario_id": scenario["scenario_id"],
        "seed": seed,
        "params": params,
        "final": final,
        "passed": final["passed_diagnostic"],
        "resource_ever_reached": any(row["resource_reached"] for row in history),
        "passed_before_damage": any(row["step"] < DAMAGE_STEP and row["passed_diagnostic"] for row in history),
        "passed_after_damage": any(row["step"] >= DAMAGE_STEP and row["passed_diagnostic"] for row in history),
        "actions": actions,
    }


def first_step(history: list[dict[str, Any]], predicate: Any) -> int | None:
    for row in history:
        if predicate(row):
            return int(row["step"])
    return None


def classify_run(history: list[dict[str, Any]], run: dict[str, Any]) -> dict[str, Any]:
    params = run["params"]
    final = run["final"]
    cause_steps: dict[str, int] = {}
    if final["average_energy"] < params["low_energy_cutoff"]:
        step = first_step(history, lambda row: row["average_energy"] < params["low_energy_cutoff"])
        cause_steps["energy collapse"] = step or STEPS
    if not final["success_distance_passed"]:
        step = first_step(history, lambda row: not row["success_distance_passed"])
        cause_steps["distance failure"] = step or STEPS
    if final["component_count"] != 1:
        step = first_step(history, lambda row: row["component_count"] != 1)
        cause_steps["fragmentation failure"] = step or STEPS
    if final["alive_count"] < 24:
        step = first_step(history, lambda row: row["alive_count"] < 24)
        cause_steps["population loss"] = step or STEPS
    if not final["resource_reached"]:
        step = first_step(history, lambda row: not row["resource_reached"])
        cause_steps["resource failure"] = step or STEPS
        cause_steps["never reaches resource"] = step or STEPS
    if run["passed_before_damage"] and not final["passed_diagnostic"]:
        step = first_step(history, lambda row: row["step"] >= DAMAGE_STEP and not row["passed_diagnostic"])
        cause_steps["post-damage failure"] = step or DAMAGE_STEP
    if run["resource_ever_reached"] and final["average_energy"] < params["low_energy_cutoff"]:
        step = first_step(history, lambda row: row["resource_reached"] and row["average_energy"] < params["low_energy_cutoff"])
        cause_steps["recovery failure"] = step or STEPS
        cause_steps["reaches resource but cannot recover"] = step or STEPS
    if final["component_count"] == 1 and final["average_energy"] < params["low_energy_cutoff"]:
        step = first_step(history, lambda row: row["component_count"] == 1 and row["average_energy"] < params["low_energy_cutoff"])
        cause_steps["connected but too weak"] = step or STEPS
    if final["alive_count"] >= 24 and not final["success_distance_passed"]:
        step = first_step(history, lambda row: row["alive_count"] >= 24 and not row["success_distance_passed"])
        cause_steps["alive but too far"] = step or STEPS
    low_bond_threshold = max(1, min(24, params["max_bonds"] * 6))
    structure_step = first_step(
        history,
        lambda row: row["bond_count"] < low_bond_threshold or row["component_count"] != 1,
    )
    if structure_step is not None and not final["passed_diagnostic"]:
        cause_steps["structure failure"] = structure_step

    primary = {"energy collapse", "distance failure", "fragmentation failure", "population loss", "resource failure"}
    primary_count = len(primary.intersection(cause_steps))
    if primary_count >= 2:
        cause_steps["combined failure"] = min(cause_steps[cause] for cause in primary.intersection(cause_steps))

    earliest = min(cause_steps.values()) if cause_steps else None
    if earliest is None:
        phase = "pass"
    elif "post-damage failure" in cause_steps or DAMAGE_STEP <= earliest <= DAMAGE_STEP + 10:
        phase = "damage-triggered"
    elif earliest < DAMAGE_STEP:
        phase = "early"
    else:
        phase = "late"

    return {
        "causes": sorted(cause_steps),
        "cause_steps": cause_steps,
        "earliest_failure_step": earliest,
        "failure_phase": phase,
    }


def diagnose_cell(causes: dict[str, int], phases: dict[str, int]) -> str:
    if not causes:
        return "No failed runs in this diagnostic cell."
    ordered = sorted(causes.items(), key=lambda item: (-item[1], item[0]))
    top = ordered[0][0]
    if top == "energy collapse":
        diagnosis = "Primary mechanism is energy depletion below the low-energy cutoff."
    elif top == "distance failure":
        diagnosis = "Primary mechanism is inability to keep the live center within the success distance."
    elif top == "fragmentation failure":
        diagnosis = "Primary mechanism is structural fragmentation into multiple live components."
    elif top == "population loss":
        diagnosis = "Primary mechanism is live population falling below the survival threshold."
    elif top in {"resource failure", "never reaches resource"}:
        diagnosis = "Primary mechanism is failure to ever reach the resource."
    elif top in {"recovery failure", "reaches resource but cannot recover", "connected but too weak"}:
        diagnosis = "Primary mechanism is reaching resource without enough energy recovery."
    else:
        diagnosis = f"Primary mechanism is {top}."
    if phases:
        phase = sorted(phases.items(), key=lambda item: (-item[1], item[0]))[0][0]
        diagnosis += f" Most failures are {phase}."
    return diagnosis


def summarize_failures(run_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in run_rows:
        grouped.setdefault(row["scenario_id"], []).append(row)

    all_causes: dict[str, int] = {}
    representatives: dict[str, list[dict[str, Any]]] = {}
    summary = []
    for scenario_id, items in grouped.items():
        failures = [item for item in items if not item["passed"]]
        cause_counts: dict[str, int] = {}
        phase_counts: dict[str, int] = {}
        earliest_by_cause: dict[str, int] = {}
        reps_by_cause: dict[str, list[int]] = {}
        for item in failures:
            phase_counts[item["failure_phase"]] = phase_counts.get(item["failure_phase"], 0) + 1
            for cause in item["causes"]:
                cause_counts[cause] = cause_counts.get(cause, 0) + 1
                all_causes[cause] = all_causes.get(cause, 0) + 1
                step = int(item["cause_steps"][cause])
                earliest_by_cause[cause] = min(earliest_by_cause.get(cause, step), step)
                reps_by_cause.setdefault(cause, [])
                if len(reps_by_cause[cause]) < 3:
                    reps_by_cause[cause].append(item["seed"])
                representatives.setdefault(cause, [])
                if len(representatives[cause]) < 5:
                    representatives[cause].append({"scenario_id": scenario_id, "seed": item["seed"], "earliest_step": step})
        first = items[0]
        summary.append(
            {
                "scenario_id": scenario_id,
                "scenario_source": first["scenario_source"],
                "parameter_a": first["parameter_a"],
                "value_a": first["value_a"],
                "parameter_b": first.get("parameter_b", ""),
                "value_b": first.get("value_b", ""),
                "runs": len(items),
                "passes": sum(1 for item in items if item["passed"]),
                "failures": len(failures),
                "cause_counts": cause_counts,
                "representative_seeds_by_cause": reps_by_cause,
                "earliest_step_by_cause": earliest_by_cause,
                "failure_phase_counts": phase_counts,
                "diagnosis": diagnose_cell(cause_counts, phase_counts),
            }
        )
    summary.sort(key=lambda item: (item["scenario_source"], str(item["parameter_a"]), int(item["value_a"]), str(item["parameter_b"]), str(item["value_b"])))
    return summary, {"cause_counts": all_causes, "representatives": representatives}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def flatten_run_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        item = dict(row)
        item["causes"] = ";".join(row["causes"])
        item["cause_steps"] = json.dumps(row["cause_steps"], sort_keys=True)
        out.append(item)
    return out


def flatten_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        item = dict(row)
        item["cause_counts"] = json.dumps(row["cause_counts"], sort_keys=True)
        item["representative_seeds_by_cause"] = json.dumps(row["representative_seeds_by_cause"], sort_keys=True)
        item["earliest_step_by_cause"] = json.dumps(row["earliest_step_by_cause"], sort_keys=True)
        item["failure_phase_counts"] = json.dumps(row["failure_phase_counts"], sort_keys=True)
        out.append(item)
    return out


def main() -> int:
    out_dir = Path(__file__).resolve().parent
    if sha256(SPEC_PATH) != SPEC_SHA256:
        raise RuntimeError("spec hash mismatch")

    scenarios = load_scenarios(out_dir)
    history_rows = []
    run_rows = []
    for scenario in scenarios:
        for seed in SEEDS:
            history, run = replay(scenario, seed)
            history_rows.extend(history)
            classification = classify_run(history, run)
            final = run["final"]
            run_rows.append(
                {
                    "scenario_id": scenario["scenario_id"],
                    "scenario_source": scenario["source"],
                    "parameter_a": scenario["parameter_a"],
                    "value_a": scenario["value_a"],
                    "parameter_b": scenario.get("parameter_b", ""),
                    "value_b": scenario.get("value_b", ""),
                    "seed": seed,
                    "passed": run["passed"],
                    "final_alive_count": final["alive_count"],
                    "final_component_count": final["component_count"],
                    "final_average_energy": final["average_energy"],
                    "final_resource_reached": final["resource_reached"],
                    "final_success_distance_passed": final["success_distance_passed"],
                    "resource_ever_reached": run["resource_ever_reached"],
                    "passed_before_damage": run["passed_before_damage"],
                    "passed_after_damage": run["passed_after_damage"],
                    **classification,
                }
            )

    scenario_summary, global_summary = summarize_failures(run_rows)

    history_csv = out_dir / "natural_math_scale_gate_6_per_step_history.csv"
    run_csv = out_dir / "natural_math_scale_gate_6_run_classification.csv"
    summary_csv = out_dir / "natural_math_scale_gate_6_failure_summary_by_cell.csv"
    write_csv(history_csv, history_rows)
    write_csv(run_csv, flatten_run_rows(run_rows))
    write_csv(summary_csv, flatten_summary_rows(scenario_summary))

    json_path = out_dir / "natural_math_scale_gate_6_summary.json"
    payload = {
        "suite": "Natural Math v5 Scale Gate 6 failure-mode diagnosis",
        "spec_path": str(SPEC_PATH),
        "spec_sha256": SPEC_SHA256,
        "seeds": [SEEDS[0], SEEDS[-1]],
        "seed_count": len(SEEDS),
        "steps": STEPS,
        "damage_step": DAMAGE_STEP,
        "scenario_count": len(scenarios),
        "run_count": len(run_rows),
        "history_row_count": len(history_rows),
        "global_failure_summary": global_summary,
        "scenario_summary": scenario_summary,
        "artifacts": {
            "history_csv": str(history_csv),
            "run_classification_csv": str(run_csv),
            "failure_summary_csv": str(summary_csv),
        },
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    md_path = out_dir / "natural_math_scale_gate_6_summary.md"
    lines = [
        "# Natural Math v5 Scale Gate 6 Failure-Mode Diagnosis",
        "",
        f"Spec SHA256: `{SPEC_SHA256}`",
        f"Seeds: `{SEEDS[0]}-{SEEDS[-1]}`",
        f"Steps per run: `{STEPS}`",
        f"Scenarios diagnosed: `{len(scenarios)}`",
        f"Runs diagnosed: `{len(run_rows)}`",
        f"Per-step history rows: `{len(history_rows)}`",
        "",
        "## Global Failure Cause Counts",
        "",
    ]
    for cause, count in sorted(global_summary["cause_counts"].items(), key=lambda item: (-item[1], item[0])):
        reps = global_summary["representatives"].get(cause, [])
        lines.append(f"- `{cause}`: `{count}` failed-run labels; representative seeds `{reps[:5]}`")
    lines.extend(["", "## Cell Diagnoses", ""])
    for item in scenario_summary:
        if item["failures"] == 0:
            continue
        label = f"{item['parameter_a']}={item['value_a']}"
        if item["parameter_b"]:
            label += f", {item['parameter_b']}={item['value_b']}"
        lines.append(
            f"- `{item['scenario_source']}` `{label}`: `{item['passes']}/{item['runs']}` pass, "
            f"causes `{item['cause_counts']}`, phases `{item['failure_phase_counts']}`. {item['diagnosis']}"
        )
    lines.extend(
        [
            "",
            "## Artifact Hashes",
            "",
            f"- Per-step history CSV SHA256: `{file_hash(history_csv)}`",
            f"- Run classification CSV SHA256: `{file_hash(run_csv)}`",
            f"- Failure summary CSV SHA256: `{file_hash(summary_csv)}`",
            f"- Summary JSON SHA256: `{file_hash(json_path)}`",
            "",
            "## Claim Boundary",
            "",
            "This diagnoses failure modes for non-stable Gate 4 and Gate 5 cells only. It does not change the model, tune parameters, or prove behavior outside the tested weak and collapse zones.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "passed": True,
                "scenarios": len(scenarios),
                "runs": len(run_rows),
                "history_rows": len(history_rows),
                "summary": str(md_path),
                "history_csv": str(history_csv),
                "run_csv": str(run_csv),
                "summary_csv": str(summary_csv),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

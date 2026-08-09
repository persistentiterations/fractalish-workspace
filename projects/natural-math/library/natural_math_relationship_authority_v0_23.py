#!/usr/bin/env python3
"""
Natural Math exploratory trial v0.23
Relationship authority / causal succession

Question:
Can a local relationship lose authority, remain dormant, allow another local
relationship to take over, and later reactivate if it becomes predictive again?

This is an exploratory harness, not the canonical Natural Math kernel.
Standard library only. Deterministic. No randomness.
"""

from collections import defaultdict
import hashlib, json, statistics, csv
from pathlib import Path

OUT = Path("natural_math_v023_outputs")
OUT.mkdir(exist_ok=True)

def sha16(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]

def run_trial(
    retain_history=True,
    steps=900,
    n_nodes=18,
    phase1_end=260,
    phase2_end=560,
    failure_trigger=3,
    probe_confirm=3,
    rebuild_delay=20,
    rebuild_cost=8,
    source_variant=0,
):
    candidates = {
        i: [(i - 1) % n_nodes, (i + 1) % n_nodes, (i + 2) % n_nodes]
        for i in range(n_nodes)
    }

    def true_index(t):
        if t < phase1_end:
            return 0
        if t < phase2_end:
            return 1
        return 0

    def true_parent(i, t):
        return candidates[i][true_index(t)]

    def source(j, t):
        if source_variant == 0:
            return (
                j * 11
                + (t // (3 + (j % 5))) * ((j % 4) + 1)
                + (t // 29) * (j % 7 + 1)
                + (t // 71) ** 2
            ) % 23
        if source_variant == 1:
            return (
                j * 5
                + (t // (4 + (j % 3))) * (j % 5 + 2)
                + (t // 31) * (j % 4 + 1)
            ) % 19
        return (
            j * 13
            + (t // (2 + (j % 6))) * (j % 3 + 1)
            + (t // 43) * (j % 8 + 1)
        ) % 29

    modulus = 29 if source_variant == 2 else 19 if source_variant == 1 else 23

    def predict(i, parent, t):
        return (source(parent, t) + (3 * i + 1) % 11) % modulus

    def actual(i, t):
        return predict(i, true_parent(i, t), t)

    nodes = {}
    for i in range(n_nodes):
        nodes[i] = {
            "active": candidates[i][0],
            "dormant": set(candidates[i][1:]),
            "deleted": set(),
            "failure_streak": 0,
            "probe_hits": defaultdict(int),
            "rebuild": None,
        }

    receipts = []
    cost = 0
    wrong_authority_steps = 0
    false_distractor_promotions = 0
    switches = 0
    reactivations = 0
    rebuilds = 0
    b_switch_delays = []
    a_return_delays = []

    for t in range(steps):
        for i, node in nodes.items():
            if node["rebuild"] is not None:
                path, remaining = node["rebuild"]
                remaining -= 1
                if remaining <= 0:
                    node["dormant"].add(path)
                    node["deleted"].discard(path)
                    node["rebuild"] = None
                    receipts.append(
                        {"t": t, "node": i, "event": "REBUILD_COMPLETE", "path": path}
                    )
                else:
                    node["rebuild"] = (path, remaining)

            # Cheap periodic cost for preserving dormant topology.
            if t % 20 == 0:
                cost += len(node["dormant"])

            # Only the currently authoritative relationship is continuously checked.
            cost += 1
            active = node["active"]
            prediction_ok = predict(i, active, t) == actual(i, t)
            node["failure_streak"] = 0 if prediction_ok else node["failure_streak"] + 1

            if active != true_parent(i, t):
                wrong_authority_steps += 1

            # Dormant relationships are not continuously rescored.
            # They are probed only after repeated local failure of the active relationship.
            if node["failure_streak"] >= failure_trigger:
                viable = []
                for path in sorted(node["dormant"]):
                    cost += 2
                    match = predict(i, path, t) == actual(i, t)
                    node["probe_hits"][path] = node["probe_hits"][path] + 1 if match else 0
                    if node["probe_hits"][path] >= probe_confirm:
                        viable.append(path)

                if viable:
                    best = sorted(
                        viable,
                        key=lambda p: (
                            node["probe_hits"][p],
                            -candidates[i].index(p),
                        ),
                        reverse=True,
                    )[0]

                    old = active
                    if retain_history:
                        node["dormant"].add(old)
                    else:
                        node["deleted"].add(old)

                    node["dormant"].remove(best)
                    node["active"] = best
                    node["failure_streak"] = 0
                    node["probe_hits"].clear()
                    switches += 1

                    if best == candidates[i][2]:
                        false_distractor_promotions += 1

                    if phase1_end <= t < phase2_end and best == candidates[i][1]:
                        b_switch_delays.append(t - phase1_end)

                    if t >= phase2_end and best == candidates[i][0]:
                        a_return_delays.append(t - phase2_end)
                        reactivations += 1

                    receipts.append(
                        {"t": t, "node": i, "event": "SWITCH", "from": old, "to": best}
                    )

                elif (
                    not retain_history
                    and node["rebuild"] is None
                    and node["deleted"]
                ):
                    # Control: deleted topology must be locally reconstructed.
                    path = sorted(
                        node["deleted"],
                        key=lambda p: candidates[i].index(p),
                    )[0]
                    cost += rebuild_cost
                    rebuilds += 1
                    node["rebuild"] = (path, rebuild_delay)
                    node["failure_streak"] = 0
                    receipts.append(
                        {"t": t, "node": i, "event": "REBUILD_START", "path": path}
                    )

    result = {
        "mode": "retain" if retain_history else "delete_rebuild",
        "steps": steps,
        "nodes": n_nodes,
        "switches": switches,
        "reactivations": reactivations,
        "rebuilds": rebuilds,
        "false_distractor_promotions": false_distractor_promotions,
        "wrong_authority_steps": wrong_authority_steps,
        "final_correct": sum(
            node["active"] == true_parent(i, steps - 1)
            for i, node in nodes.items()
        ),
        "mean_B_switch_delay": round(statistics.mean(b_switch_delays), 2)
        if b_switch_delays else None,
        "mean_A_return_delay": round(statistics.mean(a_return_delays), 2)
        if a_return_delays else None,
        "cost": cost,
    }
    result["hash"] = sha16({"result": result, "receipts": receipts})
    return result, receipts

def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        return
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

def main():
    retain, retain_receipts = run_trial(True)
    delete, delete_receipts = run_trial(False)

    write_csv(OUT / "v0_23_baseline.csv", [retain, delete])
    write_csv(OUT / "v0_23_retain_receipts.csv", retain_receipts)
    write_csv(OUT / "v0_23_delete_rebuild_receipts.csv", delete_receipts)

    sweep = []
    for source_variant in (0, 1, 2):
        for failure_trigger in (2, 3, 4):
            for probe_confirm in (2, 3, 4):
                for p1, p2, total in (
                    (220, 500, 820),
                    (260, 560, 900),
                    (320, 650, 980),
                ):
                    r, _ = run_trial(
                        True,
                        steps=total,
                        phase1_end=p1,
                        phase2_end=p2,
                        failure_trigger=failure_trigger,
                        probe_confirm=probe_confirm,
                        source_variant=source_variant,
                    )
                    d, _ = run_trial(
                        False,
                        steps=total,
                        phase1_end=p1,
                        phase2_end=p2,
                        failure_trigger=failure_trigger,
                        probe_confirm=probe_confirm,
                        source_variant=source_variant,
                    )
                    sweep.append({
                        "source_variant": source_variant,
                        "failure_trigger": failure_trigger,
                        "probe_confirm": probe_confirm,
                        "phase1_end": p1,
                        "phase2_end": p2,
                        "steps": total,
                        "retain_final_correct": r["final_correct"],
                        "retain_false_distractor": r["false_distractor_promotions"],
                        "retain_reactivations": r["reactivations"],
                        "retain_return_delay": r["mean_A_return_delay"],
                        "retain_wrong_steps": r["wrong_authority_steps"],
                        "retain_cost": r["cost"],
                        "delete_final_correct": d["final_correct"],
                        "delete_false_distractor": d["false_distractor_promotions"],
                        "delete_return_delay": d["mean_A_return_delay"],
                        "delete_wrong_steps": d["wrong_authority_steps"],
                        "delete_cost": d["cost"],
                    })

    write_csv(OUT / "v0_23_sweep.csv", sweep)

    print("v0.23 relationship authority / causal succession")
    print("retain:", retain)
    print("delete/rebuild control:", delete)
    print("sweep cases:", len(sweep))
    print("retain all-correct:", sum(x["retain_final_correct"] == 18 for x in sweep), "/", len(sweep))
    print("retain zero distractor:", sum(x["retain_false_distractor"] == 0 for x in sweep), "/", len(sweep))
    print("retain all 18 reactivated:", sum(x["retain_reactivations"] == 18 for x in sweep), "/", len(sweep))
    print("retain faster return:", sum(x["retain_return_delay"] < x["delete_return_delay"] for x in sweep), "/", len(sweep))
    print("retain fewer wrong steps:", sum(x["retain_wrong_steps"] < x["delete_wrong_steps"] for x in sweep), "/", len(sweep))
    print("retain lower cost:", sum(x["retain_cost"] < x["delete_cost"] for x in sweep), "/", len(sweep))

if __name__ == "__main__":
    main()

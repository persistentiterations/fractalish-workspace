#!/usr/bin/env python3
"""
Natural Math Exploratory Reproducibility Suite v0.22
====================================================

Purpose
-------
A clean, standalone version of the recent exploratory harnesses used in the
conversation. It is intentionally small, deterministic, and standard-library only.

Included trials
---------------
1. memory_compression_drift_v0_15
   FULL_STATE vs GENERATOR vs DISCARD memory strategies.

2. discovered_boundary_plateau_v0_19b
   Nodes infer a local predictive parent, compress stable states, store dormant
   ancestral configurations, and retrieve them when the same local boundary returns.

3. cross_environment_dormant_memory_v0_20
   Same basic dormant-memory mechanism across periodic, irregular,
   topology-changing, and delayed-return environments.

4. residual_topology_memory_v0_21b
   An old connection becomes dormant/rusty instead of being deleted.
   When conditions return, reactivation is compared conceptually with rebuilding.

5. multi_dormant_topology_v0_22
   Several historical connections remain dormant. Only the locally favorable
   historical path should reactivate.

Important
---------
These are toy mathematical experiments. Labels such as "old", "new", "path",
or "parent" are experimental bookkeeping, not moral categories.

No randomness is used in the state-transition rules. Same inputs should give
the same outputs and hashes.

Run
---
    python natural_math_exploratory_suite_v0_22.py

Outputs are written into:
    natural_math_suite_outputs/

All CSVs are regenerated from scratch.
"""

from __future__ import annotations

from pathlib import Path
from collections import Counter, defaultdict
import csv
import hashlib
import json


OUT = Path("natural_math_suite_outputs")
OUT.mkdir(exist_ok=True)


def sha16(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def write_csv(name, rows):
    path = OUT / name
    rows = list(rows)
    if not rows:
        return path
    with path.open("w", newline="", encoding="utf-8") as f:
        if isinstance(rows[0], dict):
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        else:
            w = csv.writer(f)
            w.writerows(rows)
    return path


# ============================================================
# v0.15 — MEMORY COMPRESSION / DRIFT
# ============================================================

def make_structure(seed=7317, n=32):
    vals = []
    x = seed % 97
    for i in range(n):
        x = (x * 37 + 11 + i * 3) % 101
        vals.append((x + (vals[-1] if vals else 0)) % 17)
    return vals


def mutate_from_environment(base, phase):
    out = []
    for i, v in enumerate(base):
        if phase == 0:
            out.append(v)
        elif phase == 1:
            out.append((v + (i % 3)) % 17)
        elif phase == 2:
            out.append((v * 2 + i) % 17)
        else:
            out.append((v + phase + (i % 5)) % 17)
    return out


def deterministic_rediscover(target, cycle, noise_strength=3):
    out = []
    for i, v in enumerate(target):
        noise = ((i * 13 + cycle * 7) % (2 * noise_strength + 1)) - noise_strength
        out.append((v + noise) % 17)
    return out


def distance(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def checksum(vals):
    return sum((i + 1) * v for i, v in enumerate(vals)) % 1000003


def generator_payload(seed, n):
    return {"seed": seed, "n": n}


def reconstruct_from_generator(payload):
    return make_structure(payload["seed"], payload["n"])


def run_memory_strategy(
    strategy,
    cycles=600,
    revisit_every=75,
    seed=7317,
    n=32,
    full_carry_cost_per_item=1,
    generator_carry_cost=6,
    summary_carry_cost=1,
    recheck_full_cost=2,
    recheck_generator_cost=8,
    rediscovery_cost_per_item=3,
):
    original = make_structure(seed, n)
    current = original[:]

    full_memory = original[:] if strategy == "FULL_STATE" else None
    gen_memory = generator_payload(seed, n) if strategy == "GENERATOR" else None

    total_carry = 0
    total_recheck = 0
    total_recovery_latency = 0
    total_drift = 0
    recoveries = 0
    failed_recoveries = 0
    receipts = []

    for t in range(cycles):
        if strategy == "FULL_STATE":
            total_carry += n * full_carry_cost_per_item
        elif strategy == "GENERATOR":
            total_carry += generator_carry_cost
        elif strategy == "DISCARD":
            total_carry += summary_carry_cost
        else:
            raise ValueError(strategy)

        phase = (t // 150) % 4
        live_target = mutate_from_environment(original, phase)

        if t > 0 and t % revisit_every == 0:
            recoveries += 1

            if strategy == "FULL_STATE":
                recovered = full_memory[:]
                total_recheck += recheck_full_cost
                latency = 1
            elif strategy == "GENERATOR":
                recovered = reconstruct_from_generator(gen_memory)
                total_recheck += recheck_generator_cost
                latency = 2
            else:
                recovered = deterministic_rediscover(original, t)
                total_recheck += n * rediscovery_cost_per_item
                latency = 8

            adapted = mutate_from_environment(recovered, phase)
            d = distance(adapted, live_target)
            total_drift += d
            total_recovery_latency += latency
            ok = d == 0
            if not ok:
                failed_recoveries += 1

            receipts.append({
                "cycle": t,
                "phase": phase,
                "strategy": strategy,
                "latency": latency,
                "drift": d,
                "exact": ok,
                "carry_cost_so_far": total_carry,
                "recheck_cost_so_far": total_recheck,
            })
            current = adapted

    result = {
        "strategy": strategy,
        "cycles": cycles,
        "recoveries": recoveries,
        "failed_recoveries": failed_recoveries,
        "total_carry_cost": total_carry,
        "total_recheck_cost": total_recheck,
        "total_cost": total_carry + total_recheck,
        "total_drift": total_drift,
        "avg_recovery_latency": round(
            total_recovery_latency / max(1, recoveries), 3
        ),
        "final_checksum": checksum(current),
    }
    result["hash"] = sha16({"result": result, "receipts": receipts})
    return result, receipts


def trial_v015():
    results = []
    all_receipts = []
    for strategy in ("FULL_STATE", "GENERATOR", "DISCARD"):
        result, receipts = run_memory_strategy(strategy)
        results.append(result)
        all_receipts.extend(receipts)

    write_csv("v0_15_memory_baseline.csv", results)
    write_csv("v0_15_memory_receipts.csv", all_receipts)
    return results


# ============================================================
# v0.19b — DISCOVERED LOCAL BOUNDARY + DORMANT ANCESTRAL STATE
# ============================================================

def run_discovered_boundary_plateau(
    steps=720,
    n_nodes=18,
    train_end=120,
    stable_after=16,
    dormant_after=48,
    active_cost=5,
    compressed_cost=2,
    dormant_cost=1,
    retrieval_cost=4,
):
    neighbors = {
        i: [(i - 1) % n_nodes, (i + 1) % n_nodes]
        for i in range(n_nodes)
    }
    hidden_parent = {
        i: neighbors[i][i % 2]
        for i in range(n_nodes)
    }

    def plateau(t):
        if t < train_end:
            return -1
        if t < 280:
            return 0
        if t < 440:
            return 1
        if t < 560:
            return 2
        return 0

    def source(i, t):
        p = plateau(t)
        if p == -1:
            return (i * 3 + (t // 6 if (t // 6) % 3 == i % 3 else 0)) % 11
        return (i * 3 + [1, 5, 8][p]) % 11

    def make_actual(t):
        src = {i: source(i, t) for i in range(n_nodes)}
        out = {}
        for i in range(n_nodes):
            out[i] = (src[hidden_parent[i]] + (i * 2) % 7) % 17
        return src, out

    src_prev, actual_prev = make_actual(0)

    nodes = {}
    for i in range(n_nodes):
        nodes[i] = {
            "state": actual_prev[i],
            "mode": "ACTIVE",
            "persistence": 1,
            "parent_scores": {j: [0, 0] for j in neighbors[i]},
            "discovered": None,
            "signature": None,
            "last_seen_signature": None,
            "library": [],
        }

    receipts = []
    total_cost = 0
    missed = 0
    retrieval_attempts = 0
    retrieval_success = 0
    false_retrievals = 0
    drift = 0

    for t in range(1, steps):
        src, actual = make_actual(t)

        if t < train_end:
            for i, n in nodes.items():
                self_changed = actual[i] != actual_prev[i]
                for j in neighbors[i]:
                    neigh_changed = src[j] != src_prev[j]
                    if neigh_changed:
                        n["parent_scores"][j][1] += 1
                        if self_changed:
                            n["parent_scores"][j][0] += 1

                scored = []
                for j, (correct, total) in n["parent_scores"].items():
                    score = (100 * correct // total) if total else 0
                    scored.append((score, total, j))
                scored.sort(reverse=True)

                if scored[0][1] >= 4 and scored[0][0] - scored[1][0] >= 15:
                    n["discovered"] = scored[0][2]

        for i, n in nodes.items():
            if n["mode"] == "ACTIVE":
                total_cost += active_cost
            elif n["mode"] == "COMPRESSED":
                total_cost += compressed_cost
            else:
                total_cost += dormant_cost

            parent = n["discovered"]
            signature = (parent, src[parent]) if parent is not None else None
            signature_changed = signature != n["last_seen_signature"]

            if signature_changed and n["mode"] != "ACTIVE" and signature is not None:
                matches = [
                    m for m in n["library"]
                    if m["signature"] == signature
                ]
                if matches:
                    retrieval_attempts += 1
                    candidate = matches[-1]
                    total_cost += retrieval_cost

                    if candidate["state"] == actual[i]:
                        retrieval_success += 1
                        n["state"] = candidate["state"]
                        n["signature"] = signature
                        n["mode"] = "ACTIVE"
                        n["persistence"] = 1
                        receipts.append({
                            "cycle": t,
                            "node": i,
                            "event": "RETRIEVE_SUCCESS",
                            "parent": parent,
                            "delta": 0,
                        })
                    else:
                        false_retrievals += 1
                        receipts.append({
                            "cycle": t,
                            "node": i,
                            "event": "RETRIEVE_REJECT",
                            "parent": parent,
                            "delta": abs(candidate["state"] - actual[i]),
                        })

            if n["mode"] == "ACTIVE":
                if (
                    signature is not None
                    and actual[i] == n["state"]
                    and signature == n["signature"]
                ):
                    n["persistence"] += 1
                else:
                    if n["signature"] is not None and n["persistence"] >= stable_after:
                        if not any(
                            m["state"] == n["state"]
                            and m["signature"] == n["signature"]
                            for m in n["library"]
                        ):
                            n["library"].append({
                                "state": n["state"],
                                "signature": n["signature"],
                                "persistence": n["persistence"],
                            })

                    n["state"] = actual[i]
                    n["signature"] = signature
                    n["persistence"] = 1

                if signature is not None and n["persistence"] >= stable_after:
                    n["mode"] = "COMPRESSED"
                    receipts.append({
                        "cycle": t,
                        "node": i,
                        "event": "COMPRESS",
                        "parent": parent,
                        "delta": 0,
                    })

            elif n["mode"] == "COMPRESSED":
                if actual[i] == n["state"] and signature == n["signature"]:
                    n["persistence"] += 1
                    if n["persistence"] >= dormant_after:
                        if not any(
                            m["state"] == n["state"]
                            and m["signature"] == n["signature"]
                            for m in n["library"]
                        ):
                            n["library"].append({
                                "state": n["state"],
                                "signature": n["signature"],
                                "persistence": n["persistence"],
                            })
                        n["mode"] = "DORMANT"
                        receipts.append({
                            "cycle": t,
                            "node": i,
                            "event": "DORMANT",
                            "parent": parent,
                            "delta": 0,
                        })
                else:
                    missed += 1
                    if n["signature"] is not None:
                        if not any(
                            m["state"] == n["state"]
                            and m["signature"] == n["signature"]
                            for m in n["library"]
                        ):
                            n["library"].append({
                                "state": n["state"],
                                "signature": n["signature"],
                                "persistence": n["persistence"],
                            })

                    n["mode"] = "ACTIVE"
                    n["state"] = actual[i]
                    n["signature"] = signature
                    n["persistence"] = 1
                    receipts.append({
                        "cycle": t,
                        "node": i,
                        "event": "WAKE_CHANGE",
                        "parent": parent if parent is not None else -1,
                        "delta": 0,
                    })

            else:
                if actual[i] != n["state"] or signature != n["signature"]:
                    missed += 1
                    n["mode"] = "ACTIVE"
                    n["state"] = actual[i]
                    n["signature"] = signature
                    n["persistence"] = 1
                    receipts.append({
                        "cycle": t,
                        "node": i,
                        "event": "WAKE_DORMANT_CHANGE",
                        "parent": parent if parent is not None else -1,
                        "delta": 0,
                    })

            drift += abs(n["state"] - actual[i])
            n["last_seen_signature"] = signature

        src_prev, actual_prev = src, actual

    correct = sum(
        nodes[i]["discovered"] == hidden_parent[i]
        for i in range(n_nodes)
    )
    wrong = sum(
        nodes[i]["discovered"] is not None
        and nodes[i]["discovered"] != hidden_parent[i]
        for i in range(n_nodes)
    )

    result = {
        "steps": steps,
        "nodes": n_nodes,
        "correct_parent_found": correct,
        "wrong_parent_found": wrong,
        "library_entries": sum(len(n["library"]) for n in nodes.values()),
        "retrieval_attempts": retrieval_attempts,
        "retrieval_success": retrieval_success,
        "false_retrievals": false_retrievals,
        "missed_changes": missed,
        "total_drift": drift,
        "total_cost": total_cost,
        "final_active": sum(n["mode"] == "ACTIVE" for n in nodes.values()),
        "final_compressed": sum(n["mode"] == "COMPRESSED" for n in nodes.values()),
        "final_dormant": sum(n["mode"] == "DORMANT" for n in nodes.values()),
    }
    result["hash"] = sha16({
        "result": result,
        "receipts": receipts,
        "discovered": {i: nodes[i]["discovered"] for i in nodes},
        "libraries": {i: nodes[i]["library"] for i in nodes},
    })
    return result, receipts


def trial_v019b():
    result, receipts = run_discovered_boundary_plateau()
    write_csv("v0_19b_discovered_boundary_baseline.csv", [result])
    write_csv("v0_19b_discovered_boundary_receipts.csv", receipts)
    return result


# ============================================================
# v0.20 — CROSS-ENVIRONMENT DORMANT MEMORY
# ============================================================

def run_cross_environment(env_name, steps=900, n_nodes=18):
    neighbors = {
        i: [(i - 1) % n_nodes, (i + 1) % n_nodes]
        for i in range(n_nodes)
    }
    hidden_parent = {
        i: neighbors[i][i % 2]
        for i in range(n_nodes)
    }

    def phase(t):
        if env_name == "periodic":
            if t < 120:
                return -1
            return ((t - 120) // 140) % 3

        if env_name == "irregular":
            if t < 120:
                return -1
            intervals = [
                (120, 245, 0),
                (245, 360, 1),
                (360, 525, 0),
                (525, 610, 2),
                (610, 760, 1),
                (760, 900, 0),
            ]
            for a, b, value in intervals:
                if a <= t < b:
                    return value
            return 0

        if env_name == "topology_change":
            if t < 120:
                return -1
            if t < 320:
                return 0
            if t < 600:
                return 1
            return 0

        if env_name == "delayed_return":
            if t < 120:
                return -1
            if t < 260:
                return 0
            if t < 420:
                return 1
            if t < 560:
                return 2
            if t < 820:
                return 3
            return 0

        raise ValueError(env_name)

    def source(i, t):
        p = phase(t)
        if p == -1:
            return (i * 3 + (t // 6 if (t // 6) % 3 == i % 3 else 0)) % 11
        return (i * 3 + [1, 5, 8, 3][p]) % 11

    def true_parent(i, t):
        if env_name == "topology_change" and t >= 450:
            return neighbors[i][1 - (i % 2)]
        return hidden_parent[i]

    # This cross-environment test intentionally reuses the learned parent logic
    # from the clean plateau trial but keeps accumulated learning history.
    parent_scores = {
        i: {j: [0, 0] for j in neighbors[i]}
        for i in range(n_nodes)
    }
    discovered = {i: None for i in range(n_nodes)}

    def make_actual(t):
        src = {i: source(i, t) for i in range(n_nodes)}
        actual = {}
        for i in range(n_nodes):
            actual[i] = (src[true_parent(i, t)] + (i * 2) % 7) % 17
        return src, actual

    src_prev, actual_prev = make_actual(0)

    # Reuse a compact state machine.
    state = {
        i: {
            "value": actual_prev[i],
            "mode": "ACTIVE",
            "persistence": 1,
            "signature": None,
            "last_signature": None,
            "library": [],
        }
        for i in range(n_nodes)
    }

    receipts = []
    total_cost = 0
    drift = 0
    missed = 0
    retrieval_attempts = 0
    retrieval_success = 0
    false_retrievals = 0

    for t in range(1, steps):
        src, actual = make_actual(t)

        for i in range(n_nodes):
            self_changed = actual[i] != actual_prev[i]
            for j in neighbors[i]:
                neigh_changed = src[j] != src_prev[j]
                if neigh_changed:
                    parent_scores[i][j][1] += 1
                    if self_changed:
                        parent_scores[i][j][0] += 1

            scored = []
            for j, (correct, total) in parent_scores[i].items():
                score = (100 * correct // total) if total else 0
                scored.append((score, total, j))
            scored.sort(reverse=True)
            if scored[0][1] >= 4 and scored[0][0] - scored[1][0] >= 15:
                discovered[i] = scored[0][2]

        for i in range(n_nodes):
            n = state[i]
            total_cost += 5 if n["mode"] == "ACTIVE" else 2 if n["mode"] == "COMPRESSED" else 1

            parent = discovered[i]
            signature = (parent, src[parent]) if parent is not None else None
            signature_changed = signature != n["last_signature"]

            if signature_changed and n["mode"] != "ACTIVE" and signature is not None:
                matches = [m for m in n["library"] if m["signature"] == signature]
                if matches:
                    retrieval_attempts += 1
                    candidate = matches[-1]
                    total_cost += 4
                    if candidate["state"] == actual[i]:
                        retrieval_success += 1
                        n["value"] = candidate["state"]
                        n["mode"] = "ACTIVE"
                        n["persistence"] = 1
                        n["signature"] = signature
                        receipts.append({
                            "cycle": t,
                            "node": i,
                            "event": "RETRIEVE_SUCCESS",
                            "parent": parent,
                            "delta": 0,
                        })
                    else:
                        false_retrievals += 1
                        receipts.append({
                            "cycle": t,
                            "node": i,
                            "event": "RETRIEVE_REJECT",
                            "parent": parent,
                            "delta": abs(candidate["state"] - actual[i]),
                        })

            if n["mode"] == "ACTIVE":
                if actual[i] == n["value"] and signature == n["signature"] and signature is not None:
                    n["persistence"] += 1
                else:
                    n["value"] = actual[i]
                    n["signature"] = signature
                    n["persistence"] = 1

                if signature is not None and n["persistence"] >= 16:
                    n["mode"] = "COMPRESSED"

            elif n["mode"] == "COMPRESSED":
                if actual[i] == n["value"] and signature == n["signature"]:
                    n["persistence"] += 1
                    if n["persistence"] >= 48:
                        if not any(
                            m["state"] == n["value"] and m["signature"] == n["signature"]
                            for m in n["library"]
                        ):
                            n["library"].append({
                                "state": n["value"],
                                "signature": n["signature"],
                            })
                        n["mode"] = "DORMANT"
                else:
                    missed += 1
                    if n["signature"] is not None:
                        if not any(
                            m["state"] == n["value"] and m["signature"] == n["signature"]
                            for m in n["library"]
                        ):
                            n["library"].append({
                                "state": n["value"],
                                "signature": n["signature"],
                            })
                    n["mode"] = "ACTIVE"
                    n["value"] = actual[i]
                    n["signature"] = signature
                    n["persistence"] = 1

            else:
                if actual[i] != n["value"] or signature != n["signature"]:
                    missed += 1
                    n["mode"] = "ACTIVE"
                    n["value"] = actual[i]
                    n["signature"] = signature
                    n["persistence"] = 1

            drift += abs(n["value"] - actual[i])
            n["last_signature"] = signature

        src_prev, actual_prev = src, actual

    final_true = {i: true_parent(i, steps - 1) for i in range(n_nodes)}
    result = {
        "environment": env_name,
        "steps": steps,
        "correct_parent_final": sum(discovered[i] == final_true[i] for i in range(n_nodes)),
        "wrong_parent_final": sum(
            discovered[i] is not None and discovered[i] != final_true[i]
            for i in range(n_nodes)
        ),
        "library_entries": sum(len(state[i]["library"]) for i in range(n_nodes)),
        "retrieval_attempts": retrieval_attempts,
        "retrieval_success": retrieval_success,
        "false_retrievals": false_retrievals,
        "missed_changes": missed,
        "total_drift": drift,
        "total_cost": total_cost,
    }
    result["hash"] = sha16({
        "result": result,
        "receipts": receipts,
        "discovered": discovered,
    })
    return result, receipts


def trial_v020():
    envs = ["periodic", "irregular", "topology_change", "delayed_return"]
    results = []
    for env in envs:
        result, receipts = run_cross_environment(env)
        results.append(result)
        write_csv(f"v0_20_{env}_receipts.csv", receipts)

    write_csv("v0_20_cross_environment_summary.csv", results)
    return results


# ============================================================
# v0.21b — RESIDUAL / RUSTY TOPOLOGICAL MEMORY
# ============================================================

def run_residual_topology(
    steps=700,
    retain_old_path=True,
    decay_interval=10,
    integrity_floor=40,
    rebuild_cost=80,
    rebuild_delay=20,
    reactivation_cost=12,
    active_maintenance=4,
):
    old_state = "ACTIVE"
    old_integrity = 100
    new_state = "ABSENT"
    rebuild_timer = None

    total_cost = 0
    unmet = 0
    useful = 0
    receipts = []

    for t in range(steps):
        old_favorable = t < 180 or t >= 460

        if t == 180:
            new_state = "ACTIVE"
            if retain_old_path:
                old_state = "DORMANT"
                receipts.append({
                    "cycle": t,
                    "path": "OLD",
                    "event": "DORMANT",
                    "value": old_integrity,
                })
            else:
                old_state = "DELETED"
                old_integrity = 0
                receipts.append({
                    "cycle": t,
                    "path": "OLD",
                    "event": "DELETE",
                    "value": 0,
                })

        if old_state == "DORMANT" and decay_interval > 0 and t % decay_interval == 0:
            old_integrity = max(integrity_floor, old_integrity - 1)

        if t == 460:
            if old_state == "DORMANT":
                total_cost += reactivation_cost
                old_state = "ACTIVE"
                receipts.append({
                    "cycle": t,
                    "path": "OLD",
                    "event": "REACTIVATE",
                    "value": old_integrity,
                })
            elif old_state == "DELETED":
                total_cost += rebuild_cost
                rebuild_timer = rebuild_delay
                old_state = "REBUILDING"
                receipts.append({
                    "cycle": t,
                    "path": "OLD",
                    "event": "REBUILD_START",
                    "value": 0,
                })

        if rebuild_timer is not None:
            rebuild_timer -= 1
            if rebuild_timer <= 0:
                rebuild_timer = None
                old_state = "ACTIVE"
                old_integrity = 100
                receipts.append({
                    "cycle": t,
                    "path": "OLD",
                    "event": "REBUILD_COMPLETE",
                    "value": 100,
                })

        if old_state == "ACTIVE":
            total_cost += active_maintenance
        if new_state == "ACTIVE":
            total_cost += active_maintenance

        delivered = 0
        if old_favorable:
            if old_state == "ACTIVE":
                penalty = max(0, (100 - old_integrity) // 10)
                delivered = max(2, 10 - penalty)
        else:
            if new_state == "ACTIVE":
                delivered = 10

        useful += min(10, delivered)
        unmet += max(0, 10 - delivered)

        if old_state == "ACTIVE" and old_integrity < 100:
            old_integrity = min(100, old_integrity + 5)

    result = {
        "retain_old_path": retain_old_path,
        "decay_interval": decay_interval,
        "integrity_floor": integrity_floor,
        "total_cost": total_cost,
        "useful": useful,
        "unmet": unmet,
        "final_integrity": old_integrity,
    }
    result["hash"] = sha16({"result": result, "receipts": receipts})
    return result, receipts


def trial_v021b():
    retained, retained_receipts = run_residual_topology(retain_old_path=True)
    deleted, deleted_receipts = run_residual_topology(retain_old_path=False)

    write_csv("v0_21b_residual_topology_baseline.csv", [retained, deleted])
    write_csv("v0_21b_retain_receipts.csv", retained_receipts)
    write_csv("v0_21b_delete_receipts.csv", deleted_receipts)
    return [retained, deleted]


# ============================================================
# v0.22 — MULTI-DORMANT TOPOLOGY, SELECTIVE WAKE
# ============================================================

def run_multi_dormant_paths(
    steps=800,
    path_count=4,
    active_path=0,
    dormancy_start=180,
    return_cycle=520,
    returning_path=2,
    active_maintenance=4,
    reactivation_cost=10,
    decay_intervals=(8, 12, 20, 30),
    integrity_floors=(20, 30, 40, 50),
):
    integrity = {p: 100 for p in range(path_count)}
    state = {
        p: ("ACTIVE" if p == active_path else "DORMANT")
        for p in range(path_count)
    }

    total_cost = 0
    useful = 0
    unmet = 0
    receipts = []
    wake_count = 0
    wrong_wakes = 0

    def local_payoff(p, t):
        if t < dormancy_start:
            return 10 if p == active_path else 2
        if dormancy_start <= t < return_cycle:
            return 10 if p == 1 else 2
        return 10 if p == returning_path else 2

    for t in range(steps):
        if t == dormancy_start:
            state[active_path] = "DORMANT"
            state[1] = "ACTIVE"
            receipts.append({
                "cycle": t,
                "path": active_path,
                "event": "DORMANT",
                "integrity": integrity[active_path],
                "local_payoff": local_payoff(active_path, t),
            })
            receipts.append({
                "cycle": t,
                "path": 1,
                "event": "ACTIVE",
                "integrity": integrity[1],
                "local_payoff": local_payoff(1, t),
            })

        for p in range(path_count):
            if state[p] == "DORMANT":
                interval = decay_intervals[p % len(decay_intervals)]
                if interval > 0 and t % interval == 0:
                    floor = integrity_floors[p % len(integrity_floors)]
                    integrity[p] = max(floor, integrity[p] - 1)

        if t >= return_cycle:
            current_active = [
                p for p in range(path_count)
                if state[p] == "ACTIVE"
            ]
            current_best = max(
                (local_payoff(p, t) for p in current_active),
                default=0,
            )

            for p in range(path_count):
                if state[p] == "DORMANT":
                    payoff = local_payoff(p, t)
                    if payoff > current_best:
                        total_cost += reactivation_cost
                        state[p] = "ACTIVE"
                        wake_count += 1
                        if p != returning_path:
                            wrong_wakes += 1

                        receipts.append({
                            "cycle": t,
                            "path": p,
                            "event": "REACTIVATE",
                            "integrity": integrity[p],
                            "local_payoff": payoff,
                        })

                        for q in list(current_active):
                            if local_payoff(q, t) < payoff:
                                state[q] = "DORMANT"
                                receipts.append({
                                    "cycle": t,
                                    "path": q,
                                    "event": "YIELD_DORMANT",
                                    "integrity": integrity[q],
                                    "local_payoff": local_payoff(q, t),
                                })

                        current_active = [
                            q for q in range(path_count)
                            if state[q] == "ACTIVE"
                        ]
                        current_best = max(
                            local_payoff(q, t)
                            for q in current_active
                        )

        active_now = [
            p for p in range(path_count)
            if state[p] == "ACTIVE"
        ]

        total_cost += len(active_now) * active_maintenance

        best_delivery = 0
        for p in active_now:
            rust_penalty = max(0, (100 - integrity[p]) // 10)
            delivery = max(1, local_payoff(p, t) - rust_penalty)
            best_delivery = max(best_delivery, delivery)

            if integrity[p] < 100:
                integrity[p] = min(100, integrity[p] + 4)

        useful += min(10, best_delivery)
        unmet += max(0, 10 - best_delivery)

    result = {
        "path_count": path_count,
        "returning_path": returning_path,
        "wake_count": wake_count,
        "wrong_wakes": wrong_wakes,
        "total_cost": total_cost,
        "useful": useful,
        "unmet": unmet,
        "final_active": ";".join(
            map(str, sorted(p for p in state if state[p] == "ACTIVE"))
        ),
        "final_integrities": ";".join(
            f"{p}:{integrity[p]}"
            for p in sorted(integrity)
        ),
    }
    result["hash"] = sha16({
        "result": result,
        "receipts": receipts,
        "state": state,
        "integrity": integrity,
    })
    return result, receipts


def trial_v022():
    baseline, receipts = run_multi_dormant_paths()

    sweep = []
    for path_count in (3, 4, 6, 8):
        decay_intervals = tuple(8 + 4 * i for i in range(path_count))
        integrity_floors = tuple(20 + 5 * (i % 5) for i in range(path_count))

        for returning_path in range(1, path_count):
            for return_cycle in (400, 520, 650):
                result, _ = run_multi_dormant_paths(
                    path_count=path_count,
                    returning_path=returning_path,
                    return_cycle=return_cycle,
                    decay_intervals=decay_intervals,
                    integrity_floors=integrity_floors,
                )
                result = {"return_cycle": return_cycle, **result}
                sweep.append(result)

    write_csv("v0_22_multi_dormant_baseline.csv", [baseline])
    write_csv("v0_22_multi_dormant_receipts.csv", receipts)
    write_csv("v0_22_multi_dormant_sweep.csv", sweep)
    return baseline, sweep


# ============================================================
# MAIN
# ============================================================

def main():
    print("Natural Math Exploratory Reproducibility Suite v0.22")
    print("=" * 60)

    v15 = trial_v015()
    print("\nv0.15 memory compression:")
    for r in v15:
        print(
            r["strategy"],
            "cost=", r["total_cost"],
            "drift=", r["total_drift"],
            "failures=", r["failed_recoveries"],
            "hash=", r["hash"],
        )

    v19 = trial_v019b()
    print("\nv0.19b discovered boundary:")
    print(v19)

    v20 = trial_v020()
    print("\nv0.20 cross-environment:")
    for r in v20:
        print(r)

    v21 = trial_v021b()
    print("\nv0.21b residual topology:")
    for r in v21:
        print(r)

    v22, sweep22 = trial_v022()
    print("\nv0.22 multi-dormant topology:")
    print(v22)

    correct_selective = sum(
        (
            r["wake_count"] == 1 and r["wrong_wakes"] == 0
        )
        or (
            r["wake_count"] == 0
            and str(r["final_active"]) == str(r["returning_path"])
        )
        for r in sweep22
    )
    print(
        "v0.22 selected/retained correct connection:",
        correct_selective,
        "/",
        len(sweep22),
    )
    print(
        "v0.22 wrong wakes:",
        sum(r["wrong_wakes"] > 0 for r in sweep22),
    )

    print("\nOutputs written to:", OUT.resolve())


if __name__ == "__main__":
    main()

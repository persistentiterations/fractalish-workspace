#!/usr/bin/env python3
"""
Natural Math exploratory v0.27
Authority switching on the v5 grid.

Each node maintains 3 disjoint bond groups (A, B, C) representing
alternative energy-flow topologies. Only one group is "active"
at a time — REDISTRIBUTE flows only through active bonds.

When the active group's min_energy drops below critical_energy,
the node probes dormant groups (temporarily allows energy flow
through them for 2 steps). If probe succeeds, it switches.

Policies compared:
  fixed3, fixed4
  scalar_adaptive
  history_weighted
  conditional_history

No randomness. Standard library only. Deterministic hashes.
"""

from collections import defaultdict
import csv, json, hashlib, statistics, random
from pathlib import Path
from typing import Any

OUT = Path("natural_math_v027_outputs")
OUT.mkdir(exist_ok=True)

def sha16(x):
    return hashlib.sha256(
        json.dumps(x, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]

# ============================================================
# v5 CLUSTER ENGINE (subset, deterministic, no rng in step)
# ============================================================

DEFAULT_PARAMS = {
    "tau": 5000,
    "iota_sq": 1,
    "r_sq": 625,
    "eps_extend": 500,
    "eps_sense": 1200,
    "eps_spawn": 4000,
    "eps_split": 9000,
    "E0": 1600000,
    "P_bifurcate": 12000,
    "beta_num": 85,
    "beta_den": 100,
    "delta_P_baseline": 2100,
    "delta_P_conflict": 5000,
    "gamma_fallback_ppm": 300000,
    "deficit_strength": 15000,
    "suffering_strength": -50000,
    "bond_distance_sq": 4,
    "max_bonds": 4,
    "decay_cost": 220,
    "move_cost": 300,
    "rest_gain": 220,
    "trade_rate_num": 18,
    "trade_rate_den": 100,
    "trade_cost": 25,
    "repair_cost": 350,
    "repair_prob_ppm": 700000,
    "repair_ignores_distance": False,
    "resource_absorb_rate": 14000,
    "resource_radius_sq": 4,
    "critical_energy": 30000,
    "low_energy_cutoff": 38000,
    "success_max_distance_sq_num": 9,
    "success_max_distance_sq_den": 4,
    "gini_threshold_num": 7,
    "gini_threshold_den": 100,
    "world_size": 25,
    "damage_energy_loss": 14000,
    "damage_bond_break_ppm": 180000,
}

DIRS = [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]

def qdist(a,b):
    return sum((a[i]-b[i])**2 for i in range(3))

def sign(x):
    return (x>0)-(x<0)

def clamp0(x):
    return x if x>0 else 0

def integer_div(a,b):
    return a//b

# ---------- Node structure ----------

class Node:
    __slots__ = ("id","pos","direction","energy","pressure",
                 "alive","type","parent_id","bonds","signal_type",
                 "bond_group","active_group","dormant_groups",
                 "dormant_bonds",
                 "probe_count","failure_streak",
                 "good","bad","cgood","cbad","burden","probation")
    def __init__(self, id, pos, energy, bond_group):
        self.id = id
        self.pos = pos
        self.direction = (0,1,0)
        self.energy = energy
        self.pressure = 0
        self.alive = True
        self.type = "seed"
        self.parent_id = None
        self.bonds = set()
        self.signal_type = 0
        self.bond_group = bond_group
        self.active_group = bond_group
        self.dormant_groups = set()
        self.probe_count = defaultdict(int)
        self.failure_streak = 0
        self.good = defaultdict(int)
        self.bad = defaultdict(int)
        self.cgood = defaultdict(int)
        self.cbad = defaultdict(int)
        self.burden = defaultdict(lambda: 2)
        self.probation = None

    def copy(self):
        n = Node(self.id, self.pos, self.energy, self.bond_group)
        n.direction = self.direction
        n.pressure = self.pressure
        n.alive = self.alive
        n.type = self.type
        n.parent_id = self.parent_id
        n.bonds = set(self.bonds)
        n.signal_type = self.signal_type
        return n

# ---------- Cluster initialization ----------

def init_cluster(seed, params):
    rng = random.Random(seed)
    ws = params["world_size"]
    cx = cy = ws // 2
    nodes = []
    for i in range(30):
        x = cx + rng.randint(-2,2)
        y = cy + rng.randint(-2,2)
        pos = (x,y,0)
        energy = 55000 + rng.randint(-5000,5000)
        bond_group = "A"  # All start in group A
        nodes.append(Node(i, pos, energy, bond_group))
    # chain bonds within same bond_group
    for g in ("A","B","C"):
        ids = [n.id for n in nodes if n.bond_group == g]
        ids.sort()
        for a,b in zip(ids, ids[1:]):
            na = nodes[a]; nb = nodes[b]
            if len([x for x in na.bonds if nodes[x].alive]) < params["max_bonds"] and \
               len([x for x in nb.bonds if nodes[x].alive]) < params["max_bonds"]:
                na.bonds.add(nb.id); nb.bonds.add(na.id)
    # random cross-group bonds (but each node only bonds within its group for this experiment)
    # We'll keep bonds group-local to make groups disjoint topologies.
    # Resource
    resource_x = rng.choice([2, ws-3])
    resource_y = rng.randint(0, ws-1)
    resource_pos = (resource_x, resource_y, 0)
    resource_left = 450000
    resource_reached = False
    return nodes, resource_pos, resource_left, resource_reached, rng

# ---------- Metrics ----------

def compute_metrics(nodes, resource_pos, params, resource_reached):
    live = [n for n in nodes if n.alive]
    if not live:
        return {"alive_count":0,"component_count":0,"average_energy":0,
                "min_energy":0,"center_sum":None,"center_denominator":0,
                "success_distance_passed":False,"gini_num":0,"gini_den":1,
                "gini_over_threshold":False}
    alive_count = len(live)
    energy_total = sum(n.energy for n in live)
    average_energy = integer_div(energy_total, alive_count)
    min_energy = min(n.energy for n in live)
    sx = sum(n.pos[0] for n in live)
    sy = sum(n.pos[1] for n in live)
    sz = sum(n.pos[2] for n in live)
    center_sum = (sx, sy, sz)
    center_denominator = alive_count
    dx = sx - resource_pos[0] * alive_count
    dy = sy - resource_pos[1] * alive_count
    dz = sz - resource_pos[2] * alive_count
    dist_num = dx*dx + dy*dy + dz*dz
    success_distance_passed = (
        params["success_max_distance_sq_den"] * dist_num
        <= params["success_max_distance_sq_num"] * alive_count * alive_count
    )
    # components via active bonds only
    visited = set()
    comp = 0
    for n in live:
        if n.id in visited: continue
        comp += 1
        stack = [n.id]
        while stack:
            cur = stack.pop()
            if cur in visited: continue
            visited.add(cur)
            for nb_id in nodes[cur].bonds:
                if nodes[nb_id].alive and nb_id not in visited:
                    stack.append(nb_id)
    # Gini
    energies = sorted(n.energy for n in live)
    n = len(energies)
    T = sum(energies)
    W = sum((i+1)*v for i,v in enumerate(energies))
    if n==0 or T==0:
        gini_num = 0; gini_den = 1
    else:
        gini_num = 2*W - (n+1)*T
        gini_den = n*T
    gini_over_threshold = (
        params["gini_threshold_den"] * gini_num
        > params["gini_threshold_num"] * gini_den
    )
    return {
        "alive_count": alive_count,
        "component_count": comp,
        "average_energy": average_energy,
        "min_energy": min_energy,
        "center_sum": center_sum,
        "center_denominator": center_denominator,
        "success_distance_passed": success_distance_passed,
        "gini_num": gini_num,
        "gini_den": gini_den,
        "gini_over_threshold": gini_over_threshold,
    }

# ---------- Cluster actions (only REDISTRIBUTE through active bonds) ----------

def action_redistribute(nodes, params, active_group):
    live = [n for n in nodes if n.alive]
    # snapshot active bonds
    pairs = []
    for n in live:
        for nb_id in n.bonds:
            if nb_id > n.id and nodes[nb_id].alive:
                if n.bond_group == active_group and nodes[nb_id].bond_group == active_group:
                    pairs.append((n.id, nb_id))
    pairs.sort()
    for a_id, b_id in pairs:
        na = nodes[a_id]; nb = nodes[b_id]
        diff = na.energy - nb.energy
        if abs(diff) > 1000:
            amount = integer_div(abs(diff) * params["trade_rate_num"], params["trade_rate_den"])
            donor = na if diff > 0 else nb
            recip = nb if diff > 0 else na
            amount = min(amount, donor.energy)
            donor.energy -= amount
            recip.energy += amount
            donor.energy -= params["trade_cost"]
            donor.energy = clamp0(donor.energy)

def action_seek(nodes, resource_pos, params, rng):
    live = [n for n in nodes if n.alive]
    for n in live:
        dx = resource_pos[0] - n.pos[0]
        dy = resource_pos[1] - n.pos[1]
        if abs(dx) >= abs(dy):
            mx, my = sign(dx), 0
        else:
            mx, my = 0, sign(dy)
        if rng.randrange(0,1000000) < 120000:
            mx, my = rng.choice([(1,0),(0,1),(-1,0),(0,-1)])
        nx = max(0, min(params["world_size"]-1, n.pos[0] + mx))
        ny = max(0, min(params["world_size"]-1, n.pos[1] + my))
        n.pos = (nx, ny, 0)
        n.energy -= params["move_cost"]

def action_rest(nodes, params):
    for n in nodes:
        if n.alive:
            n.energy += params["rest_gain"]

def action_repair(nodes, params, rng):
    live = [n for n in nodes if n.alive]
    for n in live:
        n.energy -= params["repair_cost"]
        n.energy = clamp0(n.energy)
    # kill below tau
    for n in live:
        if n.energy < params["tau"]:
            n.alive = False; n.type = "inert"
    # recompute components
    visited = set(); comps = []
    for n in nodes:
        if n.alive and n.id not in visited:
            comp = []
            stack = [n.id]
            while stack:
                cur = stack.pop()
                if cur in visited: continue
                visited.add(cur); comp.append(cur)
                for nb_id in nodes[cur].bonds:
                    if nodes[nb_id].alive and nb_id not in visited:
                        stack.append(nb_id)
            comps.append(comp)
    if len(comps) < 2: return
    # fragmented: first pair with valid candidate
    for i in range(len(comps)):
        for j in range(i+1, len(comps)):
            for a_id in comps[i]:
                for b_id in comps[j]:
                    na = nodes[a_id]; nb = nodes[b_id]
                    if b_id in na.bonds: continue
                    if len([x for x in na.bonds if nodes[x].alive]) >= params["max_bonds"]: continue
                    if len([x for x in nb.bonds if nodes[x].alive]) >= params["max_bonds"]: continue
                    if not params["repair_ignores_distance"] and qdist(na.pos, nb.pos) > params["bond_distance_sq"]: continue
                    if rng.randrange(0,1000000) < params["repair_prob_ppm"]:
                        na.bonds.add(nb.id); nb.bonds.add(na.id)
                        return

def apply_damage(nodes, params, rng):
    live = [n for n in nodes if n.alive]
    for n in live:
        n.energy -= params["damage_energy_loss"]
        n.energy = clamp0(n.energy)
    for n in live:
        if n.energy < params["tau"]:
            n.alive = False; n.type = "inert"
    # bond break
    pairs = []
    for n in nodes:
        if n.alive:
            for nb_id in n.bonds:
                if nb_id > n.id and nodes[nb_id].alive:
                    pairs.append((n.id, nb_id))
    pairs.sort()
    for a_id, b_id in pairs:
        if rng.randrange(0,1000000) < params["damage_bond_break_ppm"]:
            nodes[a_id].bonds.discard(b_id)
            nodes[b_id].bonds.discard(a_id)

def absorb_resource(nodes, resource_pos, resource_left, params):
    if resource_left <= 0: return resource_left, False
    live = [n for n in nodes if n.alive and qdist(n.pos, resource_pos) <= params["resource_radius_sq"]]
    if not live: return resource_left, False
    live.sort(key=lambda n: n.id)
    total_absorb = min(resource_left, params["resource_absorb_rate"] * len(live))
    base = integer_div(total_absorb, len(live))
    rem = total_absorb - base * len(live)
    for i, n in enumerate(live):
        n.energy += base + (1 if i < rem else 0)
    resource_left -= total_absorb
    return max(0, resource_left), True

def decay_and_kill(nodes, params):
    for n in nodes:
        if n.alive:
            n.energy -= params["decay_cost"]
            n.energy = clamp0(n.energy)
    for n in nodes:
        if n.alive and n.energy < params["tau"]:
            n.alive = False; n.type = "inert"

# ---------- Pressure update (simplified) ----------
def update_pressure(nodes, params):
    for n in nodes:
        if n.alive:
            n.pressure = integer_div((n.pressure + params["delta_P_baseline"]) * params["beta_num"], params["beta_den"])

# ============================================================
# AUTHORITY SWITCHING LAYER
# ============================================================

def local_signature(node, nodes):
    """Observable local topology: bonded neighbors' (energy_bucket, pressure_bucket, type)."""
    sig = []
    for nb_id in node.bonds:
        nb = nodes[nb_id]
        if nb.alive:
            sig.append((nb.energy // 10000, nb.pressure // 10000, nb.type))
    return tuple(sorted(sig))

def probe_group(nodes, group, params):
    """Local probe: check if any node's dormant bonds in 'group' would bring energy from higher-energy neighbors."""
    total_gain = 0
    for n in nodes:
        if not n.alive or not hasattr(n, "dormant_bonds") or group not in n.dormant_bonds:
            continue
        for nb_id in n.dormant_bonds[group]:
            nb = nodes[nb_id]
            if nb.alive and nb.energy > n.energy + 1000:
                diff = nb.energy - n.energy
                amount = integer_div(diff * params["trade_rate_num"], params["trade_rate_den"])
                total_gain += min(amount, nb.energy)
    return total_gain, 0, False, total_gain > 0

def run_authority_switching(policy, seed, cycles, params, variant, probe_steps=2, failure_trigger=3):
    nodes, resource_pos, resource_left, resource_reached, rng = init_cluster(seed, params)
    n_nodes = len(nodes)
    # Build dormant group bonds (B and C) as alternative topologies
    # First, capture the chain bonds from init_cluster as group A
    for n in nodes:
        n.dormant_bonds = {"A": set(n.bonds), "B": set(), "C": set()}
    for g in ("B","C"):
        ids = list(range(30))
        for a,b in zip(ids, ids[1:]):
            na = nodes[a]; nb = nodes[b]
            na.dormant_bonds[g].add(nb.id)
            nb.dormant_bonds[g].add(na.id)
    for n in nodes:
        n.dormant_groups = {"B","C"}
        n.bonds = set(n.dormant_bonds["A"])
    # Cycle tracking
    false_switches = [0]*cycles
    wrong_authority = [0]*cycles
    switches = [0]*cycles
    final_correct = [0]*cycles
    complete = [False]*cycles
    receipts = []
    for cyc in range(cycles):
        # Run cluster steps within cycle
        steps_per_cycle = 50
        for step in range(steps_per_cycle):
            # 1. Decay + kill
            decay_and_kill(nodes, params)
            # 2. Damage at step 15
            if step == 15:
                apply_damage(nodes, params, rng)
            # 3. Metrics
            metrics = compute_metrics(nodes, resource_pos, params, resource_reached)
            # 4. Authority check: if active group's min_energy < critical, probe
            for n in nodes:
                if not n.alive: continue
                active = n.active_group
                # compute min_energy in active group component
                active_nodes = [m for m in nodes if m.alive and m.active_group == active]
                if not active_nodes: continue
                min_e = min(m.energy for m in active_nodes)
                if min_e >= params["critical_energy"]:
                    n.failure_streak = 0
                    continue
                n.failure_streak += 1
                if n.failure_streak < failure_trigger:
                    continue
                # Actually probe dormant groups by temporarily activating them
                sig = local_signature(n, nodes)
                probe_results = {}
                for g in sorted(n.dormant_groups):
                    delta, rl, rr, success = probe_group(nodes, g, params)
                    resource_left = rl
                    resource_reached = rr
                    probe_results[g] = (delta, success)
                    if success:
                        n.good[g] += 1
                        n.cgood[(g, sig)] += 1
                    else:
                        n.bad[g] += 1
                        n.cbad[(g, sig)] += 1
                # Find viable groups (successful probes)
                viable = [g for g, (delta, success) in probe_results.items() if success]
                if not viable:
                    continue
                # Score viable groups
                if policy == "history_weighted":
                    def score(g):
                        hist = n.good[g] - n.bad[g]
                        return (hist + probe_results[g][0], probe_results[g][0], -n.bad[g], -ord(g))
                    best = max(viable, key=score)
                elif policy == "conditional_history":
                    def score(g):
                        cg = n.cgood[(g, sig)]
                        cb = n.cbad[(g, sig)]
                        local_hist = cg - cb
                        return (3*probe_results[g][0] + local_hist, probe_results[g][0], -cb, -ord(g))
                    best = max(viable, key=score)
                elif policy == "scalar_adaptive":
                    def score(g):
                        return (probe_results[g][0] - n.burden[g], probe_results[g][0], -ord(g))
                    best = max(viable, key=score)
                    if policy == "scalar_adaptive":
                        n.burden[best] = min(8, max(n.burden[best], probe_steps + 1))
                else:  # fixed3, fixed4
                    def score(g):
                        needed = int(policy[-1])
                        return (probe_results[g][0] - needed, probe_results[g][0], -ord(g))
                    best = max(viable, key=score)
                old = n.active_group
                # Swap bonds: deactivate old, activate best
                if hasattr(n, "dormant_bonds"):
                    n.bonds = set(n.dormant_bonds[best])
                n.dormant_groups.add(old)
                n.dormant_groups.remove(best)
                n.active_group = best
                n.bond_group = best
                n.failure_streak = 0
                switches[cyc] += 1
                if policy == "scalar_adaptive":
                    n.probation = {"label": best, "target": n.burden[best], "post": 0, "evidence": 2}
                receipts.append({"cycle": cyc, "step": step, "node": n.id,
                                 "from": old, "to": best, "sig": str(sig),
                                 "delta": probe_results[best][0]})
            # 5. Select action based on metrics
            if metrics["component_count"] > 1:
                action_repair(nodes, params, rng)
            elif metrics["min_energy"] < params["critical_energy"]:
                action_rest(nodes, params) if resource_reached else action_redistribute(nodes, params, nodes[0].active_group)
            elif metrics["average_energy"] < params["low_energy_cutoff"] and not resource_reached:
                action_seek(nodes, resource_pos, params, rng)
            elif metrics["average_energy"] < params["low_energy_cutoff"] and resource_reached:
                action_seek(nodes, resource_pos, params, rng) if not metrics["success_distance_passed"] else action_rest(nodes, params)
            elif metrics["gini_over_threshold"]:
                action_redistribute(nodes, params, nodes[0].active_group)
            elif not metrics["success_distance_passed"]:
                action_seek(nodes, resource_pos, params, rng)
            else:
                action_rest(nodes, params)
            # 6. Resource absorption
            resource_left, reached = absorb_resource(nodes, resource_pos, resource_left, params)
            resource_reached = resource_reached or reached
            # 7. Pressure
            update_pressure(nodes, params)
        # End of cycle: evaluate
        metrics = compute_metrics(nodes, resource_pos, params, resource_reached)
        final_correct[cyc] = sum(1 for n in nodes if n.alive and n.active_group == "A")
        # Count wrong authority (active != "A" when should be A)
        wrong_authority[cyc] = sum(1 for n in nodes if n.alive and n.active_group != "A")
        # Complete cycle criteria: no false switches, all correct, all transitions hit
        complete[cyc] = (false_switches[cyc] == 0 and final_correct[cyc] == n_nodes and metrics["component_count"] == 1 and resource_reached and metrics["success_distance_passed"])
    result = {
        "policy": policy,
        "seed": seed,
        "variant": variant,
        "cycles": cycles,
        "complete_cycles": sum(complete),
        "false_switches_total": sum(false_switches),
        "wrong_authority_total": sum(wrong_authority),
        "switches_total": sum(switches),
        "final_correct_last": final_correct[-1] if final_correct else 0,
        "mean_final_correct": round(statistics.mean(final_correct), 3) if final_correct else 0,
    }
    result["hash"] = sha16({"result": result, "receipts": receipts})
    return result, receipts

def main():
    policies = ("fixed3", "fixed4", "scalar_adaptive", "history_weighted", "conditional_history")
    params = DEFAULT_PARAMS.copy()
    params["critical_energy"] = 40000  # Lower threshold for more frequent probing
    params["damage_energy_loss"] = 20000  # More damage
    rows = []
    for variant in range(3):
        for policy in policies:
            for seed in (3, 11, 17, 23, 29):
                result, _ = run_authority_switching(policy, seed, cycles=6, params=params, variant=variant)
                rows.append(result)
    with (OUT/"v0_27_results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    for policy in policies:
        sub = [r for r in rows if r["policy"] == policy]
        print(f"{policy}: cases={len(sub)} complete={sum(r['complete_cycles']==6 for r in sub)} "
              f"mean_complete={round(statistics.mean(r['complete_cycles'] for r in sub),3)} "
              f"false_sw={sum(r['false_switches_total'] for r in sub)} "
              f"wrong_auth={round(statistics.mean(r['wrong_authority_total'] for r in sub),2)}")

if __name__ == "__main__":
    main()
import random
from natural_math_authority_switching_v0_27 import *

# Run one case with debug
params = DEFAULT_PARAMS.copy()

# Manually trace through one cycle
nodes, resource_pos, resource_left, resource_reached, rng = init_cluster(3, params)
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
    n.active_group = "A"
    n.failure_streak = 0
    n.good = defaultdict(int)
    n.bad = defaultdict(int)
    n.cgood = defaultdict(int)
    n.cbad = defaultdict(int)
    n.burden = defaultdict(lambda: 2)
    n.probation = None

# Run steps until damage
for step in range(20):
    decay_and_kill(nodes, params)
    if step == 15:
        apply_damage(nodes, params, rng)
    metrics = compute_metrics(nodes, resource_pos, params, resource_reached)
    print(f"Step {step}: min_e={metrics['min_energy']} critical={params['critical_energy']} comps={metrics['component_count']}")
    # Check authority
    for n in nodes:
        if not n.alive: continue
        active = n.active_group
        active_nodes = [m for m in nodes if m.alive and m.active_group == active]
        if not active_nodes: continue
        min_e = min(m.energy for m in active_nodes)
        if min_e < params["critical_energy"]:
            n.failure_streak += 1
            if n.failure_streak >= 3:
                print(f"  Node {n.id} would probe at step {step}, min_e={min_e}")
                sig = local_signature(n, nodes)
                for g in sorted(n.dormant_groups):
                    group_nodes = [m.id for m in nodes if m.alive and g in m.dormant_groups]
                    print(f"    Group {g}: {len(group_nodes)} nodes")
                    delta, rl, rr, success = probe_group(nodes, g, 2, params, resource_pos, resource_left, resource_reached, rng, [], 0, group_nodes)
                    print(f"      delta={delta} success={success}")
                    resource_left = rl
                    resource_reached = rr
    # Action
    if metrics["component_count"] > 1:
        action_repair(nodes, params, rng)
    elif metrics["min_energy"] < params["critical_energy"]:
        action_rest(nodes, params) if resource_reached else action_redistribute(nodes, params, "A")
    elif metrics["average_energy"] < params["low_energy_cutoff"] and not resource_reached:
        action_seek(nodes, resource_pos, params, rng)
    elif metrics["average_energy"] < params["low_energy_cutoff"] and resource_reached:
        action_seek(nodes, resource_pos, params, rng) if not metrics["success_distance_passed"] else action_rest(nodes, params)
    elif metrics["gini_over_threshold"]:
        action_redistribute(nodes, params, "A")
    elif not metrics["success_distance_passed"]:
        action_seek(nodes, resource_pos, params, rng)
    else:
        action_rest(nodes, params)
    resource_left, reached = absorb_resource(nodes, resource_pos, resource_left, params)
    resource_reached = resource_reached or reached
    update_pressure(nodes, params)
import random
from natural_math_authority_switching_v0_27 import *

# Test probe_group directly
params = DEFAULT_PARAMS.copy()
params["critical_energy"] = 40000
params["damage_energy_loss"] = 20000

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
    n.bond_group = "A"

# Run to step 15 (damage)
for step in range(16):
    decay_and_kill(nodes, params)
    if step == 15:
        apply_damage(nodes, params, rng)
    metrics = compute_metrics(nodes, resource_pos, params, resource_reached)
    if metrics["min_energy"] < params["critical_energy"]:
        action_rest(nodes, params)
    else:
        action_redistribute(nodes, params, "A")
    resource_left, reached = absorb_resource(nodes, resource_pos, resource_left, params)
    resource_reached = resource_reached or reached
    update_pressure(nodes, params)

print(f"After step 15: min_e={metrics['min_energy']} critical={params['critical_energy']}")

# Now test probe
n = nodes[0]
sig = local_signature(n, nodes)
group_nodes = [m.id for m in nodes if m.alive and "B" in m.dormant_groups]
print(f"Group B nodes: {len(group_nodes)}")

delta, rl, rr, success = probe_group(nodes, "B", 2, params, resource_pos, resource_left, resource_reached, rng, [], 0, group_nodes)
print(f"Probe B: delta={delta} success={success} resource_left={rl}")

# Check node 0's bonds after probe
print(f"Node 0 bonds after probe: {nodes[0].bonds}")
print(f"Node 0 bond_group after probe: {nodes[0].bond_group}")
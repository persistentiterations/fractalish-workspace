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

# Check energy differences in group B bonds
print("Group B bond energy diffs:")
for a in range(29):
    b = a + 1
    na = nodes[a]; nb = nodes[b]
    if b in na.dormant_bonds["B"]:
        diff = abs(na.energy - nb.energy)
        if diff > 1000:
            print(f"  {a}-{b}: {na.energy} vs {nb.energy} diff={diff} -> would transfer {int(diff * params['trade_rate_num'] / params['trade_rate_den'])}")

# Now test probe with actual bond_group switching
print("\nTesting probe with manual bond swap:")
# Save original bonds
orig_bonds = {n.id: set(n.bonds) for n in nodes}
orig_groups = {n.id: n.bond_group for n in nodes}

# Switch all to group B
for n in nodes:
    n.bonds = set(n.dormant_bonds["B"])
    n.bond_group = "B"

# Run REDISTRIBUTE
before = {n.id: n.energy for n in nodes}
action_redistribute(nodes, params, "B")
after = {n.id: n.energy for n in nodes}

total_delta = sum(after[i] - before[i] for i in before)
print(f"Total delta: {total_delta}")

# Restore
for n in nodes:
    n.bonds = orig_bonds[n.id]
    n.bond_group = orig_groups[n.id]
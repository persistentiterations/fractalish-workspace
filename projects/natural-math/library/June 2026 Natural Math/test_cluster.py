import random
import sys
sys.path.insert(0, r"C:\June 2026 Natural Math")
from natural_math_authority_switching_v0_27 import *

params = DEFAULT_PARAMS.copy()
nodes, resource_pos, resource_left, resource_reached, rng = init_cluster(3, params)

# Build dormant bonds
for g in ("B","C"):
    ids = list(range(30))
    for a,b in zip(ids, ids[1:]):
        na = nodes[a]; nb = nodes[b]
        if not hasattr(na, "dormant_bonds"):
            na.dormant_bonds = {"A": set(), "B": set(), "C": set()}
        if not hasattr(nb, "dormant_bonds"):
            nb.dormant_bonds = {"A": set(), "B": set(), "C": set()}
        na.dormant_bonds[g].add(nb.id)
        nb.dormant_bonds[g].add(na.id)
for n in nodes:
    n.dormant_groups = {"B","C"}
    if hasattr(n, "dormant_bonds"):
        n.bonds = set(n.dormant_bonds["A"])

for step in range(10):
    decay_and_kill(nodes, params)
    action_redistribute(nodes, params, 'A')
    action_rest(nodes, params)
    resource_left, reached = absorb_resource(nodes, resource_pos, resource_left, params)
    resource_reached = resource_reached or reached
    update_pressure(nodes, params)
    metrics = compute_metrics(nodes, resource_pos, params, resource_reached)
    print(f'step {step}: alive={metrics["alive_count"]} avg_e={metrics["average_energy"]} comps={metrics["component_count"]} resource_left={resource_left} reached={resource_reached}')

print("Done")
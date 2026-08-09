import random
from natural_math_authority_switching_v0_27 import init_cluster, DEFAULT_PARAMS, compute_metrics

params = DEFAULT_PARAMS.copy()
nodes, resource_pos, resource_left, resource_reached, rng = init_cluster(3, params)
print('After init_cluster:')
for n in nodes[:5]:
    print(f'  node {n.id}: bonds={n.bonds}')
# Now capture dormant bonds
for n in nodes:
    n.dormant_bonds = {'A': set(n.bonds), 'B': set(), 'C': set()}
for g in ('B','C'):
    ids = list(range(30))
    for a,b in zip(ids, ids[1:]):
        na = nodes[a]; nb = nodes[b]
        na.dormant_bonds[g].add(nb.id)
        nb.dormant_bonds[g].add(na.id)
for n in nodes:
    n.dormant_groups = {'B','C'}
    n.bonds = set(n.dormant_bonds['A'])
print('After setting active bonds:')
for n in nodes[:5]:
    print(f'  node {n.id}: bonds={n.bonds}')
metrics = compute_metrics(nodes, resource_pos, params, resource_reached)
print(f'Metrics: components={metrics["component_count"]} alive={metrics["alive_count"]}')
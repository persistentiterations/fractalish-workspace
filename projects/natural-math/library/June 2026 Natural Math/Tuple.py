import random
import math
from typing import Tuple, Optional, List

class Node:
    def __init__(self, id: int, pos: Tuple[int, int, int], dir: Tuple[int, int, int], energy: float, pressure: float, parent_id: Optional[int], node_type: str, alive: bool):
        self.id = id
        self.pos = pos
        self.dir = dir
        self.energy = energy
        self.pressure = pressure
        self.parent_id = parent_id
        self.type = node_type
        self.alive = alive
        self.bonds: List[int] = []

class Params:
    def __init__(self):
        self.tau = 5.0
        self.iota = 1.0
        self.r = 25.0
        self.eps_extend = 0.5
        self.eps_sense = 0.01
        self.E0 = 1600.0
        self.eta_sq = 0.01
        self.gamma_fallback = 0.0  # CHANGED: no random jitter
        self.eps_tol = 1e-9
        self.r_sq = self.r ** 2
        self.iota_sq = self.iota ** 2
        self.deficit_strength = 15.0
        self.max_bonds = 3

def Q(p1, p2):
    return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2

def norm(v):
    return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)

def normalize(v, eps_tol=1e-9):
    n = norm(v)
    if n < eps_tol:
        return (0.0, 0.0, 0.0)
    return (v[0]/n, v[1]/n, v[2]/n)

def COMPUTE_GRADIENT(p, A_t_snapshot, params):
    g = [0.0, 0.0, 0.0]
    weight_sum = 0.0
    for q in A_t_snapshot:
        if q.id == p.id: continue
        q_dist = Q(p.pos, q.pos)
        if q_dist > params.r_sq + params.eps_tol or q_dist < params.eps_tol: continue
        w = 1.0 / q_dist
        weight_sum += w
        energy_diff = q.energy - p.energy
        deficit_p = max(0.0, (params.E0 - p.energy) / params.E0)
        deficit_q = max(0.0, (params.E0 - q.energy) / params.E0)
        deficit_factor = params.deficit_strength * deficit_p * deficit_q
        effective_diff = energy_diff - deficit_factor
        dx = q.pos[0] - p.pos[0]
        dy = q.pos[1] - p.pos[1]
        dz = q.pos[2] - p.pos[2]
        g[0] += w * effective_diff * dx
        g[1] += w * effective_diff * dy
        g[2] += w * effective_diff * dz
    if weight_sum < params.eps_tol:
        if norm(p.dir) > params.eps_tol:
            return normalize(p.dir)
        return (0.0, 1.0, 0.0)
    g = [g[0]/weight_sum, g[1]/weight_sum, g[2]/weight_sum]
    g_norm_sq = g[0]**2 + g[1]**2 + g[2]**2
    if g_norm_sq < params.eps_tol:
        return (0.0, 0.0, 0.0)
    return normalize((-g[0], -g[1], -g[2]))

def UPDATE_DIRECTION(g, params):
    g_norm_sq = g[0]**2 + g[1]**2 + g[2]**2
    if g_norm_sq < params.eps_tol:
        return (0, 1, 0)
    abs_vals = [abs(g[0]), abs(g[1]), abs(g[2])]
    max_abs = max(abs_vals)
    if abs(abs_vals[0] - max_abs) < params.eps_tol:
        idx = 0
    elif abs(abs_vals[1] - max_abs) < params.eps_tol:
        idx = 1
    else:
        idx = 2
    d = [0, 0, 0]
    d[idx] = 1 if g[idx] >= 0 else -1
    return tuple(d)

def COMPUTE_DECISION(p, A_t_snapshot, active_occupied, params):
    min_q = float('inf')
    for q in A_t_snapshot:
        if q.id == p.id: continue
        dist = Q(p.pos, q.pos)
        if dist < min_q:
            min_q = dist
    if p.energy < params.tau - params.eps_tol:
        return -1
    if min_q < params.iota_sq - params.eps_tol:
        return -1
    can_extend = (p.energy >= params.tau - params.eps_tol) and (min_q > params.iota_sq + params.eps_tol)
    if can_extend:
        g = COMPUTE_GRADIENT(p, A_t_snapshot, params)
        g_norm_sq = g[0]**2 + g[1]**2 + g[2]**2
        if g_norm_sq > params.eta_sq + params.eps_tol:
            return +1
        if random.random() < params.gamma_fallback:
            return +1
    if p.energy >= params.tau - params.eps_tol:
        return 0
    return -1

def run_simple_simulation(steps=12, hungry=True, num_nodes=5):
    params = Params()
    random.seed(42)
    e = params.E0 * 0.5 if hungry else params.E0
    nodes = []
    for i in range(num_nodes):
        nodes.append(Node(i, (i*2, 0, 0), (0,1,0), e, 0.0, None, 'seed', True))
    print(f"=== {num_nodes}-Node, gamma_fallback=0.0 (NO RANDOMNESS) ===")
    print("Initial positions:", [n.pos for n in nodes], "Energies:", [round(n.energy,1) for n in nodes])
    for t in range(steps):
        active = [n for n in nodes if n.alive]
        if not active: break
        A_t_snapshot = active[:]
        active_occupied = {n.pos for n in active}
        candidates = []
        for p in active:
            decision = COMPUTE_DECISION(p, A_t_snapshot, active_occupied, params)
            if decision == 1:
                g = COMPUTE_GRADIENT(p, A_t_snapshot, params)
                dir_new = UPDATE_DIRECTION(g, params)
                new_pos = (p.pos[0] + dir_new[0], p.pos[1] + dir_new[1], p.pos[2] + dir_new[2])
                candidates.append((p, new_pos, dir_new))
        for p, new_pos, d in candidates:
            if new_pos not in active_occupied:
                p.pos = new_pos
                p.dir = d
                p.energy = max(p.energy - params.eps_extend, 0.0)
                p.type = 'tip'
        # Bonding with max_bonds limit
        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                if nodes[i].alive and nodes[j].alive:
                    if len(nodes[i].bonds) >= params.max_bonds or len(nodes[j].bonds) >= params.max_bonds:
                        continue
                    dist = Q(nodes[i].pos, nodes[j].pos)
                    if 0 < dist <= 4:
                        avg = (nodes[i].energy + nodes[j].energy) / 2
                        nodes[i].energy = avg
                        nodes[j].energy = avg
                        nodes[j].pos = nodes[i].pos
                        nodes[i].bonds.append(nodes[j].id)
                        nodes[j].bonds.append(nodes[i].id)
                        print(f"  BOND {nodes[i].id}-{nodes[j].id} at {nodes[i].pos} (bonds: {len(nodes[i].bonds)}/{params.max_bonds})")
        print(f"Step {t+1}: {[n.pos for n in nodes if n.alive]} E: {[round(n.energy,1) for n in nodes if n.alive]}")
    return nodes

# Test with no randomness
for n in [2, 3, 4, 5, 6]:
    print()
    run_simple_simulation(12, hungry=True, num_nodes=n)
    print("-" * 60)

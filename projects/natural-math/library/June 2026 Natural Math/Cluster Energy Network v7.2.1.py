import random
import math
from collections import defaultdict, deque

# ============================================================
# Cluster Energy Network v7.2
# Simple AI-style adaptive agent test
# ============================================================

SEEDS = range(0, 50)

N_NODES = 30
WORLD_SIZE = 25
STEPS = 140

INITIAL_ENERGY = 55.0
ENERGY_NOISE = 5.0

LOW_ENERGY_CUTOFF = 38.0
CRITICAL_ENERGY = 30.0

DECAY_COST = 0.22
MOVE_COST = 0.30
REST_GAIN = 0.22

RESOURCE_AMOUNT = 450.0
RESOURCE_RADIUS = 2.0
RESOURCE_ABSORB_RATE = 14.0

TRADE_RATE = 0.18
TRADE_COST = 0.025

BOND_PROB = 0.08
MAX_BONDS_PER_NODE = 4

BREAK_BOND_IN_DAMAGE = True
DAMAGE_STEP = 35
DAMAGE_ENERGY_LOSS = 14.0
DAMAGE_BOND_BREAK_PROB = 0.18

REPAIR_COST = 0.35
REPAIR_PROB = 0.70

SUCCESS_FINAL_AVG_MIN = 38.0
SUCCESS_REQUIRE_ONE_CLUSTER = True
SUCCESS_REQUIRE_ALIVE_MIN = 24
SUCCESS_MAX_DISTANCE_TO_RESOURCE = 1.5

POLICIES = [
    "random_policy",
    "fixed_policy",
    "cluster_energy_policy",
]


def dist(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def gini(values):
    values = sorted(list(values))
    if not values:
        return 0.0

    total = sum(values)
    n = len(values)

    if total <= 0:
        return 0.0

    weighted = sum((i + 1) * v for i, v in enumerate(values))
    return (2 * weighted) / (n * total) - (n + 1) / n


def degree(i, bonds):
    return sum(1 for a, b in bonds if a == i or b == i)


def alive_nodes(state):
    return [i for i, ok in enumerate(state["alive"]) if ok]


def avg_energy(state):
    vals = [e for e, ok in zip(state["energy"], state["alive"]) if ok]
    return sum(vals) / len(vals) if vals else 0.0


def min_energy(state):
    vals = [e for e, ok in zip(state["energy"], state["alive"]) if ok]
    return min(vals) if vals else 0.0


def inequality(state):
    vals = [e for e, ok in zip(state["energy"], state["alive"]) if ok]
    return gini(vals)


def count_alive_bonds(state):
    return sum(1 for a, b in state["bonds"] if state["alive"][a] and state["alive"][b])


def center_of_mass(state):
    nodes = alive_nodes(state)
    if not nodes:
        return (0.0, 0.0)

    x = sum(state["pos"][i][0] for i in nodes) / len(nodes)
    y = sum(state["pos"][i][1] for i in nodes) / len(nodes)

    return (x, y)


def distance_to_resource(state):
    return dist(center_of_mass(state), state["resource_pos"])


def cluster_stats(state):
    nodes = alive_nodes(state)
    alive_set = set(nodes)

    if not nodes:
        return 0, 0, 0

    adj = defaultdict(list)

    for a, b in state["bonds"]:
        if a in alive_set and b in alive_set:
            adj[a].append(b)
            adj[b].append(a)

    seen = set()
    sizes = []

    for start in nodes:
        if start in seen:
            continue

        q = deque([start])
        seen.add(start)
        size = 0

        while q:
            cur = q.popleft()
            size += 1

            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb)
                    q.append(nb)

        sizes.append(size)

    return len(nodes), max(sizes), len(sizes)


def get_clusters(state):
    nodes = alive_nodes(state)
    alive_set = set(nodes)

    adj = defaultdict(list)

    for a, b in state["bonds"]:
        if a in alive_set and b in alive_set:
            adj[a].append(b)
            adj[b].append(a)

    seen = set()
    clusters = []

    for start in nodes:
        if start in seen:
            continue

        q = deque([start])
        seen.add(start)
        cluster = []

        while q:
            cur = q.popleft()
            cluster.append(cur)

            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb)
                    q.append(nb)

        clusters.append(cluster)

    return clusters


def build_initial_state(seed):
    rng = random.Random(seed)

    pos = []
    energy = []
    alive = []

    cx = WORLD_SIZE // 2
    cy = WORLD_SIZE // 2

    for _ in range(N_NODES):
        x = cx + rng.randint(-2, 2)
        y = cy + rng.randint(-2, 2)

        pos.append((x, y))
        energy.append(INITIAL_ENERGY + rng.uniform(-ENERGY_NOISE, ENERGY_NOISE))
        alive.append(True)

    bonds = set()

    for i in range(N_NODES - 1):
        bonds.add((i, i + 1))

    for i in range(N_NODES):
        for j in range(i + 2, N_NODES):
            if rng.random() < BOND_PROB:
                if degree(i, bonds) < MAX_BONDS_PER_NODE and degree(j, bonds) < MAX_BONDS_PER_NODE:
                    bonds.add((i, j))

    side = rng.choice(["left", "right", "top", "bottom"])

    if side == "left":
        resource_pos = (2, rng.randint(4, WORLD_SIZE - 5))
    elif side == "right":
        resource_pos = (WORLD_SIZE - 3, rng.randint(4, WORLD_SIZE - 5))
    elif side == "top":
        resource_pos = (rng.randint(4, WORLD_SIZE - 5), 2)
    else:
        resource_pos = (rng.randint(4, WORLD_SIZE - 5), WORLD_SIZE - 3)

    return {
        "seed": seed,
        "rng": rng,
        "step": 0,
        "pos": pos,
        "energy": energy,
        "alive": alive,
        "bonds": bonds,
        "resource_pos": resource_pos,
        "resource_left": RESOURCE_AMOUNT,
        "reached_resource": False,
        "damage_done": False,
        "actions": {
            "REST": 0,
            "SEEK": 0,
            "REPAIR": 0,
            "REDISTRIBUTE": 0,
        },
    }


def choose_action_random(state):
    return state["rng"].choice(["REST", "SEEK", "REPAIR", "REDISTRIBUTE"])


def choose_action_fixed(state):
    step = state["step"]

    if step % 4 == 0:
        return "REPAIR"
    elif step % 4 == 1:
        return "SEEK"
    elif step % 4 == 2:
        return "REDISTRIBUTE"
    else:
        return "REST"


def choose_action_cluster_energy(state):
    avg_e = avg_energy(state)
    min_e = min_energy(state)
    ineq = inequality(state)
    alive, largest, clusters = cluster_stats(state)
    d = distance_to_resource(state)

    if clusters > 1:
        return "REPAIR"

    if min_e < CRITICAL_ENERGY:
        if state["reached_resource"]:
            return "REST"
        return "REDISTRIBUTE"

    if avg_e < LOW_ENERGY_CUTOFF and not state["reached_resource"]:
        return "SEEK"

    if avg_e < LOW_ENERGY_CUTOFF and state["reached_resource"]:
        if d > SUCCESS_MAX_DISTANCE_TO_RESOURCE:
            return "SEEK"
        return "REST"

    # THE ONLY CHANGE: threshold raised from 0.045 to 0.07
    if ineq > 0.07:
        return "REDISTRIBUTE"

    if d > SUCCESS_MAX_DISTANCE_TO_RESOURCE:
        return "SEEK"

    return "REST"


def choose_action(state, policy):
    if policy == "random_policy":
        return choose_action_random(state)

    if policy == "fixed_policy":
        return choose_action_fixed(state)

    if policy == "cluster_energy_policy":
        return choose_action_cluster_energy(state)

    raise ValueError(f"Unknown policy: {policy}")


def apply_decay(state):
    for i in range(N_NODES):
        if state["alive"][i]:
            state["energy"][i] -= DECAY_COST

            if state["energy"][i] <= 0:
                state["energy"][i] = 0.0
                state["alive"][i] = False


def apply_rest(state):
    for i in alive_nodes(state):
        state["energy"][i] += REST_GAIN


def apply_seek(state):
    rng = state["rng"]
    rx, ry = state["resource_pos"]

    for i in alive_nodes(state):
        x, y = state["pos"][i]

        dx = 0
        dy = 0

        if rx > x:
            dx = 1
        elif rx < x:
            dx = -1

        if ry > y:
            dy = 1
        elif ry < y:
            dy = -1

        if rng.random() < 0.12:
            dx, dy = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])

        nx = clamp(x + dx, 0, WORLD_SIZE - 1)
        ny = clamp(y + dy, 0, WORLD_SIZE - 1)

        state["pos"][i] = (nx, ny)
        state["energy"][i] -= MOVE_COST


def apply_redistribute(state):
    for a, b in list(state["bonds"]):
        if not state["alive"][a] or not state["alive"][b]:
            continue

        ea = state["energy"][a]
        eb = state["energy"][b]
        diff = ea - eb

        if abs(diff) > 1.0:
            amount = abs(diff) * TRADE_RATE

            if diff > 0:
                amount = min(amount, max(0.0, state["energy"][a]))
                state["energy"][a] -= amount + TRADE_COST
                state["energy"][b] += amount
            else:
                amount = min(amount, max(0.0, state["energy"][b]))
                state["energy"][b] -= amount + TRADE_COST
                state["energy"][a] += amount


def apply_repair(state):
    rng = state["rng"]
    nodes = alive_nodes(state)

    if len(nodes) < 2:
        return

    for i in nodes:
        state["energy"][i] -= REPAIR_COST

    if rng.random() > REPAIR_PROB:
        return

    clusters = get_clusters(state)

    if len(clusters) > 1:
        c1 = rng.choice(clusters)
        c2 = rng.choice([c for c in clusters if c is not c1])

        a = rng.choice(c1)
        b = rng.choice(c2)

        state["bonds"].add(tuple(sorted((a, b))))
        return

    for _ in range(20):
        a = rng.choice(nodes)
        b = rng.choice(nodes)

        if a == b:
            continue

        edge = tuple(sorted((a, b)))

        if edge in state["bonds"]:
            continue

        if degree(a, state["bonds"]) < MAX_BONDS_PER_NODE and degree(b, state["bonds"]) < MAX_BONDS_PER_NODE:
            state["bonds"].add(edge)
            return


def absorb_resource_if_reached(state):
    if state["resource_left"] <= 0:
        return

    near = [
        i for i in alive_nodes(state)
        if dist(state["pos"][i], state["resource_pos"]) <= RESOURCE_RADIUS
    ]

    if not near:
        return

    state["reached_resource"] = True

    total_absorb = min(state["resource_left"], RESOURCE_ABSORB_RATE * len(near))
    per_node = total_absorb / len(near)

    for i in near:
        state["energy"][i] += per_node

    state["resource_left"] -= total_absorb


def apply_damage(state):
    if state["damage_done"]:
        return

    if state["step"] != DAMAGE_STEP:
        return

    rng = state["rng"]

    for i in alive_nodes(state):
        state["energy"][i] = max(0.0, state["energy"][i] - DAMAGE_ENERGY_LOSS)

        if state["energy"][i] <= 0:
            state["alive"][i] = False

    if BREAK_BOND_IN_DAMAGE:
        new_bonds = set()

        for edge in state["bonds"]:
            if rng.random() > DAMAGE_BOND_BREAK_PROB:
                new_bonds.add(edge)

        state["bonds"] = new_bonds

    state["damage_done"] = True


def cleanup_dead_nodes(state):
    for i in range(N_NODES):
        if state["alive"][i] and state["energy"][i] <= 0:
            state["energy"][i] = 0.0
            state["alive"][i] = False


def run_step(state, policy):
    action = choose_action(state, policy)
    state["actions"][action] += 1

    apply_decay(state)
    apply_damage(state)

    if action == "REST":
        apply_rest(state)
    elif action == "SEEK":
        apply_seek(state)
    elif action == "REPAIR":
        apply_repair(state)
    elif action == "REDISTRIBUTE":
        apply_redistribute(state)
    else:
        raise ValueError(action)

    absorb_resource_if_reached(state)
    cleanup_dead_nodes(state)

    state["step"] += 1


def judge_success(state):
    alive, largest, clusters = cluster_stats(state)
    final_avg = avg_energy(state)
    distance = distance_to_resource(state)

    if alive < SUCCESS_REQUIRE_ALIVE_MIN:
        return False, "too few alive"

    if SUCCESS_REQUIRE_ONE_CLUSTER and clusters != 1:
        return False, "not one cluster"

    if final_avg < SUCCESS_FINAL_AVG_MIN:
        return False, "avgE below cutoff"

    if not state["reached_resource"]:
        return False, "resource not reached"

    if distance > SUCCESS_MAX_DISTANCE_TO_RESOURCE:
        return False, "too far from resource"

    return True, "success"


def run_trial(seed, policy):
    state = build_initial_state(seed)

    for _ in range(STEPS):
        run_step(state, policy)

        if len(alive_nodes(state)) == 0:
            break

    alive, largest, clusters = cluster_stats(state)
    success, reason = judge_success(state)

    return {
        "seed": seed,
        "policy": policy,
        "success": success,
        "reason": reason,
        "alive": alive,
        "largest": largest,
        "clusters": clusters,
        "bonds": count_alive_bonds(state),
        "final_avgE": avg_energy(state),
        "final_minE": min_energy(state),
        "ineq": inequality(state),
        "distance": distance_to_resource(state),
        "resource_left": state["resource_left"],
        "reached_resource": state["reached_resource"],
        "REST": state["actions"]["REST"],
        "SEEK": state["actions"]["SEEK"],
        "REPAIR": state["actions"]["REPAIR"],
        "REDISTRIBUTE": state["actions"]["REDISTRIBUTE"],
    }


def summarize_results(results):
    n = len(results)

    return {
        "trials": n,
        "success_pct": 100.0 * sum(1 for r in results if r["success"]) / n,
        "reached_pct": 100.0 * sum(1 for r in results if r["reached_resource"]) / n,
        "avg_alive": sum(r["alive"] for r in results) / n,
        "avg_largest": sum(r["largest"] for r in results) / n,
        "avg_clusters": sum(r["clusters"] for r in results) / n,
        "avg_bonds": sum(r["bonds"] for r in results) / n,
        "avg_final_avgE": sum(r["final_avgE"] for r in results) / n,
        "avg_ineq": sum(r["ineq"] for r in results) / n,
        "avg_distance": sum(r["distance"] for r in results) / n,
    }


def print_policy_summary(all_results):
    print()
    print("=" * 110)
    print("Cluster Energy Network v7.2 - Simple AI-Style Agent Test")
    print("=" * 110)
    print()
    print(f"Seeds tested: {list(SEEDS)}")
    print(f"Steps per trial: {STEPS}")
    print(f"Damage step: {DAMAGE_STEP}")
    print(f"Success max distance to resource: {SUCCESS_MAX_DISTANCE_TO_RESOURCE}")
    print()

    print(
        "Policy                 Trials  Success%  Reached%  AvgAlive  Largest  "
        "Clusters  Bonds  FinalAvgE  Inequality  DistToRes"
    )
    print("-" * 110)

    for policy in POLICIES:
        s = summarize_results(all_results[policy])

        print(
            f"{policy:<22} "
            f"{s['trials']:6} "
            f"{s['success_pct']:8.1f} "
            f"{s['reached_pct']:8.1f} "
            f"{s['avg_alive']:8.2f} "
            f"{s['avg_largest']:8.2f} "
            f"{s['avg_clusters']:8.2f} "
            f"{s['avg_bonds']:6.2f} "
            f"{s['avg_final_avgE']:10.2f} "
            f"{s['avg_ineq']:10.3f} "
            f"{s['avg_distance']:9.2f}"
        )


def print_detailed_failures(all_results):
    print()
    print("=" * 110)
    print("Failure Reason Counts")
    print("=" * 110)

    for policy in POLICIES:
        counts = defaultdict(int)

        for r in all_results[policy]:
            if not r["success"]:
                counts[r["reason"]] += 1

        print()
        print(policy)
        print("-" * len(policy))

        if not counts:
            print("No failures")
        else:
            for reason, count in sorted(counts.items()):
                print(f"{reason:<25} {count}")


def print_best_and_worst(all_results):
    print()
    print("=" * 110)
    print("Best/Worst Seeds by Policy")
    print("=" * 110)

    for policy in POLICIES:
        rows = all_results[policy]

        best = sorted(
            rows,
            key=lambda r: (
                r["success"],
                r["reached_resource"],
                r["final_avgE"],
                r["alive"],
                -r["distance"],
            ),
            reverse=True,
        )[:5]

        worst = sorted(
            rows,
            key=lambda r: (
                r["success"],
                r["reached_resource"],
                r["final_avgE"],
                r["alive"],
                -r["distance"],
            ),
        )[:5]

        print()
        print(policy)
        print("-" * len(policy))

        print("Best seeds:")
        for r in best:
            print(
                f"  seed={r['seed']:3} success={str(r['success']):5} "
                f"avgE={r['final_avgE']:6.2f} alive={r['alive']:2} "
                f"clusters={r['clusters']:2} dist={r['distance']:5.2f} "
                f"reason={r['reason']} "
                f"REST={r['REST']} SEEK={r['SEEK']} REPAIR={r['REPAIR']} "
                f"REDIST={r['REDISTRIBUTE']}"
            )

        print("Worst seeds:")
        for r in worst:
            print(
                f"  seed={r['seed']:3} success={str(r['success']):5} "
                f"avgE={r['final_avgE']:6.2f} alive={r['alive']:2} "
                f"clusters={r['clusters']:2} dist={r['distance']:5.2f} "
                f"reason={r['reason']} "
                f"REST={r['REST']} SEEK={r['SEEK']} REPAIR={r['REPAIR']} "
                f"REDIST={r['REDISTRIBUTE']}"
            )


def main():
    all_results = {policy: [] for policy in POLICIES}

    for policy in POLICIES:
        for seed in SEEDS:
            result = run_trial(seed, policy)
            all_results[policy].append(result)

    print_policy_summary(all_results)
    print_detailed_failures(all_results)
    print_best_and_worst(all_results)

    print()
    print("=" * 110)
    print("Interpretation guide")
    print("=" * 110)
    print("This version tests survival + resource reaching + staying near resource.")
    print("If cluster_energy_policy beats both baselines, it is doing adaptive control.")


if __name__ == "__main__":
    main()
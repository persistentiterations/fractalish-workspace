"""
Head-to-head comparison: Silent vs Scream
Drain 10.0, 6 deadly patches near food, seed 42.
Sustainable colony with 20 starting seeds and lower costs.
"""

import random
import math

# ============================================================
# CONFIGURATION - TUNED FOR SUSTAINABLE COLONY
# ============================================================
START_ENERGY = 100.0
MAX_ENERGY = 250.0
cost_extend = 1.0              # cheaper movement
cost_sense = 0.2               # cheaper sensing
PASSIVE_ENERGY_DRAIN = 0.02    # slower metabolism
spawn_cost = 1.0               # cheaper reproduction
REPRODUCE_THRESHOLD = 120.0     # easier to reproduce
REPRODUCE_PROB = 0.06           # higher reproduction chance
MIN_ENERGY_FOR_BIFURCATION = 150.0

FOOD_COUNT = 100                # more food
FOOD_ENERGY_MIN = 15.0
FOOD_ENERGY_MAX = 25.0
FOOD_DRIFT_SPEED = 0.15
FOOD_SPAWN_BOUNDS = {"x": (-40, 40), "y": (-10, 30), "z": (0, 0)}

NUM_DEADLY = 6
DEADLY_ENERGY = 300.0
DEADLY_DRAIN = 10.0             # LETHAL - will actually kill
DEADLY_DRIFT_SPEED = 0.06       # drift into food zones
DEADLY_APPEARS_AT_STEP = 150    # give colony time to establish

ABSORB_RADIUS_SQ = 4.0
PROXIMITY_BONUS_SQ = 64.0
PROXIMITY_BONUS = 3.0           # stronger food attraction

BOUNDS = {"x_min": -50, "x_max": 50,
          "y_min": -20, "y_max": 40,
          "z_min": -20, "z_max": 20}

pressure_bifurcate = 8.0         # easier to bifurcate
pressure_baseline = 2.2
pressure_decay = 0.85
tau = 5.0
contact_inhibition_sq = 1.0
sense_radius_sq = 900.0
gradient_threshold_sq = 0.01
MAX_POPULATION = 150             # room to grow
STEPS = 400                      # longer simulation
SEED = 42

# 20 starting seeds spread out
START_POSITIONS = [
    (-25, 0, 0), (-22, 2, 0), (-28, -2, 0), (-20, 5, 0), (-30, -5, 0),
    (-24, 3, 0), (-26, -3, 0), (-23, -1, 0), (-27, 1, 0), (-21, 4, 0),
    (-29, -4, 0), (-25, 1, 0), (-22, -2, 0), (-28, 2, 0), (-20, -3, 0),
    (-30, 3, 0), (-24, -4, 0), (-26, 4, 0), (-23, 0, 0), (-27, -1, 0)
]

# ============================================================
# HELPERS
# ============================================================
def Q(a, b):
    dx = a[0]-b[0]; dy = a[1]-b[1]; dz = a[2]-b[2]
    return dx*dx + dy*dy + dz*dz

def norm_sq(v):
    return v[0]*v[0] + v[1]*v[1] + v[2]*v[2]

def in_bounds(pos):
    return (BOUNDS["x_min"] <= pos[0] <= BOUNDS["x_max"] and
            BOUNDS["y_min"] <= pos[1] <= BOUNDS["y_max"] and
            BOUNDS["z_min"] <= pos[2] <= BOUNDS["z_max"])

def find_perpendicular(d):
    if d[0] != 0: return (0, 1, 0)
    if d[1] != 0: return (1, 0, 0)
    return (1, 0, 0)

def project_to_axis(v):
    abs_vals = [abs(v[0]), abs(v[1]), abs(v[2])]
    idx = abs_vals.index(max(abs_vals))
    r = [0, 0, 0]
    r[idx] = 1 if v[idx] >= 0 else -1
    return tuple(r)

def bifurcation_children(parent_dir):
    perp = find_perpendicular(parent_dir)
    c1_raw = (parent_dir[0]+perp[0], parent_dir[1]+perp[1], parent_dir[2]+perp[2])
    c2_raw = (parent_dir[0]-perp[0], parent_dir[1]-perp[1], parent_dir[2]-perp[2])
    c1 = project_to_axis(c1_raw)
    c2 = project_to_axis(c2_raw)
    if c1 == (0,0,0): c1 = (1,0,0)
    if c2 == (0,0,0) or c2 == c1:
        c2 = (0,1,0) if c1 != (0,1,0) else (0,0,1)
    return c1, c2

# ============================================================
# CLASSES
# ============================================================
class Node:
    def __init__(self, id, pos, dir, energy, pressure, alive, node_type, parent_id, team):
        self.id = id
        self.pos = pos
        self.dir = dir
        self.energy = energy
        self.pressure = pressure
        self.alive = alive
        self.type = node_type
        self.parent_id = parent_id
        self.team = team
        self.is_feeding = False
        self.generation = 0
        self.total_distance_traveled = 0.0

class Nutrient:
    def __init__(self, id, pos, energy, is_deadly, drain_per_step=0, drift_vec=(0,0,0)):
        self.id = id
        self.pos = pos
        self.energy = energy
        self.is_deadly = is_deadly
        self.drain_per_step = drain_per_step
        self.alive = True
        self.type = "deadly" if is_deadly else "food"
        self.deaths_caused = 0
        self.drift_vector = drift_vec
        self.total_distance_traveled = 0.0
        self.feeding_events = 0

    def interact(self, node, stats):
        if not self.alive or self.energy <= 0:
            return 0, 0, False
        if self.is_deadly:
            if Q(node.pos, self.pos) > ABSORB_RADIUS_SQ:
                return 0, 0, False
            damage = self.drain_per_step
            node.energy -= damage
            stats["deadly_contacts"] = stats.get("deadly_contacts", 0) + 1
            died = node.energy <= 0
            if died:
                self.deaths_caused += 1
            return 0, damage, died
        if Q(node.pos, self.pos) > ABSORB_RADIUS_SQ:
            return 0, 0, False
        absorb = min(self.energy, MAX_ENERGY - node.energy)
        node.energy += absorb
        self.energy -= absorb
        node.is_feeding = True
        self.feeding_events += 1
        if self.energy <= 0:
            self.alive = False
        return absorb, 0, False

    def move(self, bounds):
        if self.drift_vector == (0, 0, 0):
            return False
        new_x = self.pos[0] + self.drift_vector[0]
        new_y = self.pos[1] + self.drift_vector[1]
        new_z = self.pos[2] + self.drift_vector[2]
        bounced = False
        if new_x > bounds["x_max"] or new_x < bounds["x_min"]:
            self.drift_vector = (-self.drift_vector[0], self.drift_vector[1], self.drift_vector[2])
            new_x = self.pos[0] + self.drift_vector[0]
            bounced = True
        if new_y > bounds["y_max"] or new_y < bounds["y_min"]:
            self.drift_vector = (self.drift_vector[0], -self.drift_vector[1], self.drift_vector[2])
            new_y = self.pos[1] + self.drift_vector[1]
            bounced = True
        if new_z > bounds["z_max"] or new_z < bounds["z_min"]:
            self.drift_vector = (self.drift_vector[0], self.drift_vector[1], -self.drift_vector[2])
            new_z = self.pos[2] + self.drift_vector[2]
            bounced = True
        dx = new_x - self.pos[0]
        dy = new_y - self.pos[1]
        dz = new_z - self.pos[2]
        self.total_distance_traveled += math.sqrt(dx*dx + dy*dy + dz*dz)
        self.pos = (new_x, new_y, new_z)
        return bounced

# ============================================================
# SIMULATION FUNCTIONS
# ============================================================
def compute_gradient(node, active_nodes, nutrients, suffering_strength):
    g = (0.0, 0.0, 0.0)
    for other in active_nodes:
        if other.id == node.id: continue
        d2 = Q(node.pos, other.pos)
        if d2 == 0 or d2 > sense_radius_sq: continue
        w = 1.0 / d2
        energy_diff = (suffering_strength if (other.energy < tau*2 or not other.alive)
                       else other.energy - node.energy)
        g = (g[0] + w * energy_diff * (other.pos[0]-node.pos[0]),
             g[1] + w * energy_diff * (other.pos[1]-node.pos[1]),
             g[2] + w * energy_diff * (other.pos[2]-node.pos[2]))
    for nut in nutrients:
        if not nut.alive or nut.energy <= 0: continue
        d2 = Q(node.pos, nut.pos)
        if d2 == 0 or d2 > sense_radius_sq: continue
        w = 1.0 / d2
        energy_diff = nut.energy - node.energy
        if energy_diff < 0: energy_diff = nut.energy
        g = (g[0] + w * energy_diff * (nut.pos[0]-node.pos[0]),
             g[1] + w * energy_diff * (nut.pos[1]-node.pos[1]),
             g[2] + w * energy_diff * (nut.pos[2]-node.pos[2]))
    if norm_sq(g) == 0.0: g = node.dir
    return g

def compute_decision(node, active_nodes, nutrients, suffering_strength):
    min_d2 = float('inf')
    for other in active_nodes:
        if other.id == node.id: continue
        d2 = Q(node.pos, other.pos)
        if d2 < min_d2: min_d2 = d2
    if node.energy < tau: return -1
    if min_d2 < contact_inhibition_sq: return -1
    for nut in nutrients:
        if nut.alive and not nut.is_deadly and nut.energy > 0:
            if Q(node.pos, nut.pos) <= ABSORB_RADIUS_SQ and node.energy > START_ENERGY*0.5:
                return 0
    g = compute_gradient(node, active_nodes, nutrients, suffering_strength)
    if norm_sq(g) > gradient_threshold_sq and node.energy >= tau:
        return 1
    return 0

def update_direction_from_gradient(g):
    abs_vals = [abs(g[0]), abs(g[1]), abs(g[2])]
    idx = abs_vals.index(max(abs_vals))
    d = [0, 0, 0]
    d[idx] = 1 if g[idx] >= 0 else -1
    return tuple(d)

def spawn_food(nutrients, next_id):
    x = random.uniform(*FOOD_SPAWN_BOUNDS["x"])
    y = random.uniform(*FOOD_SPAWN_BOUNDS["y"])
    energy = random.uniform(FOOD_ENERGY_MIN, FOOD_ENERGY_MAX)
    dx = random.uniform(-FOOD_DRIFT_SPEED, FOOD_DRIFT_SPEED)
    dy = random.uniform(-FOOD_DRIFT_SPEED, FOOD_DRIFT_SPEED)
    food = Nutrient(next_id, (x, y, 0.0), energy, False, drift_vec=(dx, dy, 0.0))
    nutrients.append(food)
    return next_id + 1

def step(nodes, nutrients, next_id, stats, deadly_active, suffering_strength):
    active_nodes = [n for n in nodes if n.alive]
    if not active_nodes:
        return nodes, nutrients, next_id
    for nut in nutrients:
        if nut.alive and nut.type in ("food", "deadly"):
            nut.move(BOUNDS)
    for n in active_nodes:
        n.is_feeding = False
        n.energy -= PASSIVE_ENERGY_DRAIN
        if n.energy <= 0:
            n.alive = False
            n.type = "inert"
    active_nodes = [n for n in nodes if n.alive]
    if len(active_nodes) > MAX_POPULATION:
        active_nodes.sort(key=lambda n: n.energy)
        for i in range(len(active_nodes) - MAX_POPULATION):
            active_nodes[i].alive = False
            active_nodes[i].type = "inert"
            stats["population_culled"] = stats.get("population_culled", 0) + 1
    active_nodes = [n for n in nodes if n.alive]
    decisions = {}
    for n in active_nodes:
        decisions[n.id] = compute_decision(n, active_nodes, nutrients, suffering_strength)
    new_nodes = []
    for n in active_nodes[:]:
        for nut in nutrients:
            if not nut.alive: continue
            gained, damage, died = nut.interact(n, stats)
            if gained > 0:
                stats["safe_absorbed"] += gained
            if damage > 0:
                stats["deadly_damage"] += damage
                if died:
                    stats["deaths_at_deadly"] += 1
            if not nut.is_deadly and nut.alive and nut.energy > 0:
                if Q(n.pos, nut.pos) < PROXIMITY_BONUS_SQ:
                    n.energy = min(n.energy + PROXIMITY_BONUS, MAX_ENERGY)
        if not n.alive: continue
        if decisions[n.id] == -1:
            n.alive = False
            n.energy = 0.0
            n.type = "inert"
        elif decisions[n.id] == 0:
            n.energy -= cost_sense
            n.pressure = (n.pressure + pressure_baseline) * pressure_decay
        else:
            g = compute_gradient(n, active_nodes, nutrients, suffering_strength)
            d = update_direction_from_gradient(g)
            new_pos = (n.pos[0]+d[0], n.pos[1]+d[1], n.pos[2]+d[2])
            if not in_bounds(new_pos):
                stats["boundary_kills"] += 1
                n.alive = False
                n.type = "inert"
                continue
            if (n.pressure >= pressure_bifurcate and 
                n.energy > MIN_ENERGY_FOR_BIFURCATION and 
                n.energy > 2*cost_extend + spawn_cost):
                n.energy -= (cost_extend + spawn_cost)
                child_energy = max(n.energy / 3.0, START_ENERGY * 0.4)
                v1, v2 = bifurcation_children(n.dir)
                c1 = Node(next_id, (n.pos[0]+v1[0], n.pos[1]+v1[1], n.pos[2]+v1[2]),
                          v1, child_energy, n.pressure*pressure_decay, True, "tip", n.id, n.team)
                c1.generation = n.generation + 1; next_id += 1
                c2 = Node(next_id, (n.pos[0]+v2[0], n.pos[1]+v2[1], n.pos[2]+v2[2]),
                          v2, child_energy, n.pressure*pressure_decay, True, "tip", n.id, n.team)
                c2.generation = n.generation + 1; next_id += 1
                new_nodes.extend([c1, c2])
                n.alive = False; n.type = "branch"
                stats["bifurcations"] = stats.get("bifurcations", 0) + 1
            else:
                n.energy -= cost_extend
                n.pos = new_pos; n.dir = d
                n.total_distance_traveled += 1.0
                n.pressure = (n.pressure + pressure_baseline) * pressure_decay
                if n.energy > REPRODUCE_THRESHOLD and random.random() < REPRODUCE_PROB:
                    offsets = [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]
                    random.shuffle(offsets)
                    for dx, dy, dz in offsets:
                        test_pos = (n.pos[0]+dx, n.pos[1]+dy, n.pos[2]+dz)
                        if in_bounds(test_pos) and not any(other.pos == test_pos for other in nodes if other.alive):
                            child_energy = START_ENERGY * 0.5
                            n.energy -= child_energy + spawn_cost
                            new_seed = Node(next_id, test_pos, (0,1,0), child_energy, 0.0,
                                            True, "seed", None, n.team)
                            new_seed.generation = n.generation + 1; next_id += 1
                            new_nodes.append(new_seed)
                            stats["births"] = stats.get("births", 0) + 1
                            break
    nodes.extend(new_nodes)
    to_remove = [nut for nut in nutrients if nut.type == "food" and not nut.alive]
    for p in to_remove:
        nutrients.remove(p)
        next_id = spawn_food(nutrients, next_id)
    for n in nodes:
        if n.alive and n.energy < tau:
            n.alive = False; n.type = "inert"
    return nodes, nutrients, next_id

def initialize():
    nodes = []; next_id = 0
    for pos in START_POSITIONS:
        nodes.append(Node(next_id, pos, (1,0,0), START_ENERGY, 0.0, True, "seed", None, "red"))
        next_id += 1
    nutrients = []
    for _ in range(FOOD_COUNT):
        next_id = spawn_food(nutrients, next_id)
    return nodes, nutrients, next_id

def run_one_simulation(label, suffering_strength):
    random.seed(SEED)
    nodes, nutrients, next_id = initialize()
    deadly_active = False
    stats = {"boundary_kills": 0, "safe_absorbed": 0, "deadly_damage": 0,
             "deaths_at_deadly": 0, "population_culled": 0, "bifurcations": 0,
             "births": 0, "deadly_contacts": 0}

    print("")
    print("=" * 60)
    print("  " + label)
    print("  Suffering signal: " + str(suffering_strength))
    print("  Deadly patches: " + str(NUM_DEADLY) + ", Drain: " + str(DEADLY_DRAIN) + "/step")
    print("  Starting seeds: " + str(len(START_POSITIONS)))
    print("  Seed: " + str(SEED))
    print("=" * 60)
    print("  Step | Alive | AvgE  | Contacts | Deaths | Food")
    print("  " + "-" * 50)

    for step_num in range(STEPS):
        if not deadly_active and step_num >= DEADLY_APPEARS_AT_STEP:
            for _ in range(NUM_DEADLY):
                # Spawn deadly patches inside the food zone
                pos = (random.uniform(-30, 30), random.uniform(-5, 25), 0)
                drift_vec = (random.uniform(-DEADLY_DRIFT_SPEED, DEADLY_DRIFT_SPEED),
                             random.uniform(-DEADLY_DRIFT_SPEED, DEADLY_DRIFT_SPEED), 0)
                deadly = Nutrient(next_id, pos, DEADLY_ENERGY, True,
                                  drain_per_step=DEADLY_DRAIN, drift_vec=drift_vec)
                nutrients.append(deadly)
                next_id += 1
            deadly_active = True
            print("  >>> DEADLY PATCHES APPEAR (step " + str(step_num) + ")")

        nodes, nutrients, next_id = step(nodes, nutrients, next_id, stats, deadly_active, suffering_strength)
        alive = [n for n in nodes if n.alive]

        if step_num % 50 == 0:
            avg_e = sum(n.energy for n in alive) / len(alive) if alive else 0
            food_count = len([nut for nut in nutrients if nut.type == "food" and nut.alive])
            print("  " + str(step_num).rjust(4) + " | " + str(len(alive)).rjust(5) + " | " + str(round(avg_e,1)).rjust(5) + " | " + str(stats["deadly_contacts"]).rjust(8) + " | " + str(stats["deaths_at_deadly"]).rjust(6) + " | " + str(food_count).rjust(4))

        if not alive:
            print("")
            print("  COLONY EXTINCT at step " + str(step_num))
            break

    alive = [n for n in nodes if n.alive]
    final_alive = len(alive)
    final_deaths = stats["deaths_at_deadly"]
    final_contacts = stats["deadly_contacts"]
    final_damage = stats["deadly_damage"]
    print("")
    print("  FINAL: " + str(final_alive) + " alive, " + str(final_deaths) + " deadly deaths, " + str(final_contacts) + " contacts, " + str(round(final_damage,1)) + " damage")
    return final_alive, final_deaths, final_contacts, final_damage

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("HEAD-TO-HEAD COMPARISON: SILENT vs SCREAM")
    print("Drain: " + str(DEADLY_DRAIN) + "/step (LETHAL)")
    print("Seeds: " + str(len(START_POSITIONS)))
    print("=" * 60)

    alive_silent, deaths_silent, contacts_silent, damage_silent = run_one_simulation("SILENT (no suffering signal)", 0.0)
    alive_scream, deaths_scream, contacts_scream, damage_scream = run_one_simulation("SCREAM (suffering signal ON)", -100.0)

    print("")
    print("=" * 60)
    print("COMPARISON")
    print("=" * 60)
    print("Metric".ljust(25) + " | " + "Silent".rjust(10) + " | " + "Scream".rjust(10))
    print("-" * 50)
    print("Final population".ljust(25) + " | " + str(alive_silent).rjust(10) + " | " + str(alive_scream).rjust(10))
    print("Deadly deaths".ljust(25) + " | " + str(deaths_silent).rjust(10) + " | " + str(deaths_scream).rjust(10))
    print("Deadly contacts".ljust(25) + " | " + str(contacts_silent).rjust(10) + " | " + str(contacts_scream).rjust(10))
    print("Deadly damage".ljust(25) + " | " + str(round(damage_silent,1)).rjust(10) + " | " + str(round(damage_scream,1)).rjust(10))

    print("")
    if deaths_scream > 0 and deaths_silent == 0:
        print("*** SCREAM had deaths but Silent did not - signal may have scattered colony ***")
    elif deaths_scream < deaths_silent and alive_scream > alive_silent:
        print("*** SCREAM WINS: higher survival, fewer deaths ***")
    elif contacts_scream < contacts_silent:
        print("*** SCREAM had fewer contacts - possible avoidance ***")
    elif alive_scream > alive_silent:
        print("*** SCREAM had higher survival ***")
    elif deaths_scream < deaths_silent:
        print("*** SCREAM had fewer deaths ***")
    else:
        print("*** No clear difference in this single run ***")
        print("*** Run more seeds to determine if signal helps ***")

    print("=" * 60)
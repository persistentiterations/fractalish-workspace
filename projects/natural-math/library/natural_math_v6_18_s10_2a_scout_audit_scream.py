"""
Natural Math v6.18-S10-2a — Scout+Audit Cell Scream Diagnostic

Based on: Natural Math v6.15-S8C (frozen Stage 5B base + S6B warning + S8C cap)
Branch: S10-2a scout-written scream during relocation, audit reads scream

Purpose:
Test whether local negative memory is useful when written during scout
relocation rather than after audit failure. Scouts write scream marks
when they personally encounter dead ends or loops during relocation.
Other scouts read scream during exploration as a local avoidance penalty.
The audit follower subtracts scream from edge preference when reading
the trail.

Frozen S9B-4b discipline preserved:
- Maze: 20x20
- SCOUT_RATE: 0.30 (S9B-3 diagnostic)
- EDGE_DECAY: 0.90 (S9B-4b diagnostic)
- No BFS trail-building
- No follower writing during relocation
- No mixed scout/follower phase before audit
- Only completed scout cycles write positive relocated B-memory
- Warning marks structurally separate from trail edges
- Only scouts read warnings (followers do not)
- WARNING_CAP = 25

S10-2a additions:
- SCREAM_DECAY = 0.90, SCREAM_THRESHOLD = 0.1, SCREAM_PENALTY = 3.0
- Scouts write scream on loop (strength=1.0) and dead-end (strength=2.0)
- Scouts read scream as penalty in score_move during relocation
- Audit subtracts scream*SCREAM_PENALTY from edge preference
- Scream decays each round like warnings
- Scream is structurally separate from warnings and trail edges
"""

import random
from collections import deque

# ============================================================
# CONSTANTS (frozen S5B + S8C cap + S9B diagnostics + S10-2a scream)
# ============================================================
WIDTH, HEIGHT = 20, 20  # S9B: 20x20 for scale diagnostic
AGENT_COUNT = 30
TRAIN_ROUNDS = 10
RECALL_ROUNDS = 10
RELOCATE_ROUNDS = 20
NEW_RECALL_ROUNDS = 10
MAX_STEPS = 500
SCOUT_RATE = 0.30       # S9B-3 diagnostic
EDGE_DECAY = 0.90      # S9B-4b diagnostic

# S6B Warning constants
WARNING_DECAY = 0.90
WARNING_THRESHOLD = 0.1
WARNING_PENALTY = 2.0
WARNING_CAP = 25       # S8C confirmed default

# S10-2a: Scream constants
SCREAM_DECAY = 0.90
SCREAM_THRESHOLD = 0.1
SCREAM_PENALTY = 3.0   # stronger than WARNING_PENALTY (2.0)

DIRS = [(0, -1, "n"), (0, 1, "s"), (-1, 0, "w"), (1, 0, "e")]
DIR_MAP = {"n": (0, -1), "s": (0, 1), "w": (-1, 0), "e": (1, 0)}
OPPOSITE = {"n": "s", "s": "n", "w": "e", "e": "w"}

# ============================================================
# MAZE (frozen S5B)
# ============================================================
class Maze:
    def __init__(self, seed, forced_base=None, forced_a=None, forced_b=None):
        random.seed(seed)
        self.walls = {}
        self.cells = set()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                self.cells.add((x, y))
                for d in ["n", "s", "e", "w"]:
                    self.walls[(x, y, d)] = True
        self._generate()
        if forced_base is not None:
            self.base = forced_base
            self.resource_a = forced_a
            self.resource_b = forced_b
        else:
            self.resource_a = self._pick_far_pair()[0]
            self.resource_b = self._pick_far_pair()[1]
            self.base = (WIDTH // 2, HEIGHT // 2)

    def _neighbors(self, x, y):
        res = []
        for dx, dy, d in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                res.append((nx, ny, d))
        return res

    def _generate(self):
        visited = set()
        stack = [(0, 0)]
        visited.add((0, 0))
        while stack:
            x, y = stack[-1]
            nbrs = [(nx, ny, d) for nx, ny, d in self._neighbors(x, y) if (nx, ny) not in visited]
            if nbrs:
                nx, ny, d = random.choice(nbrs)
                self.walls[(x, y, d)] = False
                self.walls[(nx, ny, OPPOSITE[d])] = False
                visited.add((nx, ny))
                stack.append((nx, ny))
            else:
                stack.pop()

    def _bfs_dist(self, start, goal):
        if start == goal:
            return 0
        q = deque([(start, 0)])
        seen = {start}
        while q:
            (x, y), d = q.popleft()
            for dx, dy, dn in DIRS:
                if not self.walls[(x, y, dn)]:
                    nx, ny = x + dx, y + dy
                    if (nx, ny) == goal:
                        return d + 1
                    if (nx, ny) not in seen and (nx, ny) in self.cells:
                        seen.add((nx, ny))
                        q.append(((nx, ny), d + 1))
        return -1

    def _pick_far_pair(self):
        best = None
        best_dist = -1
        cells = list(self.cells)
        for _ in range(200):
            a = random.choice(cells)
            b = random.choice(cells)
            d = self._bfs_dist(a, b)
            if d > best_dist:
                best_dist = d
                best = (a, b)
        return best

    def legal_moves(self, x, y):
        res = []
        for dx, dy, d in DIRS:
            if not self.walls[(x, y, d)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                    res.append((nx, ny, d))
        return res

# ============================================================
# MEMCELL (frozen S5B)
# ============================================================
class MemCell:
    __slots__ = ("x", "y", "perm", "ghost", "weak", "last_visit", "last_success")
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.perm = 0
        self.ghost = 0
        self.weak = 0
        self.last_visit = -999
        self.last_success = -999

    def commit_cycle(self):
        self.perm += 1
        self.ghost = 5

    def decay(self, current_round):
        if self.ghost > 0:
            self.ghost -= 1
        if self.weak > 0:
            self.weak = max(0, self.weak - 0.5)

# ============================================================
# AGENT (frozen S5B + S6B warning counters)
# ============================================================
class Agent:
    def __init__(self, aid, x, y, is_scout=False):
        self.aid = aid
        self.x = x
        self.y = y
        self.is_scout = is_scout
        self.path_out = []
        self.path_back = []
        self.energy = 1000
        self.carrying = False
        self.reached_resource = False
        self.completed_cycle = False
        self.target = None
        self.steps = 0
        self.visited = set()
        self.last_dir = None
        self.scout_stack = []
        # S6B: warning counters
        self.dead_end_hits = 0
        self.loop_hits = 0
        self.failed_branches = 0

    def reset(self, x, y):
        self.x = x
        self.y = y
        self.path_out = []
        self.path_back = []
        self.energy = 1000
        self.carrying = False
        self.reached_resource = False
        self.completed_cycle = False
        self.target = None
        self.steps = 0
        self.visited = set()
        self.last_dir = None
        self.scout_stack = []
        self.dead_end_hits = 0
        self.loop_hits = 0
        self.failed_branches = 0

def compress_path(path):
    if not path:
        return path
    seen = {}
    result = []
    for pos in path:
        if pos in seen:
            idx = seen[pos]
            result = result[:idx + 1]
            seen = {p: i for i, p in enumerate(result)}
        else:
            seen[pos] = len(result)
            result.append(pos)
    return result

# ============================================================
# SIMULATION (frozen S5B + S6B warning + S8C cap + S10-2a scream)
# ============================================================
class Simulation:
    def __init__(self, seed, forced_base=None, forced_a=None, forced_b=None,
                 warning_active=False, warning_cap=WARNING_CAP):
        self.maze = Maze(seed, forced_base, forced_a, forced_b)
        self.mem = [[MemCell(x, y) for x in range(WIDTH)] for y in range(HEIGHT)]
        self.out_edges = {}
        self.home_edges = {}
        # S6B: warning memory
        self.dead_end_marks = {}
        self.warning_active = warning_active
        self.warning_cap = warning_cap
        # S10-2a: scream memory
        self.scream_marks = {}
        self.agents = []
        for i in range(AGENT_COUNT):
            is_scout = random.random() < SCOUT_RATE
            self.agents.append(Agent(i, self.maze.base[0], self.maze.base[1], is_scout=is_scout))
        self.current_resource = self.maze.resource_a
        self.round_num = 0
        # Stats
        self.warning_cells = 0
        self.warning_strength_total = 0.0
        self.warning_strength_max = 0.0
        self.warning_on_out_path = 0
        self.warning_on_home_path = 0
        self.warning_trail_overlap = 0
        # S10-2a: scream stats
        self.scream_cells = 0
        self.scream_strength_total = 0.0
        self.scream_strength_max = 0.0
        self.scream_written_total = 0.0  # total before decay

    # ---- S6B Warning methods (S8C: cap enforced) ----
    def write_warning(self, x, y, strength=1.0):
        key = (x, y)
        new_value = self.dead_end_marks.get(key, 0.0) + strength
        if self.warning_cap is not None:
            new_value = min(new_value, self.warning_cap)
        self.dead_end_marks[key] = new_value

    def get_warning(self, x, y):
        return self.dead_end_marks.get((x, y), 0.0)

    def decay_warnings(self):
        to_delete = []
        for key in list(self.dead_end_marks.keys()):
            self.dead_end_marks[key] *= WARNING_DECAY
            if self.dead_end_marks[key] < WARNING_THRESHOLD:
                to_delete.append(key)
        for key in to_delete:
            del self.dead_end_marks[key]

    # ---- S10-2a: Scream methods ----
    def write_scream(self, x, y, strength=1.0):
        key = (x, y)
        new_value = self.scream_marks.get(key, 0.0) + strength
        if self.warning_cap is not None:
            new_value = min(new_value, self.warning_cap)
        self.scream_marks[key] = new_value
        self.scream_written_total += strength

    def get_scream(self, x, y):
        return self.scream_marks.get((x, y), 0.0)

    def decay_screams(self):
        to_delete = []
        for key in list(self.scream_marks.keys()):
            self.scream_marks[key] *= SCREAM_DECAY
            if self.scream_marks[key] < SCREAM_THRESHOLD:
                to_delete.append(key)
        for key in to_delete:
            del self.scream_marks[key]

    def beacon(self, pos, target):
        if target is None:
            return 0
        dist = abs(target[0] - pos[0]) + abs(target[1] - pos[1])
        if dist == 0:
            return 100
        return 5.0 / (dist + 1)

    def reinforce_edges(self, edge_map, path, resource_id, amount=10):
        if len(path) < 2:
            return
        for i in range(len(path) - 1):
            a = path[i]
            b = path[i + 1]
            key = (a, b, resource_id)
            edge_map[key] = edge_map.get(key, 0) + amount

    def decay_edges(self):
        for key in list(self.out_edges.keys()):
            self.out_edges[key] *= EDGE_DECAY
            if self.out_edges[key] < 0.1:
                del self.out_edges[key]
        for key in list(self.home_edges.keys()):
            self.home_edges[key] *= EDGE_DECAY
            if self.home_edges[key] < 0.1:
                del self.home_edges[key]

    def score_move(self, ag, nx, ny, nd, beacon_on, target):
        cell = self.mem[ny][nx]
        s = 0.0
        cur = (ag.x, ag.y)
        nxt = (nx, ny)
        resource_id = self.current_resource

        if ag.is_scout:
            if beacon_on and target is not None:
                s += self.beacon((nx, ny), target) * 3.0
            if cell.last_visit < 0:
                s += 8.0
            else:
                age = self.round_num - cell.last_visit
                s += min(age * 0.5, 5.0)
            if ag.last_dir is not None and nd == OPPOSITE[ag.last_dir]:
                s -= 15.0
            # S6B: warning penalty (scouts only during relocation)
            # S10-2a: scream penalty (scouts only during relocation)
            if self.warning_active and self.current_resource == self.maze.resource_b:
                warning = self.get_warning(nx, ny)
                s -= warning * WARNING_PENALTY
                scream = self.get_scream(nx, ny)
                s -= scream * SCREAM_PENALTY
            return s

        if not ag.carrying:
            edge_score = self.out_edges.get((cur, nxt, resource_id), 0)
            s += edge_score * 20.0
        else:
            edge_score = self.home_edges.get((cur, nxt, resource_id), 0)
            s += edge_score * 20.0

        s += cell.perm * 1.0
        s += cell.ghost * 0.5

        if ag.last_dir is not None and nd == OPPOSITE[ag.last_dir]:
            s -= 20.0

        if beacon_on and target is not None:
            s += self.beacon((nx, ny), target)

        return s

    def step_agent(self, ag, beacon_on, target):
        if ag.energy <= 0:
            return "none"
        moves = self.maze.legal_moves(ag.x, ag.y)
        if not moves:
            return "none"

        if ag.is_scout:
            if ag.carrying:
                if ag.scout_stack:
                    next_pos = ag.scout_stack.pop()
                    for nx, ny, nd in moves:
                        if (nx, ny) == next_pos:
                            ag.x, ag.y = nx, ny
                            ag.last_dir = nd
                            ag.steps += 1
                            ag.energy -= 1
                            ag.path_back.append((nx, ny))
                            if (nx, ny) == self.maze.base:
                                ag.completed_cycle = True
                                return "cycle"
                            return "none"
                nx, ny, nd = random.choice(moves)
                ag.x, ag.y = nx, ny
                ag.last_dir = nd
                ag.steps += 1
                ag.energy -= 1
                ag.path_back.append((nx, ny))
                if (nx, ny) == self.maze.base:
                    ag.completed_cycle = True
                    return "cycle"
                return "none"

            ag.visited.add((ag.x, ag.y))
            scores = []
            for nx, ny, nd in moves:
                s = self.score_move(ag, nx, ny, nd, beacon_on, target)
                s += random.random() * 2.0
                scores.append((s, nx, ny, nd))
            scores.sort(reverse=True)
            _, nx, ny, nd = scores[0]

            # S6B: loop detection
            # S10-2a: also write scream on loop
            if (nx, ny) in ag.visited:
                ag.loop_hits += 1
                self.write_warning(ag.x, ag.y, 1.0)
                self.write_scream(ag.x, ag.y, 1.0)

            # S6B: dead-end detection
            # S10-2a: also write scream on dead end
            all_visited = all((mx, my) in ag.visited for mx, my, md in moves)
            if all_visited and len(moves) > 0:
                ag.dead_end_hits += 1
                self.write_warning(ag.x, ag.y, 2.0)
                self.write_scream(ag.x, ag.y, 2.0)

            ag.scout_stack.append((ag.x, ag.y))
            ag.path_out.append((nx, ny))
            ag.x, ag.y = nx, ny
            ag.last_dir = nd
            ag.steps += 1
            ag.energy -= 1
            cell = self.mem[ny][nx]
            cell.last_visit = self.round_num
            if (nx, ny) == target and not ag.carrying:
                ag.carrying = True
                ag.reached_resource = True
                ag.path_back = [(nx, ny)]
                return "reach"
            return "none"

        else:
            scores = []
            for nx, ny, nd in moves:
                s = self.score_move(ag, nx, ny, nd, beacon_on, target)
                s += random.random() * 0.2
                scores.append((s, nx, ny, nd))
            scores.sort(reverse=True)
            _, nx, ny, nd = scores[0]
            ag.x, ag.y = nx, ny
            ag.last_dir = nd
            ag.steps += 1
            ag.energy -= 1
            ag.visited.add((nx, ny))
            cell = self.mem[ny][nx]
            cell.last_visit = self.round_num
            if not ag.carrying:
                ag.path_out.append((nx, ny))
            else:
                ag.path_back.append((nx, ny))
            if (nx, ny) == target and not ag.carrying:
                ag.carrying = True
                ag.reached_resource = True
                ag.path_back = [(nx, ny)]
                return "reach"
            if (nx, ny) == self.maze.base and ag.carrying and ag.reached_resource:
                ag.completed_cycle = True
                return "cycle"
            return "none"

    def do_round(self, round_index, beacon_on=True, scouts_only=False, followers_only=False):
        self.round_num = round_index
        for ag in self.agents:
            ag.reset(self.maze.base[0], self.maze.base[1])
        target = self.current_resource
        reached = 0
        cycled = 0
        scout_reached = 0
        scout_cycled = 0
        follower_reached = 0
        follower_cycled = 0
        completed = set()

        for step in range(MAX_STEPS):
            for ag in self.agents:
                if ag.aid in completed:
                    continue
                if scouts_only and not ag.is_scout:
                    continue
                if followers_only and ag.is_scout:
                    continue
                event = self.step_agent(ag, beacon_on, target)
                if event == "reach":
                    reached += 1
                    if ag.is_scout:
                        scout_reached += 1
                    else:
                        follower_reached += 1
                elif event == "cycle":
                    cycled += 1
                    completed.add(ag.aid)
                    if ag.is_scout:
                        scout_cycled += 1
                    else:
                        follower_cycled += 1
                        # S9B-4b: follower reinforcement stays at frozen value (5)
                        resource_id = self.current_resource
                        clean_out = compress_path([self.maze.base] + ag.path_out)
                        clean_home = compress_path(ag.path_back)
                        self.reinforce_edges(self.out_edges, clean_out, resource_id, amount=5)
                        self.reinforce_edges(self.home_edges, clean_home, resource_id, amount=5)
                    if ag.is_scout:
                        # Scout reinforcement stays at frozen value (10)
                        resource_id = self.current_resource
                        clean_out = compress_path([self.maze.base] + ag.path_out)
                        clean_home = compress_path(ag.path_back)
                        self.reinforce_edges(self.out_edges, clean_out, resource_id, amount=10)
                        self.reinforce_edges(self.home_edges, clean_home, resource_id, amount=10)
                        for p in ag.path_out:
                            px, py = p
                            self.mem[py][px].last_success = round_index
                            self.mem[py][px].commit_cycle()
                        for p in ag.path_back:
                            px, py = p
                            self.mem[py][px].last_success = round_index
                            self.mem[py][px].commit_cycle()

        assert cycled <= reached, f"Invalid: cycled={cycled}, reached={reached}"
        for y in range(HEIGHT):
            for x in range(WIDTH):
                self.mem[y][x].decay(round_index)
        self.decay_edges()
        self.decay_warnings()
        self.decay_screams()  # S10-2a
        return reached, cycled, scout_reached, scout_cycled, follower_reached, follower_cycled

    def train(self, rounds, beacon_on=True):
        results = []
        for r in range(rounds):
            res = self.do_round(r, beacon_on=beacon_on)
            results.append(res)
        return results


# ============================================================
# S10-2a Protocol: Scout+Audit Cell Scream Diagnostic
# ============================================================

def run_seed_s10_2a(seed, forced_base, forced_a, forced_b,
                    relocate_rounds=20, warning_active=False, warning_cap=WARNING_CAP):
    """Run S10-2a scout+audit scream diagnostic with S9B-4b configuration."""
    sim = Simulation(seed, forced_base, forced_a, forced_b,
                     warning_active=warning_active, warning_cap=warning_cap)
    scouts = sum(1 for ag in sim.agents if ag.is_scout)
    followers = AGENT_COUNT - scouts

    # Train A
    train = sim.train(TRAIN_ROUNDS, beacon_on=True)

    # Recall A
    for r in range(RECALL_ROUNDS):
        sim.do_round(TRAIN_ROUNDS + r, beacon_on=False)

    # Relocate B — scouts only
    sim.current_resource = sim.maze.resource_b
    relocate = []
    for r in range(relocate_rounds):
        sim.round_num = TRAIN_ROUNDS + r
        for ag in sim.agents:
            ag.reset(sim.maze.base[0], sim.maze.base[1])
        target = sim.current_resource
        completed = set()
        scout_cycled = 0
        follower_cycled = 0

        for step in range(MAX_STEPS):
            for ag in sim.agents:
                if ag.aid in completed:
                    continue
                if not ag.is_scout:
                    continue
                event = sim.step_agent(ag, beacon_on=True, target=target)
                if event == "cycle":
                    completed.add(ag.aid)
                    if ag.is_scout:
                        scout_cycled += 1
                        # S9B-4a: scout relocation reinforcement = 20
                        resource_id = sim.current_resource
                        clean_out = compress_path([sim.maze.base] + ag.path_out)
                        clean_home = compress_path(ag.path_back)
                        sim.reinforce_edges(sim.out_edges, clean_out, resource_id, amount=20)
                        sim.reinforce_edges(sim.home_edges, clean_home, resource_id, amount=20)
                        for p in ag.path_out:
                            px, py = p
                            sim.mem[py][px].last_success = sim.round_num
                            sim.mem[py][px].commit_cycle()
                        for p in ag.path_back:
                            px, py = p
                            sim.mem[py][px].last_success = sim.round_num
                            sim.mem[py][px].commit_cycle()

        relocate.append((0, len(completed), 0, scout_cycled, 0, follower_cycled))
        for y in range(HEIGHT):
            for x in range(WIDTH):
                sim.mem[y][x].decay(sim.round_num)
        sim.decay_edges()
        sim.decay_warnings()
        sim.decay_screams()  # S10-2a

    # ASSERT: follower_relocate_cycles == 0
    foll_reloc_cycles = sum(r[5] for r in relocate)

    # Audit with S10-2a scream subtraction
    def audit_out():
        pos = sim.maze.base
        resource = sim.current_resource
        seen = {pos}
        for step in range(200):
            if pos == resource:
                return True, step, "REACHED"
            x, y = pos
            choices = []
            for nx, ny, d in sim.maze.legal_moves(x, y):
                edge = sim.out_edges.get((pos, (nx, ny), resource), 0)
                # S10-2a: subtract scream from edge preference
                scream = sim.get_scream(nx, ny)
                effective_edge = edge - scream * SCREAM_PENALTY
                choices.append((effective_edge, (nx, ny)))
            choices.sort(reverse=True)
            if not choices:
                return False, step, "DEAD_END"
            best_edge, best_next = choices[0]
            if best_edge <= 0:
                return False, step, "DEAD_END"
            if best_next in seen:
                return False, step, "LOOP"
            pos = best_next
            seen.add(pos)
        return False, 200, "TIMEOUT"

    def audit_home():
        pos = sim.current_resource
        start = sim.maze.base
        resource = sim.current_resource
        seen = {pos}
        for step in range(200):
            if pos == start:
                return True, step, "REACHED"
            x, y = pos
            choices = []
            for nx, ny, d in sim.maze.legal_moves(x, y):
                edge = sim.home_edges.get((pos, (nx, ny), resource), 0)
                # S10-2a: subtract scream from edge preference
                scream = sim.get_scream(nx, ny)
                effective_edge = edge - scream * SCREAM_PENALTY
                choices.append((effective_edge, (nx, ny)))
            choices.sort(reverse=True)
            if not choices:
                return False, step, "DEAD_END"
            best_edge, best_next = choices[0]
            if best_edge <= 0:
                return False, step, "DEAD_END"
            if best_next in seen:
                return False, step, "LOOP"
            pos = best_next
            seen.add(pos)
        return False, 200, "TIMEOUT"

    ok_out, _, reason_out = audit_out()
    ok_home, _, reason_home = audit_home()

    # Follower-only recall (beacon off)
    foll_only_cycles = 0
    for r in range(NEW_RECALL_ROUNDS):
        res = sim.do_round(TRAIN_ROUNDS + relocate_rounds + r,
                          beacon_on=False, followers_only=True)
        foll_only_cycles += res[5]

    foll_rate = foll_only_cycles / (followers * NEW_RECALL_ROUNDS) if followers > 0 else 0

    # Compute warning stats
    sim.warning_cells = len(sim.dead_end_marks)
    sim.warning_strength_total = sum(sim.dead_end_marks.values())
    sim.warning_strength_max = max(sim.dead_end_marks.values()) if sim.dead_end_marks else 0.0

    # S10-2a: scream stats
    sim.scream_cells = len(sim.scream_marks)
    sim.scream_strength_total = sum(sim.scream_marks.values())
    sim.scream_strength_max = max(sim.scream_marks.values()) if sim.scream_marks else 0.0

    # Determine pass/fail and reason
    passed = ok_out and ok_home and foll_rate >= 0.50 and foll_reloc_cycles == 0

    if foll_reloc_cycles != 0:
        fail_reason = "FOLLOWER_CONTAMINATION"
    elif sum(r[3] for r in relocate) == 0:
        fail_reason = "NO_SCOUT_CYCLE"
    elif not ok_out:
        fail_reason = "AUDIT_OUT_FAIL"
    elif not ok_home:
        fail_reason = "AUDIT_HOME_FAIL"
    elif foll_rate < 0.50:
        fail_reason = "FOLLOWER_RECALL_FAIL"
    else:
        fail_reason = "PASS"

    return {
        "seed": seed,
        "dist_a": sim.maze._bfs_dist(sim.maze.base, sim.maze.resource_a),
        "dist_b": sim.maze._bfs_dist(sim.maze.base, sim.maze.resource_b),
        "scout_relocate_cycles": sum(r[3] for r in relocate),
        "follower_relocate_cycles": foll_reloc_cycles,
        "audit_out": reason_out,
        "audit_home": reason_home,
        "foll_only_cycles": foll_only_cycles,
        "foll_rate": foll_rate,
        "warning_cells": sim.warning_cells,
        "warning_strength_total": round(sim.warning_strength_total, 1),
        "warning_strength_max": round(sim.warning_strength_max, 1),
        "scream_cells": sim.scream_cells,
        "scream_strength_total": round(sim.scream_strength_total, 1),
        "scream_strength_max": round(sim.scream_strength_max, 1),
        "scream_written_total": round(sim.scream_written_total, 1),
        "pass": passed,
        "fail_reason": fail_reason
    }


# ============================================================
# S10-2a Targeted Test Runner
# ============================================================

def run_s10_2a_targeted():
    """
    S10-2a targeted diagnostic.
    Seeds: F1_close_original seed=0, seed=5; F3_close_corner seed=5
    Rounds: [5, 10, 20]
    """
    print("=" * 90)
    print("Natural Math v6.18-S10-2a — Scout+Audit Cell Scream Diagnostic (Targeted)")
    print("=" * 90)
    print()
    print("Configuration:")
    print(f"  Maze: {WIDTH}x{HEIGHT}")
    print(f"  SCOUT_RATE: {SCOUT_RATE}")
    print(f"  EDGE_DECAY: {EDGE_DECAY}")
    print(f"  WARNING_CAP: {WARNING_CAP}")
    print(f"  SCREAM_PENALTY: {SCREAM_PENALTY}")
    print()
    print("Frozen S9B-4b base preserved:")
    print("  Follower reinforcement: 5 (unchanged)")
    print("  Scout do_round reinforcement: 10 (unchanged)")
    print("  Scout relocation reinforcement: 20 (S9B-4a diagnostic)")
    print()
    print("S10-2a additions:")
    print("  Scouts write scream on loop (1.0) and dead-end (2.0)")
    print("  Scouts read scream as penalty during relocation")
    print("  Audit subtracts scream*3.0 from edge preference")
    print()

    # Targeted seeds from S9B-4b failures
    test_cases = [
        ("F1_close_original", 0, (0, 0), (9, 9), (5, 3)),
        ("F1_close_original", 5, (0, 0), (9, 9), (5, 3)),
        ("F3_close_corner", 5, (0, 0), (10, 10), (10, 0)),
    ]

    rounds = [5, 10, 20]

    print("Targeted test cases (known S9B-4b failing seeds):")
    for fixture, seed, base, a, b in test_cases:
        print(f"  {fixture} seed={seed}")
    print()

    results = []
    for fixture, seed, base, a, b in test_cases:
        for R in rounds:
            result = run_seed_s10_2a(seed, base, a, b,
                                     relocate_rounds=R,
                                     warning_active=True,
                                     warning_cap=WARNING_CAP)
            results.append((fixture, seed, R, result))
            status = "PASS" if result["pass"] else f"FAIL:{result['fail_reason']}"
            print(f"{fixture:18s} seed={seed:2d} R={R:2d} | "
                  f"ScoutRC={result['scout_relocate_cycles']:3d} | "
                  f"{status:18s} | "
                  f"WarnC={result['warning_cells']:3d} | "
                  f"WarnMx={result['warning_strength_max']:5.1f} | "
                  f"ScreamC={result['scream_cells']:3d} | "
                  f"ScreamMx={result['scream_strength_max']:5.1f} | "
                  f"ScreamWrt={result['scream_written_total']:6.1f}")

    print()
    print("=" * 90)
    print("SUMMARY")
    print("=" * 90)

    total = len(results)
    passed = sum(1 for _, _, _, r in results if r["pass"])
    print(f"Total passes: {passed}/{total}")

    # Compare to S9B-4b baseline
    print()
    print("S9B-4b baseline (no scream):")
    print("  F1 seed=0: R=5=FAIL, R=10=FAIL, R=20=FAIL")
    print("  F1 seed=5: R=5=FAIL, R=10=FAIL, R=20=FAIL")
    print("  F3 seed=5: R=5=FAIL, R=10=FAIL, R=20=FAIL")
    print()
    print("S10-2a interpretation:")
    print("  If AUDIT_OUT_FAIL -> PASS: scream helps resolve misleading branches")
    print("  If NO_SCOUT_CYCLE unchanged: scream cannot fix discovery problems")
    print("  If unchanged: local scream too weak or conflict not locally resolvable")
    print("  If worsened: scream suppresses useful exploration too broadly")

    return results


if __name__ == "__main__":
    run_s10_2a_targeted()

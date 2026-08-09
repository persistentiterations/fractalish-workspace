"""Natural Math v6.18-S10-5 — Trail Formation Diagnostic"""

import random
from collections import deque

WIDTH, HEIGHT = 20, 20
AGENT_COUNT = 30
TRAIN_ROUNDS = 10
RECALL_ROUNDS = 10
RELOCATE_ROUNDS = 20
NEW_RECALL_ROUNDS = 10
MAX_STEPS = 500
SCOUT_RATE = 0.30
EDGE_DECAY = 0.90
WARNING_DECAY = 0.90
WARNING_THRESHOLD = 0.1
WARNING_PENALTY = 2.0
WARNING_CAP = 25
SCREAM_DECAY = 0.90
SCREAM_THRESHOLD = 0.1
SCREAM_PENALTY = 3.0

DIRS = [(0, -1, "n"), (0, 1, "s"), (-1, 0, "w"), (1, 0, "e")]
DIR_MAP = {"n": (0, -1), "s": (0, 1), "w": (-1, 0), "e": (1, 0)}
OPPOSITE = {"n": "s", "s": "n", "w": "e", "e": "w"}

AUDIT_TIMEOUT = MAX_STEPS  # S10-9 correction: audit timeout equals max steps


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


def find_cycle_edges(path):
    """Find edges that form a cycle in the path."""
    if not path or len(path) < 2:
        return []
    seen = {}
    cycle_edges = []
    for i, pos in enumerate(path):
        if pos in seen:
            cycle_start = seen[pos]
            for j in range(cycle_start, i):
                if j + 1 < len(path):
                    cycle_edges.append((path[j], path[j+1]))
            break
        seen[pos] = i
    return cycle_edges


class Simulation:
    def __init__(self, seed, forced_base=None, forced_a=None, forced_b=None,
                 warning_active=False, warning_cap=WARNING_CAP):
        self.maze = Maze(seed, forced_base, forced_a, forced_b)
        self.mem = [[MemCell(x, y) for x in range(WIDTH)] for y in range(HEIGHT)]
        self.out_edges = {}
        self.home_edges = {}
        self.dead_end_marks = {}
        self.warning_active = warning_active
        self.warning_cap = warning_cap
        self.scream_edges = {}
        self.agents = []
        for i in range(AGENT_COUNT):
            is_scout = random.random() < SCOUT_RATE
            self.agents.append(Agent(i, self.maze.base[0], self.maze.base[1], is_scout=is_scout))
        self.current_resource = self.maze.resource_a
        self.round_num = 0
        self.scout_success_edges_out = set()
        self.scout_success_edges_home = set()

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

    def is_success_edge(self, from_pos, to_pos):
        return (
            (from_pos, to_pos) in self.scout_success_edges_out
            or (from_pos, to_pos) in self.scout_success_edges_home
        )

    def write_scream_edge(self, from_pos, to_pos, resource_id, strength=1.0):
        # S10-9 correction: do not write scream on edges already proven successful
        if self.is_success_edge(from_pos, to_pos):
            return
        key = (from_pos, to_pos, resource_id)
        new_value = self.scream_edges.get(key, 0.0) + strength
        if self.warning_cap is not None:
            new_value = min(new_value, self.warning_cap)
        self.scream_edges[key] = new_value

    def get_scream_edge(self, from_pos, to_pos, resource_id):
        return self.scream_edges.get((from_pos, to_pos, resource_id), 0.0)

    def decay_screams(self):
        to_delete = []
        for key in list(self.scream_edges.keys()):
            self.scream_edges[key] *= SCREAM_DECAY
            if self.scream_edges[key] < SCREAM_THRESHOLD:
                to_delete.append(key)
        for key in to_delete:
            del self.scream_edges[key]

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
            if self.warning_active and self.current_resource == self.maze.resource_b:
                warning = self.get_warning(nx, ny)
                s -= warning * WARNING_PENALTY
                scream = self.get_scream_edge(cur, nxt, resource_id)
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

            # S10-4a cycle-only scream
            temp_path = ag.path_out + [(ag.x, ag.y), (nx, ny)]
            cycle_edges = find_cycle_edges(temp_path)
            if cycle_edges:
                ag.loop_hits += 1
                resource_id = self.current_resource
                for from_pos, to_pos in cycle_edges:
                    self.write_scream_edge(from_pos, to_pos, resource_id, 1.0)

            all_visited = all((mx, my) in ag.visited for mx, my, md in moves)
            if all_visited and len(moves) > 0:
                ag.dead_end_hits += 1
                self.write_warning(ag.x, ag.y, 2.0)

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
                        resource_id = self.current_resource
                        clean_out = compress_path([self.maze.base] + ag.path_out)
                        clean_home = compress_path(ag.path_back)
                        self.reinforce_edges(self.out_edges, clean_out, resource_id, amount=5)
                        self.reinforce_edges(self.home_edges, clean_home, resource_id, amount=5)
                    if ag.is_scout:
                        resource_id = self.current_resource
                        clean_out = compress_path([self.maze.base] + ag.path_out)
                        clean_home = compress_path(ag.path_back)
                        self.reinforce_edges(self.out_edges, clean_out, resource_id, amount=10)
                        self.reinforce_edges(self.home_edges, clean_home, resource_id, amount=10)
                        for i in range(len(clean_out) - 1):
                            self.scout_success_edges_out.add((clean_out[i], clean_out[i+1]))
                        for i in range(len(clean_home) - 1):
                            self.scout_success_edges_home.add((clean_home[i], clean_home[i+1]))
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
        self.decay_screams()
        return reached, cycled, scout_reached, scout_cycled, follower_reached, follower_cycled

    def train(self, rounds, beacon_on=True):
        results = []
        for r in range(rounds):
            res = self.do_round(r, beacon_on=beacon_on)
            results.append(res)
        return results


def run_seed_s10_5(seed, forced_base, forced_a, forced_b, relocate_rounds=20):
    sim = Simulation(seed, forced_base, forced_a, forced_b, warning_active=True, warning_cap=WARNING_CAP)
    scouts = sum(1 for ag in sim.agents if ag.is_scout)
    followers = AGENT_COUNT - scouts

    train = sim.train(TRAIN_ROUNDS, beacon_on=True)

    for r in range(RECALL_ROUNDS):
        sim.do_round(TRAIN_ROUNDS + r, beacon_on=False)

    sim.current_resource = sim.maze.resource_b

    relocate = []
    for r in range(relocate_rounds):
        sim.round_num = TRAIN_ROUNDS + r
        for ag in sim.agents:
            ag.reset(sim.maze.base[0], sim.maze.base[1])
        target = sim.current_resource
        completed = set()
        scout_cycled = 0

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
                        resource_id = sim.current_resource
                        clean_out = compress_path([sim.maze.base] + ag.path_out)
                        clean_home = compress_path(ag.path_back)
                        sim.reinforce_edges(sim.out_edges, clean_out, resource_id, amount=20)
                        sim.reinforce_edges(sim.home_edges, clean_home, resource_id, amount=20)
                        for i in range(len(clean_out) - 1):
                            sim.scout_success_edges_out.add((clean_out[i], clean_out[i+1]))
                        for i in range(len(clean_home) - 1):
                            sim.scout_success_edges_home.add((clean_home[i], clean_home[i+1]))
                        for p in ag.path_out:
                            px, py = p
                            sim.mem[py][px].last_success = sim.round_num
                            sim.mem[py][px].commit_cycle()
                        for p in ag.path_back:
                            px, py = p
                            sim.mem[py][px].last_success = sim.round_num
                            sim.mem[py][px].commit_cycle()

        relocate.append((0, len(completed), 0, scout_cycled, 0, 0))

        for y in range(HEIGHT):
            for x in range(WIDTH):
                sim.mem[y][x].decay(sim.round_num)
        sim.decay_edges()
        sim.decay_warnings()
        sim.decay_screams()

    # ===== S10-5 TRAIL FORMATION ANALYSIS =====
    resource = sim.current_resource

    # 1. Count positive out_edges for resource_b
    positive_out_edges = []
    for key, val in sim.out_edges.items():
        a, b, res_id = key
        if res_id == resource and val > 0:
            positive_out_edges.append((a, b, val))

    # 2. Build directed graph from positive out_edges
    graph = {}  # node -> list of (neighbor, strength)
    for a, b, val in positive_out_edges:
        if a not in graph:
            graph[a] = []
        graph[a].append((b, val))

    # 3. Find connected components from base using BFS on learned edges
    base = sim.maze.base
    if base not in graph:
        learned_component = set()
        reaches_b = False
    else:
        learned_component = set()
        queue = deque([base])
        learned_component.add(base)
        while queue:
            pos = queue.popleft()
            if pos in graph:
                for neighbor, strength in graph[pos]:
                    if neighbor not in learned_component:
                        learned_component.add(neighbor)
                        queue.append(neighbor)
        reaches_b = resource in learned_component

    # 4. Count components in the learned edge graph
    all_nodes = set()
    for a, b, val in positive_out_edges:
        all_nodes.add(a)
        all_nodes.add(b)

    visited_nodes = set()
    num_components = 0
    for node in all_nodes:
        if node not in visited_nodes:
            num_components += 1
            queue = deque([node])
            visited_nodes.add(node)
            while queue:
                pos = queue.popleft()
                if pos in graph:
                    for neighbor, strength in graph[pos]:
                        if neighbor not in visited_nodes:
                            visited_nodes.add(neighbor)
                            queue.append(neighbor)

    # 5. Check if successful scout paths are connected from base
    scout_paths_from_base = set()
    for edge in sim.scout_success_edges_out:
        a, b = edge
        if a == base:
            scout_paths_from_base.add(b)

    # 6. Run audit to see what happens
    def audit_out():
        pos = sim.maze.base
        resource = sim.current_resource
        seen = {pos}
        audit_path = [pos]
        for step in range(AUDIT_TIMEOUT):
            if pos == resource:
                return True, step, "REACHED", audit_path
            x, y = pos
            choices = []
            for nx, ny, d in sim.maze.legal_moves(x, y):
                edge = sim.out_edges.get((pos, (nx, ny), resource), 0)
                scream = sim.get_scream_edge(pos, (nx, ny), resource)
                effective_edge = edge - scream * SCREAM_PENALTY
                choices.append((effective_edge, (nx, ny)))
            choices.sort(reverse=True)
            if not choices:
                return False, step, "DEAD_END", audit_path
            best_edge, best_next = choices[0]
            if best_edge <= 0:
                return False, step, "DEAD_END", audit_path
            if best_next in seen:
                return False, step, "LOOP", audit_path
            pos = best_next
            seen.add(pos)
            audit_path.append(pos)
        return False, AUDIT_TIMEOUT, "TIMEOUT", audit_path

    def audit_home():
        pos = sim.current_resource
        start = sim.maze.base
        resource = sim.current_resource
        seen = {pos}
        audit_path = [pos]
        for step in range(AUDIT_TIMEOUT):
            if pos == start:
                return True, step, "REACHED", audit_path
            x, y = pos
            choices = []
            for nx, ny, d in sim.maze.legal_moves(x, y):
                edge = sim.home_edges.get((pos, (nx, ny), resource), 0)
                scream = sim.get_scream_edge(pos, (nx, ny), resource)
                effective_edge = edge - scream * SCREAM_PENALTY
                choices.append((effective_edge, (nx, ny)))
            choices.sort(reverse=True)
            if not choices:
                return False, step, "DEAD_END", audit_path
            best_edge, best_next = choices[0]
            if best_edge <= 0:
                return False, step, "DEAD_END", audit_path
            if best_next in seen:
                return False, step, "LOOP", audit_path
            pos = best_next
            seen.add(pos)
            audit_path.append(pos)
        return False, AUDIT_TIMEOUT, "TIMEOUT", audit_path

    ok_out, steps_out, reason_out, audit_out_path = audit_out()
    ok_home, steps_home, reason_home, audit_home_path = audit_home()

    # 7. Where does audit leave the learned component?
    audit_left_component = None
    if audit_out_path and len(audit_out_path) > 1:
        for i, pos in enumerate(audit_out_path):
            if pos not in learned_component:
                audit_left_component = (i, pos)
                break

    # 8. Are successful scout paths disconnected from base?
    scout_paths_connected = False
    for edge in sim.scout_success_edges_out:
        a, b = edge
        if a in learned_component or a == base:
            scout_paths_connected = True
            break

    foll_only_cycles = 0
    for r in range(NEW_RECALL_ROUNDS):
        res = sim.do_round(TRAIN_ROUNDS + relocate_rounds + r,
                          beacon_on=False, followers_only=True)
        foll_only_cycles += res[5]

    foll_rate = foll_only_cycles / (followers * NEW_RECALL_ROUNDS) if followers > 0 else 0

    passed = ok_out and ok_home and foll_rate >= 0.50

    if not ok_out:
        fail_reason = "AUDIT_OUT_FAIL"
    elif not ok_home:
        fail_reason = "AUDIT_HOME_FAIL"
    elif foll_rate < 0.50:
        fail_reason = "FOLLOWER_RECALL_FAIL"
    else:
        fail_reason = "PASS"

    # Interpretation
    if not reaches_b:
        trail_diagnosis = "NO_CONTINUOUS_PATH"
        trail_detail = "Base component does not contain resource_b"
    elif ok_out:
        trail_diagnosis = "PATH_EXISTS_AUDIT_OK"
        trail_detail = "Continuous path exists and audit follows it"
    else:
        trail_diagnosis = "PATH_EXISTS_AUDIT_FAILS"
        trail_detail = "Continuous path exists but greedy audit fails"

    if not scout_paths_connected and sim.scout_success_edges_out:
        scout_diagnosis = "SCOUT_PATHS_DISCONNECTED"
    elif not sim.scout_success_edges_out:
        scout_diagnosis = "NO_SCOUT_SUCCESS"
    else:
        scout_diagnosis = "SCOUT_PATHS_CONNECTED"

    # Count scream edges that overlap with success edges
    scream_on_success = 0
    for key in sim.scream_edges:
        from_pos, to_pos, _ = key
        if (from_pos, to_pos) in sim.scout_success_edges_out or (from_pos, to_pos) in sim.scout_success_edges_home:
            scream_on_success += 1

    return {
        "seed": seed,
        "scout_relocate_cycles": sum(r[3] for r in relocate),
        "positive_out_edges": len(positive_out_edges),
        "learned_components": num_components,
        "base_component_size": len(learned_component),
        "reaches_b": reaches_b,
        "audit_out": reason_out,
        "audit_home": reason_home,
        "audit_out_steps": steps_out,
        "audit_home_steps": steps_home,
        "audit_left_component": audit_left_component,
        "scout_paths_connected": scout_paths_connected,
        "scout_diagnosis": scout_diagnosis,
        "trail_diagnosis": trail_diagnosis,
        "trail_detail": trail_detail,
        "foll_rate": foll_rate,
        "pass": passed,
        "scream_on_success": scream_on_success,
        "fail_reason": fail_reason
    }


def run_s10_5_targeted():
    print("=" * 100)
    print("Natural Math v6.18-S10-5 — Trail Formation Diagnostic")
    print("=" * 100)
    print()
    print("Question: Does out_edges contain a continuous path from base to resource_b?")
    print()

    test_cases = [
        ("F1_close_original", 0, (0, 0), (9, 9), (5, 3)),
        ("F1_close_original", 5, (0, 0), (9, 9), (5, 3)),
        ("F3_close_corner", 5, (0, 0), (10, 10), (10, 0)),
    ]
    rounds = [10, 20]

    results = []
    for fixture, seed, base, a, b in test_cases:
        for R in rounds:
            print("Running " + fixture + " seed=" + str(seed) + " R=" + str(R) + "...")
            result = run_seed_s10_5(seed, base, a, b, relocate_rounds=R)
            results.append((fixture, seed, R, result))

            print()
            print("=" * 80)
            print("CASE: " + fixture + " | Seed=" + str(seed) + " | R=" + str(R))
            print("=" * 80)
            status = "PASS" if result['pass'] else "FAIL:" + result['fail_reason']
            print("Status: " + status)
            print("ScoutRC=" + str(result['scout_relocate_cycles']))
            print("Positive out_edges for B: " + str(result['positive_out_edges']))
            print("Learned components: " + str(result['learned_components']))
            print("Base component size: " + str(result['base_component_size']))
            print("Base component reaches B: " + str(result['reaches_b']))
            print("AuditOut: " + result['audit_out'] + " (steps=" + str(result['audit_out_steps']) + ")")
            print("AuditHome: " + result['audit_home'] + " (steps=" + str(result['audit_home_steps']) + ")")
            print("Audit left component at: " + str(result['audit_left_component']))
            print("Scout paths connected from base: " + str(result['scout_paths_connected']))
            print("Trail diagnosis: " + result['trail_diagnosis'])
            print("Trail detail: " + result['trail_detail'])
            print("Scout diagnosis: " + result['scout_diagnosis'])

    print()
    print("=" * 100)
    print("S10-5 DIAGNOSTIC SUMMARY")
    print("=" * 100)
    print("Case               | R  | Seed | ScoutRC | PosEdges | Components | BaseCompSz | ReachesB | AuditOut   | AuditHome  | TrailDiagnosis          | ScoutDiagnosis")
    print("-" * 160)
    for fixture, seed, R, result in results:
        print(fixture.ljust(18) + " | " + str(R).rjust(2) + " | " + str(seed).rjust(4) + " | " + str(result['scout_relocate_cycles']).rjust(7) + " | " + str(result['positive_out_edges']).rjust(8) + " | " + str(result['learned_components']).rjust(10) + " | " + str(result['base_component_size']).rjust(10) + " | " + str(result['reaches_b']).rjust(8) + " | " + result['audit_out'].ljust(10) + " | " + result['audit_home'].ljust(10) + " | " + result['trail_diagnosis'].ljust(23) + " | " + result['scout_diagnosis'])

    # Interpretation
    print()
    print("=" * 100)
    print("INTERPRETATION")
    print("=" * 100)

    no_path = sum(1 for _, _, _, r in results if not r['reaches_b'])
    path_audit_fails = sum(1 for _, _, _, r in results if r['reaches_b'] and not r['pass'])
    path_audit_ok = sum(1 for _, _, _, r in results if r['reaches_b'] and r['pass'])

    print("Cases where base component does NOT reach B: " + str(no_path) + "/" + str(len(results)))
    print("Cases where base component reaches B but audit fails: " + str(path_audit_fails) + "/" + str(len(results)))
    print("Cases where base component reaches B and audit passes: " + str(path_audit_ok) + "/" + str(len(results)))

    if no_path == len(results):
        print()
        print("CONCLUSION: The learned edge graph NEVER contains a continuous path from base to resource_b.")
        print("The problem is TRAIL FORMATION — scouts succeed individually but their reinforced edges")
        print("do not form a single connected route that audit can follow.")
        print()
        print("Next action: Investigate why scout paths don't create continuous learned edges.")
        print("Possible causes:")
        print("  1. Different scouts take different routes — edges are scattered")
        print("  2. Path compression removes critical intermediate edges")
        print("  3. Edge decay between rounds disconnects the path")
        print("  4. Reinforcement is too weak to overcome decay across the full distance")
    elif path_audit_fails > 0:
        print()
        print("CONCLUSION: A continuous path exists in some cases, but greedy audit fails to follow it.")
        print("The problem is AUDIT READER FRAGILITY.")
    else:
        print()
        print("CONCLUSION: Continuous paths exist and audit follows them.")
        print("The problem may be elsewhere (home path, follower recall, etc.)")

    return results


if __name__ == "__main__":
    run_s10_5_targeted()

"""Natural Math v6.18-S10-2c — Scout+Audit Edge Scream Diagnostic"""

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
        self.warning_cells = 0
        self.warning_strength_total = 0.0
        self.warning_strength_max = 0.0
        self.warning_on_out_path = 0
        self.warning_on_home_path = 0
        self.warning_trail_overlap = 0
        self.scream_edges_count = 0
        self.scream_strength_total = 0.0
        self.scream_strength_max = 0.0
        self.scream_written_total = 0.0

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

    def write_scream_edge(self, from_pos, to_pos, resource_id, strength=1.0):
        key = (from_pos, to_pos, resource_id)
        new_value = self.scream_edges.get(key, 0.0) + strength
        if self.warning_cap is not None:
            new_value = min(new_value, self.warning_cap)
        self.scream_edges[key] = new_value
        self.scream_written_total += strength

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

            if (nx, ny) in ag.visited:
                ag.loop_hits += 1
                self.write_warning(ag.x, ag.y, 1.0)
                resource_id = self.current_resource
                self.write_scream_edge((ag.x, ag.y), (nx, ny), resource_id, 1.0)

            all_visited = all((mx, my) in ag.visited for mx, my, md in moves)
            if all_visited and len(moves) > 0:
                ag.dead_end_hits += 1
                self.write_warning(ag.x, ag.y, 2.0)
                resource_id = self.current_resource
                self.write_scream_edge((ag.x, ag.y), (nx, ny), resource_id, 2.0)

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


def run_seed_s10_2c(seed, forced_base, forced_a, forced_b,
                    relocate_rounds=20, warning_active=False, warning_cap=WARNING_CAP):
    sim = Simulation(seed, forced_base, forced_a, forced_b,
                     warning_active=warning_active, warning_cap=warning_cap)
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
        sim.decay_screams()

    foll_reloc_cycles = sum(r[5] for r in relocate)

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
                scream = sim.get_scream_edge(pos, (nx, ny), resource)
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
                scream = sim.get_scream_edge(pos, (nx, ny), resource)
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

    foll_only_cycles = 0
    for r in range(NEW_RECALL_ROUNDS):
        res = sim.do_round(TRAIN_ROUNDS + relocate_rounds + r,
                          beacon_on=False, followers_only=True)
        foll_only_cycles += res[5]

    foll_rate = foll_only_cycles / (followers * NEW_RECALL_ROUNDS) if followers > 0 else 0

    sim.warning_cells = len(sim.dead_end_marks)
    sim.warning_strength_total = sum(sim.dead_end_marks.values())
    sim.warning_strength_max = max(sim.dead_end_marks.values()) if sim.dead_end_marks else 0.0

    sim.scream_edges_count = len(sim.scream_edges)
    sim.scream_strength_total = sum(sim.scream_edges.values())
    sim.scream_strength_max = max(sim.scream_edges.values()) if sim.scream_edges else 0.0

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
        "scream_edges": sim.scream_edges_count,
        "scream_strength_total": round(sim.scream_strength_total, 1),
        "scream_strength_max": round(sim.scream_strength_max, 1),
        "scream_written_total": round(sim.scream_written_total, 1),
        "pass": passed,
        "fail_reason": fail_reason
    }


def run_s10_2c_targeted():
    print("=" * 80)
    print("Natural Math v6.18-S10-2c — Scout+Audit Edge Scream Diagnostic")
    print("=" * 80)
    print()
    print("Config: 20x20, SCOUT_RATE=0.30, EDGE_DECAY=0.90, SCREAM_PENALTY=3.0")
    print()

    test_cases = [
        ("F1_close_original", 0, (0, 0), (9, 9), (5, 3)),
        ("F1_close_original", 5, (0, 0), (9, 9), (5, 3)),
        ("F3_close_corner", 5, (0, 0), (10, 10), (10, 0)),
    ]
    rounds = [5, 10, 20]

    results = []
    for fixture, seed, base, a, b in test_cases:
        for R in rounds:
            result = run_seed_s10_2c(seed, base, a, b,
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
                  f"ScreamE={result['scream_edges']:3d} | "
                  f"ScreamMx={result['scream_strength_max']:5.1f} | "
                  f"ScreamWrt={result['scream_written_total']:6.1f}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total = len(results)
    passed = sum(1 for _, _, _, r in results if r["pass"])
    print(f"Total passes: {passed}/{total}")
    print()
    print("S9B-4b baseline: All 9 cases = FAIL")
    print("S10-2a result:   All 9 cases = FAIL (cell scream too broad)")
    print()
    print("S10-2c interpretation:")
    print("  If AUDIT_OUT_FAIL -> PASS: edge-level conflict memory works")
    print("  If unchanged: edge placement not the issue, or strength too weak")
    print("  If NO_SCOUT_CYCLE: ignore — scream cannot fix no discovery")

    return results


if __name__ == "__main__":
    run_s10_2c_targeted()

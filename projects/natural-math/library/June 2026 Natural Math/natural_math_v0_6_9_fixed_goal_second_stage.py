"""
Natural Math v0.6.9 — Fixed Goal Memory + Second-Stage Transfer

Purpose
-------
Test memory over generations without moving the first resource.

Stage A:
    Same maze, same Resource A across generations.
    Agents start near the upper-left and search for Resource A.
    Successful Stage A paths are saved into a persistent Stage A memory ledger.

Stage B:
    After Resource A is found, agents are transported to a second-stage start area.
    They then search for fixed Resource B.
    Stage B has its own memory ledger, separate from Stage A.

This avoids mixing:
    - fixed-goal generational memory
    - moving-target adaptation
    - second-stage transfer

The test compares paired arms:
    1. No-memory control
    2. Memory arm

Same maze seed and same agent seed are used for both arms.
Only loaded memory differs.

Run:
    python natural_math_v0_6_9_fixed_goal_second_stage.py
"""

import csv
import random
from collections import defaultdict
from statistics import mean, median
from typing import Dict, List, Optional, Tuple


Position = Tuple[int, int]
Edge = Tuple[int, int, int, int]


BASE_PARAMS = {
    "num_agents": 15,
    "max_steps_stage_a": 30000,
    "max_steps_stage_b": 30000,
    "grid_width": 15,
    "grid_height": 15,
    "maze_type": "corridor",

    "curiosity_prob_ppm": 500000,
    "fallback_prob_ppm": 1000000,
    "gradient_weight": 50,
    "mark_sense_weight": 100,
    "mark_deposit": 1,
    "reinforcement_on_success": 100,
    "first_discovery_bonus": 500,
    "mark_decay_num": 5,
    "mark_decay_den": 8,
    "mark_max": 100000,
    "repulsion_max": -1500,
    "repulsion_weight": 200,
    "dead_end_penalty": -150,
    "reverse_trail_enabled": True,

    "memory_edge_bonus": 500,
    "memory_max_value": 100000,
    "memory_decay_num": 1,
    "memory_decay_den": 1,
    "memory_min_keep": 1,

    "random_start": True,
}


def generate_corridor_maze(width: int, height: int, rng: random.Random) -> List[List[int]]:
    if width % 2 == 0:
        width += 1
    if height % 2 == 0:
        height += 1

    grid = [[1 for _ in range(width)] for _ in range(height)]

    def carve(x: int, y: int) -> None:
        grid[y][x] = 0
        directions = [(0, -2), (0, 2), (-2, 0), (2, 0)]
        rng.shuffle(directions)
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 < nx < width - 1 and 0 < ny < height - 1 and grid[ny][nx] == 1:
                grid[y + dy // 2][x + dx // 2] = 0
                carve(nx, ny)

    carve(1, 1)
    return grid


def generate_open_grid(width: int, height: int) -> List[List[int]]:
    grid = [[0 for _ in range(width)] for _ in range(height)]
    for x in range(width):
        grid[0][x] = 1
        grid[height - 1][x] = 1
    for y in range(height):
        grid[y][0] = 1
        grid[y][width - 1] = 1
    return grid


def generate_test_maze(width: int, height: int, maze_type: str, rng: random.Random) -> List[List[int]]:
    if maze_type == "corridor":
        return generate_corridor_maze(width, height, rng)
    return generate_open_grid(width, height)


class MazeEnvironment:
    def __init__(self, params: Dict, maze_seed: int):
        self.params = params
        self.width = int(params["grid_width"])
        self.height = int(params["grid_height"])
        self.maze_rng = random.Random(maze_seed)

        self.grid = generate_test_maze(
            self.width,
            self.height,
            params.get("maze_type", "corridor"),
            self.maze_rng,
        )

        self.all_open_positions: List[Position] = []
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.grid[y][x] == 0:
                    self.all_open_positions.append((x, y))

        if not self.all_open_positions:
            raise ValueError("Maze has no open positions.")

        self.stage_a_starts = self._positions_in_region("top_left", min_count=3)
        self.stage_b_starts = self._positions_in_region("bottom_left", min_count=3)

        self.resource_a = self._pick_resource("bottom_right")
        self.resource_b = self._pick_resource("top_right")

        if self.resource_b == self.resource_a:
            candidates = [p for p in self.all_open_positions if p != self.resource_a]
            self.resource_b = candidates[-1] if candidates else self.resource_a

    def _positions_in_region(self, region: str, min_count: int) -> List[Position]:
        results: List[Position] = []

        for x, y in self.all_open_positions:
            if region == "top_left":
                ok = x < self.width // 3 and y < self.height // 3
            elif region == "bottom_left":
                ok = x < self.width // 3 and y > 2 * self.height // 3
            elif region == "top_right":
                ok = x > 2 * self.width // 3 and y < self.height // 3
            elif region == "bottom_right":
                ok = x > 2 * self.width // 3 and y > 2 * self.height // 3
            else:
                ok = True

            if ok:
                results.append((x, y))
                if len(results) >= min_count:
                    break

        if results:
            return results

        if region in ("top_left", "top_right"):
            return self.all_open_positions[:min_count]
        return self.all_open_positions[-min_count:]

    def _pick_resource(self, region: str) -> Position:
        for x, y in reversed(self.all_open_positions):
            if region == "bottom_right":
                ok = x > 2 * self.width // 3 and y > 2 * self.height // 3
            elif region == "top_right":
                ok = x > 2 * self.width // 3 and y < self.height // 3
            elif region == "bottom_left":
                ok = x < self.width // 3 and y > 2 * self.height // 3
            else:
                ok = True

            if ok:
                return (x, y)

        return self.all_open_positions[-1]

    def is_valid_move(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height and self.grid[y][x] == 0


class AntAgent:
    def __init__(self, agent_id: int, start_pos: Position):
        self.id = agent_id
        self.x, self.y = start_pos
        self.path_length = 0
        self.history: List[Position] = [start_pos]
        self.alive = True
        self.found_a = False
        self.found_b = False

    def get_position(self) -> Position:
        return (self.x, self.y)

    def move(self, dx: int, dy: int, env: MazeEnvironment) -> bool:
        nx, ny = self.x + dx, self.y + dy
        if env.is_valid_move(nx, ny):
            self.x, self.y = nx, ny
            self.path_length += 1
            self.history.append((self.x, self.y))
            return True
        return False

    def reset_to(self, start_pos: Position) -> None:
        self.x, self.y = start_pos
        self.path_length = 0
        self.history = [start_pos]
        self.found_b = False

    def path_edges(self) -> List[Tuple[Position, Position]]:
        if len(self.history) < 2:
            return []
        return [(self.history[i - 1], self.history[i]) for i in range(1, len(self.history))]

    def last_n_edges(self, n: int) -> List[Tuple[Position, Position]]:
        return self.path_edges()[-n:]


class StageMemoryLedger:
    def __init__(self, params: Dict, stage_name: str):
        self.params = params
        self.stage_name = stage_name
        self.marks: Dict[Edge, int] = defaultdict(int)
        self.confirmations: Dict[Edge, int] = defaultdict(int)

    def add_success_path(self, path_edges: List[Tuple[Position, Position]]) -> None:
        bonus = int(self.params.get("memory_edge_bonus", 500))
        cap = int(self.params.get("memory_max_value", 100000))

        for from_pos, to_pos in path_edges:
            edge = (from_pos[0], from_pos[1], to_pos[0], to_pos[1])
            rev = (to_pos[0], to_pos[1], from_pos[0], from_pos[1])

            self.confirmations[edge] += 1
            self.confirmations[rev] += 1

            self.marks[edge] = min(cap, self.marks.get(edge, 0) + bonus)
            self.marks[rev] = min(cap, self.marks.get(rev, 0) + bonus)

    def decay_between_generations(self) -> None:
        num = int(self.params.get("memory_decay_num", 1))
        den = int(self.params.get("memory_decay_den", 1))
        keep = int(self.params.get("memory_min_keep", 1))

        if den <= 0:
            raise ValueError("memory_decay_den must be positive.")

        new_marks: Dict[Edge, int] = defaultdict(int)
        new_conf: Dict[Edge, int] = defaultdict(int)

        for edge, value in self.marks.items():
            new_value = int(value * num / den)
            if new_value >= keep:
                new_marks[edge] = new_value
                new_conf[edge] = self.confirmations.get(edge, 0)

        self.marks = new_marks
        self.confirmations = new_conf

    def loadable_marks(self) -> Dict[Edge, int]:
        return dict(self.marks)

    def stats(self) -> Dict:
        return {
            f"{self.stage_name}_memory_edges": len(self.marks),
            f"{self.stage_name}_memory_mass": sum(self.marks.values()),
            f"{self.stage_name}_confirmations": sum(self.confirmations.values()),
        }


class AntTrailSimulation:
    def __init__(
        self,
        params: Dict,
        maze_seed: int,
        agent_seed: int,
        stage_a_memory: Optional[Dict[Edge, int]] = None,
        stage_b_memory: Optional[Dict[Edge, int]] = None,
    ):
        self.params = dict(params)
        self.maze_seed = maze_seed
        self.agent_seed = agent_seed
        self.agent_rng = random.Random(agent_seed)
        self.env = MazeEnvironment(self.params, maze_seed)

        self.edge_marks: Dict[Edge, int] = defaultdict(int)
        self.stage_a_memory = stage_a_memory or {}
        self.stage_b_memory = stage_b_memory or {}

        self.step_count = 0
        self.stage = "A"
        self.stage_a_step: Optional[int] = None
        self.stage_b_step: Optional[int] = None
        self.stage_a_path_edges: List[Tuple[Position, Position]] = []
        self.stage_b_path_edges: List[Tuple[Position, Position]] = []
        self.memory_moves_a = 0
        self.memory_moves_b = 0
        self.unique_cells_a = set()
        self.unique_cells_b = set()

        self.agents: List[AntAgent] = []
        self._init_agents_for_stage_a()

    def _init_agents_for_stage_a(self) -> None:
        starts = self.env.stage_a_starts
        self.agents = []
        for i in range(int(self.params["num_agents"])):
            pos = self.agent_rng.choice(starts) if self.params.get("random_start", True) else starts[i % len(starts)]
            self.agents.append(AntAgent(i, pos))

    def _transport_agents_to_stage_b(self) -> None:
        starts = self.env.stage_b_starts
        for i, agent in enumerate(self.agents):
            pos = self.agent_rng.choice(starts) if self.params.get("random_start", True) else starts[i % len(starts)]
            agent.reset_to(pos)
        self.stage = "B"
        self.edge_marks = defaultdict(int)

    def _target_for_stage(self) -> Position:
        return self.env.resource_a if self.stage == "A" else self.env.resource_b

    def _memory_for_stage(self) -> Dict[Edge, int]:
        return self.stage_a_memory if self.stage == "A" else self.stage_b_memory

    def deposit_mark(self, from_pos: Position, to_pos: Position, amount: int) -> None:
        edge = (from_pos[0], from_pos[1], to_pos[0], to_pos[1])
        value = self.edge_marks.get(edge, 0) + amount
        value = min(value, int(self.params["mark_max"]))
        value = max(value, int(self.params["repulsion_max"]))
        self.edge_marks[edge] = value

    def deposit_forward_and_reverse(self, from_pos: Position, to_pos: Position, amount: int) -> None:
        self.deposit_mark(from_pos, to_pos, amount)
        self.deposit_mark(to_pos, from_pos, amount)

    def get_gradient_dir(self, agent: AntAgent) -> Tuple[int, int]:
        tx, ty = self._target_for_stage()
        dx = tx - agent.x
        dy = ty - agent.y
        if dx == 0 and dy == 0:
            return (0, 0)
        if abs(dx) >= abs(dy):
            return (1 if dx > 0 else -1, 0)
        return (0, 1 if dy > 0 else -1)

    def _decay_short_term_marks(self) -> None:
        num = int(self.params["mark_decay_num"])
        den = int(self.params["mark_decay_den"])
        new_marks: Dict[Edge, int] = defaultdict(int)

        for edge, value in self.edge_marks.items():
            new_value = int(value * num / den)
            if new_value != 0:
                new_marks[edge] = new_value

        self.edge_marks = new_marks

    def step(self) -> None:
        self.step_count += 1
        self._decay_short_term_marks()

        target = self._target_for_stage()
        memory = self._memory_for_stage()

        for agent in self.agents:
            if not agent.alive:
                continue

            pos = agent.get_position()
            if self.stage == "A":
                self.unique_cells_a.add(pos)
            else:
                self.unique_cells_b.add(pos)

            if pos == target:
                if self.stage == "A" and not agent.found_a:
                    agent.found_a = True
                    if self.stage_a_step is None:
                        self.stage_a_step = self.step_count
                        self.stage_a_path_edges = agent.path_edges()
                        for edge_from, edge_to in agent.last_n_edges(5):
                            self.deposit_forward_and_reverse(edge_from, edge_to, int(self.params["reinforcement_on_success"]))
                        self._transport_agents_to_stage_b()
                        return

                elif self.stage == "B" and not agent.found_b:
                    agent.found_b = True
                    if self.stage_b_step is None:
                        self.stage_b_step = self.step_count
                        self.stage_b_path_edges = agent.path_edges()
                        for edge_from, edge_to in agent.last_n_edges(5):
                            self.deposit_forward_and_reverse(edge_from, edge_to, int(self.params["reinforcement_on_success"]))
                        return
                continue

            curiosity_prob = int(self.params.get("curiosity_prob_ppm", 500000))
            if self.agent_rng.randrange(1000000) < curiosity_prob:
                dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                valid = [(dx, dy) for dx, dy in dirs if self.env.is_valid_move(agent.x + dx, agent.y + dy)]
                if valid:
                    dx, dy = self.agent_rng.choice(valid)
                    if agent.move(dx, dy, self.env):
                        self.deposit_forward_and_reverse(agent.history[-2], agent.history[-1], int(self.params["mark_deposit"]))
                continue

            gradient_dir = self.get_gradient_dir(agent)
            gx, gy = gradient_dir
            gradient_valid = self.env.is_valid_move(agent.x + gx, agent.y + gy) and (gx != 0 or gy != 0)

            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            best_dir: Optional[Tuple[int, int]] = None
            best_score = -10**12

            for dx, dy in dirs:
                nx, ny = agent.x + dx, agent.y + dy
                if not self.env.is_valid_move(nx, ny):
                    continue

                edge = (agent.x, agent.y, nx, ny)
                short_mark = self.edge_marks.get(edge, 0)
                long_mark = memory.get(edge, 0)

                if short_mark > 0:
                    mark_score = short_mark * int(self.params["mark_sense_weight"])
                elif short_mark < 0:
                    mark_score = short_mark * int(self.params["repulsion_weight"])
                else:
                    mark_score = 0

                memory_score = long_mark * int(self.params["mark_sense_weight"])

                if gradient_valid:
                    alignment = dx * gx + dy * gy
                    grad_score = max(0, alignment) * 1000 if alignment >= 0 else 0
                else:
                    grad_score = 0

                grad_weight = float(self.params.get("gradient_weight", 50)) / 100.0
                total = grad_weight * grad_score + (1.0 - grad_weight) * (mark_score + memory_score)

                if total > best_score:
                    best_score = total
                    best_dir = (dx, dy)

            if best_dir is not None:
                dx, dy = best_dir
                old_pos = agent.get_position()
                if agent.move(dx, dy, self.env):
                    new_pos = agent.get_position()
                    edge = (old_pos[0], old_pos[1], new_pos[0], new_pos[1])
                    if memory.get(edge, 0) > 0:
                        if self.stage == "A":
                            self.memory_moves_a += 1
                        else:
                            self.memory_moves_b += 1
                    self.deposit_forward_and_reverse(old_pos, new_pos, int(self.params["mark_deposit"]))
            else:
                if self.agent_rng.randrange(1000000) < int(self.params.get("fallback_prob_ppm", 1000000)):
                    valid = [(dx, dy) for dx, dy in dirs if self.env.is_valid_move(agent.x + dx, agent.y + dy)]
                    if valid:
                        dx, dy = self.agent_rng.choice(valid)
                        if agent.move(dx, dy, self.env):
                            self.deposit_forward_and_reverse(agent.history[-2], agent.history[-1], int(self.params["mark_deposit"]))

    def run(self) -> Dict:
        max_total_steps = int(self.params["max_steps_stage_a"]) + int(self.params["max_steps_stage_b"])

        for _ in range(max_total_steps):
            self.step()
            if self.stage_a_step is not None and self.stage_b_step is not None:
                break
            if self.stage == "A" and self.step_count >= int(self.params["max_steps_stage_a"]):
                break
            if self.stage == "B" and self.stage_a_step is not None:
                if self.step_count - self.stage_a_step >= int(self.params["max_steps_stage_b"]):
                    break

        stage_b_relative_step = None
        if self.stage_a_step is not None and self.stage_b_step is not None:
            stage_b_relative_step = self.stage_b_step - self.stage_a_step

        return {
            "stage_a_success": self.stage_a_step is not None,
            "stage_a_step": self.stage_a_step,
            "stage_b_success": self.stage_b_step is not None,
            "stage_b_step": stage_b_relative_step,
            "stage_a_path_edges": self.stage_a_path_edges,
            "stage_b_path_edges": self.stage_b_path_edges,
            "memory_moves_a": self.memory_moves_a,
            "memory_moves_b": self.memory_moves_b,
            "unique_cells_a": len(self.unique_cells_a),
            "unique_cells_b": len(self.unique_cells_b),
            "resource_a": self.env.resource_a,
            "resource_b": self.env.resource_b,
        }


def safe_mean(values: List[int]) -> Optional[float]:
    return mean(values) if values else None


def safe_median(values: List[int]) -> Optional[float]:
    return median(values) if values else None


def format_num(value: Optional[float]) -> str:
    if value is None:
        return "--"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def run_one_maze(maze_seed: int, num_generations: int, params: Dict) -> Dict:
    memory_a = StageMemoryLedger(params, "A")
    memory_b = StageMemoryLedger(params, "B")

    memory_rows: List[Dict] = []
    control_rows: List[Dict] = []

    for gen in range(num_generations):
        agent_seed = maze_seed * 10000 + gen

        sim_control = AntTrailSimulation(params, maze_seed, agent_seed, None, None)
        control = sim_control.run()

        sim_memory = AntTrailSimulation(
            params,
            maze_seed,
            agent_seed,
            memory_a.loadable_marks(),
            memory_b.loadable_marks(),
        )
        mem = sim_memory.run()

        if mem["stage_a_success"]:
            memory_a.add_success_path(mem["stage_a_path_edges"])
        if mem["stage_b_success"]:
            memory_b.add_success_path(mem["stage_b_path_edges"])

        memory_a.decay_between_generations()
        memory_b.decay_between_generations()

        mem.update({
            "maze_seed": maze_seed,
            "generation": gen,
            **memory_a.stats(),
            **memory_b.stats(),
        })
        control.update({
            "maze_seed": maze_seed,
            "generation": gen,
        })

        memory_rows.append(mem)
        control_rows.append(control)

    return {"maze_seed": maze_seed, "memory": memory_rows, "control": control_rows}


def run_experiment(
    num_mazes: int = 10,
    num_generations: int = 10,
    params: Optional[Dict] = None,
    csv_path: str = "natural_math_v0_6_9_results.csv",
) -> List[Dict]:
    active_params = dict(BASE_PARAMS)
    if params:
        active_params.update(params)

    all_results: List[Dict] = []

    print("=" * 70)
    print("Natural Math v0.6.9 — Fixed Goal Memory + Second-Stage Transfer")
    print("=" * 70)
    print(f"Mazes: {num_mazes}")
    print(f"Generations per maze: {num_generations}")
    print("Stage A: fixed Resource A")
    print("Stage B: transport after A, then fixed Resource B")
    print("=" * 70)

    for maze_seed in range(num_mazes):
        print(f"Running maze {maze_seed}...")
        all_results.append(run_one_maze(maze_seed, num_generations, active_params))

    print("\n=== Summary by Generation ===")
    print(
        "Gen\t"
        "A_MemSucc\tA_CtrlSucc\tA_MemMed\tA_CtrlMed\tA_Speed\t"
        "B_MemSucc\tB_CtrlSucc\tB_MemMed\tB_CtrlMed\tB_Speed\t"
        "A_MemMoves\tB_MemMoves"
    )

    for gen in range(num_generations):
        mem_rows = [r["memory"][gen] for r in all_results]
        ctrl_rows = [r["control"][gen] for r in all_results]

        a_mem_steps = [r["stage_a_step"] for r in mem_rows if r["stage_a_success"]]
        a_ctrl_steps = [r["stage_a_step"] for r in ctrl_rows if r["stage_a_success"]]

        b_mem_steps = [r["stage_b_step"] for r in mem_rows if r["stage_b_success"]]
        b_ctrl_steps = [r["stage_b_step"] for r in ctrl_rows if r["stage_b_success"]]

        a_mem_mean = safe_mean(a_mem_steps)
        a_ctrl_mean = safe_mean(a_ctrl_steps)
        b_mem_mean = safe_mean(b_mem_steps)
        b_ctrl_mean = safe_mean(b_ctrl_steps)

        a_speed = (a_ctrl_mean / a_mem_mean) if a_mem_mean and a_ctrl_mean else None
        b_speed = (b_ctrl_mean / b_mem_mean) if b_mem_mean and b_ctrl_mean else None

        a_mem_moves = sum(r["memory_moves_a"] for r in mem_rows)
        b_mem_moves = sum(r["memory_moves_b"] for r in mem_rows)

        print(
            f"{gen}\t"
            f"{len(a_mem_steps)}/{num_mazes}\t{len(a_ctrl_steps)}/{num_mazes}\t"
            f"{format_num(safe_median(a_mem_steps))}\t{format_num(safe_median(a_ctrl_steps))}\t{format_num(a_speed)}\t"
            f"{len(b_mem_steps)}/{num_mazes}\t{len(b_ctrl_steps)}/{num_mazes}\t"
            f"{format_num(safe_median(b_mem_steps))}\t{format_num(safe_median(b_ctrl_steps))}\t{format_num(b_speed)}\t"
            f"{a_mem_moves}\t{b_mem_moves}"
        )

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "maze_seed",
            "generation",
            "arm",
            "stage_a_success",
            "stage_a_step",
            "stage_b_success",
            "stage_b_step_after_a",
            "memory_moves_a",
            "memory_moves_b",
            "unique_cells_a",
            "unique_cells_b",
            "resource_a",
            "resource_b",
            "A_memory_edges",
            "A_memory_mass",
            "A_confirmations",
            "B_memory_edges",
            "B_memory_mass",
            "B_confirmations",
        ])

        for result in all_results:
            for arm_name in ("control", "memory"):
                for row in result[arm_name]:
                    writer.writerow([
                        row["maze_seed"],
                        row["generation"],
                        arm_name,
                        row["stage_a_success"],
                        row["stage_a_step"] if row["stage_a_success"] else "",
                        row["stage_b_success"],
                        row["stage_b_step"] if row["stage_b_success"] else "",
                        row.get("memory_moves_a", 0),
                        row.get("memory_moves_b", 0),
                        row.get("unique_cells_a", 0),
                        row.get("unique_cells_b", 0),
                        row.get("resource_a", ""),
                        row.get("resource_b", ""),
                        row.get("A_memory_edges", ""),
                        row.get("A_memory_mass", ""),
                        row.get("A_confirmations", ""),
                        row.get("B_memory_edges", ""),
                        row.get("B_memory_mass", ""),
                        row.get("B_confirmations", ""),
                    ])

    print(f"\nSaved CSV: {csv_path}")
    return all_results


if __name__ == "__main__":
    run_experiment(
        num_mazes=10,
        num_generations=10,
        csv_path="natural_math_v0_6_9_results.csv",
    )

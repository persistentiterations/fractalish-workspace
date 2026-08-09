"""
Natural Math v0.6.7 — Generational Accumulation (Paired Control)
Separate maze/agent RNG, long-term memory ledger, paired memory vs no-memory.
"""

import random
from typing import List, Tuple, Dict, Optional
from collections import defaultdict
import csv

# =============================================================================
# Parameters
# =============================================================================

BASE_PARAMS = {
    'num_agents': 15,
    'max_steps': 30000,
    'grid_width': 15,
    'grid_height': 15,
    'reverse_trail_enabled': True,
    'reinforcement_on_success': 100,
    'curiosity_prob_ppm': 500000,
    'mark_sense_weight': 100,
    'first_discovery_bonus': 500,
    'mark_decay_num': 5,
    'mark_decay_den': 8,
    'dead_end_penalty': -150,
    'repulsion_max': -1500,
    'repulsion_weight': 200,
    'relocate_resource': False,
    'mark_deposit': 1,
    'mark_max': 100000,
    'gradient_weight': 50,
    'maze_type': 'corridor',
    'fallback_prob_ppm': 1000000,
    'random_start': True,
}

# =============================================================================
# Maze Generation
# =============================================================================

def generate_corridor_maze(width: int, height: int, rng: random.Random) -> List[List[int]]:
    if width % 2 == 0:
        width += 1
    if height % 2 == 0:
        height += 1
    grid = [[1 for _ in range(width)] for _ in range(height)]

    def carve(x: int, y: int):
        grid[y][x] = 0
        dirs = [(0, -2), (0, 2), (-2, 0), (2, 0)]
        rng.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if 0 < nx < width - 1 and 0 < ny < height - 1 and grid[ny][nx] == 1:
                grid[y + dy // 2][x + dx // 2] = 0
                carve(nx, ny)

    carve(1, 1)
    grid[1][1] = 0
    grid[height - 2][width - 2] = 0
    return grid

def generate_test_maze(width: int, height: int, maze_type: str, rng: random.Random) -> List[List[int]]:
    if maze_type == "corridor":
        return generate_corridor_maze(width, height, rng)
    # fallback: open grid with borders
    grid = [[0 for _ in range(width)] for _ in range(height)]
    for x in range(width):
        grid[0][x] = 1
        grid[height - 1][x] = 1
    for y in range(height):
        grid[y][0] = 1
        grid[y][width - 1] = 1
    return grid

# =============================================================================
# Environment
# =============================================================================

class MazeEnvironment:
    def __init__(self, params: Dict, maze_rng: random.Random):
        self.width = params['grid_width']
        self.height = params['grid_height']
        self.grid = generate_test_maze(self.width, self.height,
                                       params.get('maze_type', 'corridor'),
                                       maze_rng)
        # Find open positions
        self.all_open_positions = []
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.grid[y][x] == 0:
                    self.all_open_positions.append((x, y))

        # Choose start positions (in the top-left area)
        self.start_positions = []
        for x, y in self.all_open_positions:
            if x < self.width // 3 and y < self.height // 3:
                self.start_positions.append((x, y))
                if len(self.start_positions) >= 3:
                    break
        if not self.start_positions:
            self.start_positions = self.all_open_positions[:min(3, len(self.all_open_positions))]

        # Choose resource position (in the bottom-right area)
        self.resource_positions = []
        for x, y in reversed(self.all_open_positions):
            if x > 2 * self.width // 3 and y > 2 * self.height // 3:
                self.resource_positions.append((x, y))
                if len(self.resource_positions) >= 1:
                    break
        if not self.resource_positions:
            self.resource_positions = [self.all_open_positions[-1]]

        self.old_resource_pos = None

    def is_valid_move(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height and self.grid[y][x] == 0

# =============================================================================
# Agent (no RNG inside)
# =============================================================================

class AntAgent:
    def __init__(self, agent_id: int, start_pos: Tuple[int, int]):
        self.id = agent_id
        self.x, self.y = start_pos
        self.path_length = 0
        self.found_initial = False
        self.found_relocated = False
        self.steps_since_resource = 0
        self.history = [(self.x, self.y)]
        self.alive = True

    def get_position(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def move(self, dx: int, dy: int, env: MazeEnvironment) -> bool:
        if env.is_valid_move(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
            self.path_length += 1
            self.history.append((self.x, self.y))
            return True
        return False

    def get_last_n_edges(self, n: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        if len(self.history) < 2:
            return []
        edges = []
        for i in range(1, min(n + 1, len(self.history))):
            edges.append((self.history[-i - 1], self.history[-i]))
        return edges

# =============================================================================
# Simulation
# =============================================================================

class AntTrailSimulation:
    def __init__(self, params: Dict, maze_rng: random.Random, agent_rng: random.Random,
                 load_marks: Optional[Dict] = None):
        self.params = params
        self.maze_rng = maze_rng
        self.agent_rng = agent_rng

        self.env = MazeEnvironment(params, maze_rng)

        self.edge_marks = defaultdict(int)
        if load_marks:
            for (fx, fy, tx, ty), val in load_marks.items():
                self.edge_marks[(fx, fy, tx, ty)] = val

        self.step_count = 0
        self.first_discovery_step = None
        self.first_success_path_edges = []
        self.relocation_step = None
        self.second_discovery_step = None
        self.resource_relocated = False
        self.relocation_triggered = False
        self.relocation_delay_target = 0
        self.first_discovery_deposited = False
        self.curiosity_surge_active = False
        self.curiosity_surge_end_step = 0

        self._init_agents()

    def _init_agents(self):
        num_agents = self.params['num_agents']
        start_positions = self.env.start_positions[:]
        if not start_positions:
            # fallback
            start_positions = [(1,1)]
        self.agents = []
        for i in range(num_agents):
            if self.params.get('random_start', True):
                pos = self.agent_rng.choice(start_positions)
            else:
                pos = start_positions[i % len(start_positions)]
            self.agents.append(AntAgent(i, pos))

    def deposit_mark(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int], amount: int):
        edge_key = (from_pos[0], from_pos[1], to_pos[0], to_pos[1])
        new_val = self.edge_marks.get(edge_key, 0) + amount
        new_val = min(new_val, self.params['mark_max'])
        new_val = max(new_val, self.params['repulsion_max'])
        self.edge_marks[edge_key] = new_val

    def deposit_forward_and_reverse(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int], amount: int):
        self.deposit_mark(from_pos, to_pos, amount)
        self.deposit_mark(to_pos, from_pos, amount)

    def get_gradient_dir(self, agent: AntAgent) -> Tuple[int, int]:
        if not self.env.resource_positions:
            return (0, 0)
        rx, ry = self.env.resource_positions[0]
        dx = rx - agent.x
        dy = ry - agent.y
        if dx == 0 and dy == 0:
            return (0, 0)
        if abs(dx) >= abs(dy):
            return (1 if dx > 0 else -1, 0)
        else:
            return (0, 1 if dy > 0 else -1)

    def step(self):
        self.step_count += 1

        # Decay marks
        new_marks = defaultdict(int)
        num = self.params['mark_decay_num']
        den = self.params['mark_decay_den']
        for (fx, fy, tx, ty), val in self.edge_marks.items():
            new_val = int(val * num / den)
            if new_val != 0:
                new_marks[(fx, fy, tx, ty)] = new_val
        self.edge_marks = new_marks

        # Move each agent
        for agent in self.agents:
            if not agent.alive:
                continue

            # Check if at resource
            if agent.get_position() in self.env.resource_positions:
                if not agent.found_initial:
                    agent.found_initial = True
                    # Record first discovery if not already recorded
                    if self.first_discovery_step is None:
                        self.first_discovery_step = self.step_count
                        # Capture the path edges
                        if len(agent.history) >= 2:
                            for i in range(1, len(agent.history)):
                                self.first_success_path_edges.append((agent.history[i-1], agent.history[i]))
                        # Deposit bonus along the path (short-term)
                        for from_pos, to_pos in agent.get_last_n_edges(5):
                            self.deposit_forward_and_reverse(from_pos, to_pos,
                                                             self.params['reinforcement_on_success'])
                    # Mark the agent as having found it
                agent.steps_since_resource = 0
                continue
            else:
                agent.steps_since_resource += 1

            # Curiosity
            curiosity_prob = self.params.get('curiosity_prob_ppm', 500000)
            if self.curiosity_surge_active:
                curiosity_prob = self.params.get('curiosity_surge_ppm', 800000)

            if self.agent_rng.randrange(1000000) < curiosity_prob:
                directions = [(1,0),(-1,0),(0,1),(0,-1)]
                valid = [d for d in directions if self.env.is_valid_move(agent.x + d[0], agent.y + d[1])]
                if valid:
                    dx, dy = self.agent_rng.choice(valid)
                    moved = agent.move(dx, dy, self.env)
                    if moved:
                        self.deposit_forward_and_reverse(agent.history[-2], agent.history[-1],
                                                         self.params['mark_deposit'])
                continue

            # Gradient + marks
            gradient_dir = self.get_gradient_dir(agent)
            gx, gy = gradient_dir
            gradient_valid = self.env.is_valid_move(agent.x + gx, agent.y + gy) and (gx != 0 or gy != 0)

            directions = [(1,0),(-1,0),(0,1),(0,-1)]
            scores = {}
            for dx, dy in directions:
                tx, ty = agent.x + dx, agent.y + dy
                if self.env.is_valid_move(tx, ty):
                    edge_key = (agent.x, agent.y, tx, ty)
                    mark_val = self.edge_marks.get(edge_key, 0)
                    if mark_val > 0:
                        scores[(dx,dy)] = mark_val * self.params.get('mark_sense_weight', 100)
                    elif mark_val < 0:
                        scores[(dx,dy)] = mark_val * self.params.get('repulsion_weight', 200)
                    else:
                        scores[(dx,dy)] = 0
                else:
                    scores[(dx,dy)] = -1e9

            grad_weight = self.params.get('gradient_weight', 50) / 100.0
            best_dir = None
            best_score = -1e9
            for (dx, dy), score in scores.items():
                if score < -1e8:
                    continue
                if gradient_valid:
                    alignment = dx * gx + dy * gy
                    grad_score = max(0, alignment) * 1000 if alignment >= 0 else 0
                else:
                    grad_score = 0
                total_score = grad_weight * grad_score + (1 - grad_weight) * score
                if total_score > best_score:
                    best_score = total_score
                    best_dir = (dx, dy)

            moved = False
            if best_dir is not None:
                dx, dy = best_dir
                if self.env.is_valid_move(agent.x + dx, agent.y + dy):
                    moved = agent.move(dx, dy, self.env)
                    if moved:
                        self.deposit_forward_and_reverse(agent.history[-2], agent.history[-1],
                                                         self.params['mark_deposit'])
                else:
                    # blocked attempt – maybe deposit a repulsion mark
                    edge_key = (agent.x, agent.y, agent.x + dx, agent.y + dy)
                    if self.edge_marks.get(edge_key, 0) > self.params['repulsion_max']:
                        self.deposit_mark((agent.x, agent.y), (agent.x + dx, agent.y + dy),
                                          self.params.get('dead_end_penalty', -150))
            else:
                # fallback random move
                if self.agent_rng.randrange(1000000) < self.params.get('fallback_prob_ppm', 1000000):
                    valid = [d for d in directions if self.env.is_valid_move(agent.x + d[0], agent.y + d[1])]
                    if valid:
                        dx, dy = self.agent_rng.choice(valid)
                        moved = agent.move(dx, dy, self.env)
                        if moved:
                            self.deposit_forward_and_reverse(agent.history[-2], agent.history[-1],
                                                             self.params['mark_deposit'])

        # (surge deactivation handled outside if needed)

    def run(self, max_steps: Optional[int] = None, stop_at_first_discovery: bool = True):
        if max_steps is None:
            max_steps = self.params['max_steps']
        self.step_count = 0
        self.first_discovery_step = None
        self.first_success_path_edges = []
        for _ in range(max_steps):
            self.step()
            if stop_at_first_discovery and self.first_discovery_step is not None:
                break
        return {
            'success': self.first_discovery_step is not None,
            'first_discovery_step': self.first_discovery_step,
            'path_edges': self.first_success_path_edges,
            'final_edge_marks': dict(self.edge_marks),
        }

# =============================================================================
# Generational Test (Paired)
# =============================================================================

def run_generational_paired(maze_seed: int, num_generations: int = 10, max_steps: int = 30000):
    """
    For one maze, run paired memory and no-memory arms.
    Returns a dictionary with results per generation.
    """
    # Create a maze RNG (deterministic for this maze)
    maze_rng = random.Random(maze_seed)

    # Long-term memory ledger (accumulated deposits from successful paths)
    long_term_memory = defaultdict(int)

    memory_results = []
    no_memory_results = []

    for gen in range(num_generations):
        # Agent seed = maze_seed * 1000 + gen (deterministic per generation)
        agent_seed = maze_seed * 1000 + gen
        agent_rng = random.Random(agent_seed)

        # ---- Memory arm ----
        sim_mem = AntTrailSimulation(BASE_PARAMS, maze_rng, agent_rng, load_marks=long_term_memory)
        res_mem = sim_mem.run(max_steps, stop_at_first_discovery=True)
        if res_mem['success']:
            # Add the successful path edges to long-term memory (undecayed)
            for from_pos, to_pos in res_mem['path_edges']:
                # Deposit a strong bonus (first_discovery_bonus) both directions
                edge_key = (from_pos[0], from_pos[1], to_pos[0], to_pos[1])
                long_term_memory[edge_key] += BASE_PARAMS['first_discovery_bonus']
                rev_key = (to_pos[0], to_pos[1], from_pos[0], from_pos[1])
                long_term_memory[rev_key] += BASE_PARAMS['first_discovery_bonus']
        memory_results.append(res_mem)

        # ---- No-memory arm ----
        # Use the same agent_rng but with empty load_marks
        sim_none = AntTrailSimulation(BASE_PARAMS, maze_rng, agent_rng, load_marks=None)
        res_none = sim_none.run(max_steps, stop_at_first_discovery=True)
        no_memory_results.append(res_none)

    return {
        'maze_seed': maze_seed,
        'memory': memory_results,
        'no_memory': no_memory_results,
        'long_term_edges': len(long_term_memory),
        'long_term_mass': sum(long_term_memory.values()),
    }

def run_generational_sweep(num_mazes: int = 10, num_generations: int = 10, max_steps: int = 30000):
    all_results = []
    for m in range(num_mazes):
        print(f"Running maze {m}...")
        res = run_generational_paired(m, num_generations, max_steps)
        all_results.append(res)

    # Print summary table
    print("\n=== Generational Summary (averaged over mazes) ===")
    print("Gen\tMemSuccess\tNoMemSuccess\tMemMedian\tNoMemMedian\tMemMean\tNoMemMean\tSpeedup")
    for gen in range(num_generations):
        mem_success = sum(1 for r in all_results if r['memory'][gen]['success'])
        none_success = sum(1 for r in all_results if r['no_memory'][gen]['success'])

        mem_steps = [r['memory'][gen]['first_discovery_step'] for r in all_results if r['memory'][gen]['success']]
        none_steps = [r['no_memory'][gen]['first_discovery_step'] for r in all_results if r['no_memory'][gen]['success']]

        mem_med = sorted(mem_steps)[len(mem_steps)//2] if mem_steps else None
        none_med = sorted(none_steps)[len(none_steps)//2] if none_steps else None
        mem_mean = sum(mem_steps)/len(mem_steps) if mem_steps else None
        none_mean = sum(none_steps)/len(none_steps) if none_steps else None
        speedup = none_mean / mem_mean if (mem_mean and none_mean and mem_mean>0) else None

        print(f"{gen}\t{mem_success}/{num_mazes}\t{none_success}/{num_mazes}\t"
              f"{mem_med}\t{none_med}\t"
              f"{mem_mean:.1f if mem_mean else '--'}\t"
              f"{none_mean:.1f if none_mean else '--'}\t"
              f"{speedup:.2f if speedup else '--'}")

    # Save detailed CSV
    with open('generational_paired_results.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['maze_seed', 'generation', 'memory_step', 'memory_success',
                         'no_memory_step', 'no_memory_success'])
        for r in all_results:
            for gen in range(num_generations):
                writer.writerow([
                    r['maze_seed'],
                    gen,
                    r['memory'][gen]['first_discovery_step'] if r['memory'][gen]['success'] else '',
                    r['memory'][gen]['success'],
                    r['no_memory'][gen]['first_discovery_step'] if r['no_memory'][gen]['success'] else '',
                    r['no_memory'][gen]['success'],
                ])

if __name__ == "__main__":
    print("=" * 60)
    print("Natural Math v0.6.7 — Generational Accumulation (Paired Control)")
    print("=" * 60)
    print("Testing whether accumulated trail knowledge speeds up discovery.")
    print("Memory arm inherits marks from all previous successful generations.")
    print("No-memory arm starts fresh each generation (same maze & agent seeds).")
    print("=" * 60)
    run_generational_sweep(num_mazes=10, num_generations=10)
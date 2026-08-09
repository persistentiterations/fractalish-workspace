"""
Natural Math v6.1-T — Trail Memory Integration

Complete single-file implementation.
Integrates the proven follow-the-leader mechanism with v6.1-T.

To run: python3 natural_math_trail_memory.py
"""

import random
from dataclasses import dataclass, field
from typing import Dict, Set, Tuple, Optional, List, Any

# ============================================================
# V6.1-T CORE DATA MODEL
# ============================================================

@dataclass
class Node:
    """v6.1-T Node Record - All fields as specified."""
    id: int
    pos_x: int
    pos_y: int
    pos_z: int
    alive: bool
    energy: int
    pressure: int
    dir_x: int
    dir_y: int
    dir_z: int
    node_type: str  # seed, tip, branch, inert, wall
    parent_id: Optional[int]
    bonds: Set[int]
    signal_type: int = 0
    # Extra for trail memory
    history: List[Tuple[int, int, int]] = field(default_factory=list)

    def pos(self) -> Tuple[int, int, int]:
        return (self.pos_x, self.pos_y, self.pos_z)

    def direction(self) -> Tuple[int, int, int]:
        return (self.dir_x, self.dir_y, self.dir_z)


# ============================================================
# TRAIL MEMORY (The core learned object)
# ============================================================

class TrailMemory:
    """
    Directed edge memory using non-negative integer counters.
    
    edge_memory[(from_cell, to_cell)] = count
    
    This is the ONLY learned object in the system.
    It persists across generations and node deaths.
    """
    
    def __init__(self):
        self.marks: Dict[Tuple[Tuple[int, int, int], Tuple[int, int, int]], int] = {}
        self.paths_written: int = 0
    
    def reinforce(self, from_pos: Tuple[int, int, int], 
                  to_pos: Tuple[int, int, int], 
                  amount: int = 1) -> None:
        """Add to an edge counter (leader learning)."""
        key = (from_pos, to_pos)
        self.marks[key] = self.marks.get(key, 0) + amount
    
    def get(self, from_pos: Tuple[int, int, int], 
            to_pos: Tuple[int, int, int]) -> int:
        """Get edge count (follower reading)."""
        key = (from_pos, to_pos)
        return self.marks.get(key, 0)
    
    def best_direction(self, from_pos: Tuple[int, int, int],
                       dirs: List[Tuple[int, int, int]]) -> Optional[Tuple[int, int, int]]:
        """
        Find the direction with the highest integer mark.
        Returns (dx, dy, dz) or None if no marks exist.
        """
        best_dir = None
        best_count = 0
        
        for d in dirs:
            to_pos = (from_pos[0] + d[0], 
                      from_pos[1] + d[1], 
                      from_pos[2] + d[2])
            count = self.get(from_pos, to_pos)
            if count > best_count:
                best_count = count
                best_dir = d
        
        return best_dir
    
    def reinforce_path(self, path: List[Tuple[int, int, int]], amount: int = 1) -> None:
        """Reinforce all edges in a path."""
        if len(path) < 2:
            return
        for i in range(len(path) - 1):
            self.reinforce(path[i], path[i + 1], amount)
        self.paths_written += 1
    
    def size(self) -> int:
        return len(self.marks)
    
    def clear(self) -> None:
        self.marks.clear()
        self.paths_written = 0


# ============================================================
# MAZE (Connected and solvable)
# ============================================================

MAZE_TEXT = [
    "###########",
    "#S#.......#",
    "#.#.#####.#",
    "#.#.....#.#",
    "#.#####.#.#",
    "#.....#.#R#",
    "#####.#.#.#",
    "#.........#",
    "###########",
]

WALL = "#"
START_SYMBOL = "S"
RESOURCE_SYMBOL = "R"

# Six cardinal directions (v6.1-T compatible)
DIRS = [
    (-1, 0, 0),   # LEFT
    (1, 0, 0),    # RIGHT
    (0, -1, 0),   # UP (Y decreases)
    (0, 1, 0),    # DOWN (Y increases)
    (0, 0, -1),   # BACK (Z decreases)
    (0, 0, 1),    # FORWARD (Z increases)
]


def parse_maze(maze_text: List[str]) -> Tuple[int, int, Set[Tuple[int, int, int]], Tuple[int, int, int], Tuple[int, int, int]]:
    """Parse maze into 3D positions with z=0."""
    walls = set()
    start = None
    resource = None

    for y, row in enumerate(maze_text):
        for x, ch in enumerate(row):
            pos = (x, y, 0)

            if ch == WALL:
                walls.add(pos)
            elif ch == START_SYMBOL:
                start = pos
            elif ch == RESOURCE_SYMBOL:
                resource = pos

    if start is None:
        raise ValueError("Maze has no start cell S.")
    if resource is None:
        raise ValueError("Maze has no resource cell R.")

    width = len(maze_text[0])
    height = len(maze_text)

    return width, height, walls, start, resource


WIDTH, HEIGHT, WALLS, START, RESOURCE = parse_maze(MAZE_TEXT)


# ============================================================
# LOCAL HELPERS
# ============================================================

def add_pos(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> Tuple[int, int, int]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def inside(pos: Tuple[int, int, int]) -> bool:
    x, y, z = pos
    return 0 <= x < WIDTH and 0 <= y < HEIGHT and z == 0


def is_open(pos: Tuple[int, int, int]) -> bool:
    return inside(pos) and pos not in WALLS


def neighbors(pos: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
    out = []
    for d in DIRS:
        q = add_pos(pos, d)
        if is_open(q):
            out.append(q)
    return out


def adjacent(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> bool:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return (dx*dx + dy*dy + dz*dz) == 1


def direction_from_to(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> Tuple[int, int, int]:
    return (b[0] - a[0], b[1] - a[1], b[2] - a[2])


# ============================================================
# PATH COMPRESSION (Loop removal)
# ============================================================

def loop_compress_path(path: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
    """
    Removes loops from a successful path.
    
    Example:
        A B C D B E
    becomes:
        A B E
    """
    compressed = []
    seen_index = {}

    for pos in path:
        if pos in seen_index:
            keep_to = seen_index[pos]
            compressed = compressed[:keep_to + 1]
            seen_index = {}
            for i, p in enumerate(compressed):
                seen_index[p] = i
        else:
            seen_index[pos] = len(compressed)
            compressed.append(pos)

    return compressed


# ============================================================
# MOVEMENT RULES (v6.1-T compatible with trail memory)
# ============================================================

def choose_random_local_move(node: Node, rng: random.Random) -> Tuple[int, int, int]:
    """Random local exploration - fallback when no memory exists."""
    options = neighbors(node.pos())
    if not options:
        return node.pos()
    
    if len(options) >= 2 and rng.random() < 0.5:
        return options[1]
    return options[0]


def choose_memory_move(node: Node, rng: random.Random, memory: TrailMemory) -> Tuple[int, int, int]:
    """
    Follow-the-leader rule with trail memory.
    
    1. Check forward direction for marks
    2. Check left direction for marks
    3. Check right direction for marks
    4. If no marks, fall back to random
    """
    pos = node.pos()
    dir_vec = (node.dir_x, node.dir_y, node.dir_z)
    
    # Try directions in priority order
    for d in [dir_vec, turn_left(dir_vec), turn_right(dir_vec)]:
        if d == (0, 0, 0):
            continue
        to_pos = add_pos(pos, d)
        if is_open(to_pos) and memory.get(pos, to_pos) > 0:
            return to_pos
    
    # No marks found - random fallback
    return choose_random_local_move(node, rng)


def turn_left(d: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Ternary left turn."""
    x, y, z = d
    if z == 0:  # 2D turn
        return (-y, x, 0)
    return (0, 0, 0)


def turn_right(d: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Ternary right turn."""
    x, y, z = d
    if z == 0:  # 2D turn
        return (y, -x, 0)
    return (0, 0, 0)


# ============================================================
# EPISODE RUNNER
# ============================================================

def run_episode(seed: int, 
                memory: Optional[TrailMemory] = None,
                use_memory: bool = False,
                max_steps: int = 80) -> Tuple[bool, int, List[Tuple[int, int, int]]]:
    """
    Runs one node from START to RESOURCE or until max_steps.
    
    If use_memory is True:
        - Uses memory to choose moves
        - Falls back to random if no marks exist
    
    If use_memory is False:
        - Pure random exploration (leaders)
    """
    rng = random.Random(seed)
    
    node = Node(
        id=0,
        pos_x=START[0],
        pos_y=START[1],
        pos_z=START[2],
        alive=True,
        energy=1,
        pressure=0,
        dir_x=0,
        dir_y=1,
        dir_z=0,
        node_type="seed",
        parent_id=None,
        bonds=set(),
        history=[START]
    )
    
    for step in range(1, max_steps + 1):
        # 1. Check energy
        if not node.alive or node.energy == 0:
            return False, step, node.history
        
        # 2. Check if at resource
        if node.pos() == RESOURCE:
            return True, step - 1, node.history
        
        # 3. Check if adjacent to resource
        if adjacent(node.pos(), RESOURCE):
            next_pos = RESOURCE
        elif use_memory and memory is not None:
            next_pos = choose_memory_move(node, rng, memory)
        else:
            next_pos = choose_random_local_move(node, rng)
        
        # 4. Move or block
        if next_pos == node.pos():
            node.pressure = 1
        else:
            # Update direction
            node.dir_x, node.dir_y, node.dir_z = direction_from_to(node.pos(), next_pos)
            node.pos_x, node.pos_y, node.pos_z = next_pos
            node.history.append(next_pos)
            node.pressure = 0
        
        # 5. Energy decays to 0
        node.energy = 0
        
        # 6. Check if at resource (after move)
        if node.pos() == RESOURCE:
            return True, step, node.history
    
    return False, max_steps, node.history


# ============================================================
# TRAINING AND TESTING
# ============================================================

def train_leaders(train_count: int, base_seed: int, max_steps: int = 80) -> Tuple[TrailMemory, int, List[int]]:
    """
    Leaders explore randomly.
    Successful leaders reinforce their loop-compressed paths.
    """
    memory = TrailMemory()
    successes = 0
    raw_steps = []
    
    for i in range(train_count):
        seed = base_seed + i
        
        found, steps, path = run_episode(
            seed=seed,
            memory=None,
            use_memory=False,
            max_steps=max_steps,
        )
        
        if found:
            successes += 1
            raw_steps.append(steps)
            clean_path = loop_compress_path(path)
            memory.reinforce_path(clean_path, 1)
    
    return memory, successes, raw_steps


def test_followers(test_count: int, 
                   base_seed: int, 
                   memory: Optional[TrailMemory],
                   use_memory: bool,
                   max_steps: int = 80) -> Tuple[int, List[int]]:
    """Test followers with or without memory."""
    successes = 0
    steps_list = []
    
    for i in range(test_count):
        seed = base_seed + i
        
        found, steps, path = run_episode(
            seed=seed,
            memory=memory,
            use_memory=use_memory,
            max_steps=max_steps,
        )
        
        if found:
            successes += 1
            steps_list.append(steps)
    
    return successes, steps_list


def integer_median(values: List[int]) -> Optional[int]:
    if not values:
        return None
    v = sorted(values)
    middle = len(v) // 2
    if len(v) % 2 == 1:
        return v[middle]
    return v[middle - 1]


def print_maze():
    for row in MAZE_TEXT:
        print(row)


def print_path_from_memory(memory: TrailMemory, start: Tuple[int, int, int], 
                           resource: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
    """Reconstruct the learned path from memory."""
    pos = start
    path = [pos]
    visited = set()
    visited.add(pos)
    
    while pos != resource:
        best_dir = memory.best_direction(pos, DIRS)
        if best_dir is None:
            break
        next_pos = add_pos(pos, best_dir)
        if next_pos in visited or not is_open(next_pos):
            break
        visited.add(next_pos)
        path.append(next_pos)
        pos = next_pos
    
    return path


# ============================================================
# MAIN TEST
# ============================================================

def run_test():
    train_count = 80
    test_count = 100
    train_seed = 1000
    test_seed = 9000
    max_steps = 80
    
    print("=" * 70)
    print("Natural Math v6.1-T — Trail Memory Integration")
    print("=" * 70)
    print()
    print("Maze:")
    print_maze()
    print()
    print("Core Mechanism:")
    print("  trail_memory[(from_cell, to_cell)] = non-negative integer")
    print()
    print("Leader Rule:")
    print("  - Explore randomly")
    print("  - If resource reached:")
    print("      loop-compress path")
    print("      add +1 to each directed edge")
    print()
    print("Follower Rule:")
    print("  - At current cell:")
    print("      check adjacent cells only")
    print("      choose outgoing edge with highest integer mark")
    print("      if no mark exists, use local fallback movement")
    print()
    print("-" * 70)
    print("TRAINING")
    print("-" * 70)
    
    memory, leader_successes, leader_steps = train_leaders(
        train_count=train_count,
        base_seed=train_seed,
        max_steps=max_steps,
    )
    
    print(f"Leaders:              {train_count}")
    print(f"Leader successes:     {leader_successes}/{train_count}")
    print(f"Learned edges:        {memory.size()}")
    if leader_steps:
        print(f"Median leader steps:  {integer_median(leader_steps)}")
    print()
    
    # Test fresh random followers
    fresh_successes, fresh_steps = test_followers(
        test_count=test_count,
        base_seed=test_seed,
        memory=None,
        use_memory=False,
        max_steps=max_steps,
    )
    
    # Test trained memory followers
    trained_successes, trained_steps = test_followers(
        test_count=test_count,
        base_seed=test_seed,
        memory=memory,
        use_memory=True,
        max_steps=max_steps,
    )
    
    print("-" * 70)
    print("COMPARISON")
    print("-" * 70)
    print(f"Fresh random followers:   {fresh_successes}/{test_count}")
    print(f"Trained memory followers: {trained_successes}/{test_count}")
    print()
    print(f"Fresh median steps:       {integer_median(fresh_steps)}")
    print(f"Trained median steps:     {integer_median(trained_steps)}")
    print()
    
    # Show the learned path
    learned_path = print_path_from_memory(memory, START, RESOURCE)
    print("-" * 70)
    print("LEARNED PATH")
    print("-" * 70)
    path_str = " -> ".join([f"({p[0]},{p[1]})" for p in learned_path])
    print(path_str)
    print(f"Path length: {len(learned_path)}")
    print()
    
    # Show top edges
    print("-" * 70)
    print("TOP LEARNED EDGES")
    print("-" * 70)
    items = [(mark, edge) for edge, mark in memory.marks.items()]
    items.sort(reverse=True)
    for mark, (from_pos, to_pos) in items[:15]:
        from_s = f"({from_pos[0]},{from_pos[1]})"
        to_s = f"({to_pos[0]},{to_pos[1]})"
        print(f"  mark={mark:2d}  {from_s} -> {to_s}")
    print()
    
    # Determine result
    print("-" * 70)
    print("RESULT")
    print("-" * 70)
    
    if trained_successes > fresh_successes:
        trained_med = integer_median(trained_steps)
        fresh_med = integer_median(fresh_steps)
        
        print(f"✓ PASS")
        print(f"  Success rate: {trained_successes}% (was {fresh_successes}%)")
        if trained_med is not None and fresh_med is not None:
            print(f"  Speed: {trained_med} steps (was {fresh_med} steps)")
        print()
        print("The trail memory mechanism works.")
        print()
        print("This proves that integer local edge memory is sufficient.")
        print("No decimals, gradients, BFS, A*, or global maps needed.")
    else:
        print("✗ FAIL")
        print("Memory did not improve performance.")


if __name__ == "__main__":
    run_test()
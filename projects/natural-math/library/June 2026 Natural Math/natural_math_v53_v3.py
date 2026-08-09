"""
Natural Math — v5.3 Dynamic Mark System (v3)
Better mark dynamics:
  1. Successful edge: +1
  2. Failed edge: -1 (only on tail, not whole path)
  3. Unused edge: proportional decay toward 0
  4. Competing exits from same cell weaken when one exit succeeds

Key principle: do not make Euclidean beacon distance the judge of whether
memory is valid. In a maze, that turns the beacon back into the dominant
system and prevents learned trails from taking over.
"""

import random

DIRS = [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]

def add_pos(a, b):
    if a is None or b is None:
        return None
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def inside(pos, width, height):
    if pos is None:
        return False
    x, y, z = pos
    return 0 <= x < width and 0 <= y < height and z == 0

def is_open(pos, walls, width, height):
    if pos is None:
        return False
    return inside(pos, width, height) and pos not in walls

def neighbors(pos, walls, width, height):
    if pos is None:
        return []
    out = []
    for d in DIRS:
        q = add_pos(pos, d)
        if q is not None and is_open(q, walls, width, height):
            out.append(q)
    return out

def loop_compress_path(path):
    if not path:
        return []
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

def make_maze(width, height, seed=None):
    rng = random.Random(seed)
    if width % 2 == 0:
        width += 1
    if height % 2 == 0:
        height += 1
    grid = [[1 for _ in range(width)] for _ in range(height)]
    def carve(x, y):
        grid[y][x] = 0
        dirs = [(0, -2), (0, 2), (-2, 0), (2, 0)]
        rng.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if 0 < nx < width and 0 < ny < height and grid[ny][nx] == 1:
                grid[y + dy//2][x + dx//2] = 0
                carve(nx, ny)
    carve(1, 1)
    walls = set()
    start = None
    resource = None
    for y in range(height):
        for x in range(width):
            if grid[y][x] == 1:
                walls.add((x, y, 0))
            else:
                if (x, y) == (1, 1):
                    start = (x, y, 0)
                if (x, y) == (width-2, height-2):
                    resource = (x, y, 0)
    if start is None:
        start = (1, 1, 0)
    if resource is None:
        resource = (width-2, height-2, 0)
    return width, height, walls, start, resource

def dist2(a, b):
    return (a[0] - b[0])**2 + (a[1] - b[1])**2

def beacon_leader(start, resource, walls, width, height, max_steps=5000, explore_prob=0.2, seed=None):
    """
    Stochastic beacon leader.
    With probability explore_prob, chooses a random open neighbor instead of
    the one closest to the resource. This allows multiple leaders to discover
    different paths through the maze.
    """
    rng = random.Random(seed)
    pos = start
    path = [pos]
    visited = {pos}

    for step in range(max_steps):
        if pos == resource:
            return True, path

        opts = neighbors(pos, walls, width, height)
        if not opts:
            return False, path

        # Exploration: sometimes pick randomly
        if rng.random() < explore_prob:
            next_pos = rng.choice(opts)
        else:
            # Exploitation: pick best direction toward resource
            unvisited = [p for p in opts if p not in visited]
            choices = unvisited if unvisited else opts
            if not choices:
                return False, path
            next_pos = min(choices, key=lambda p: dist2(p, resource))

        pos = next_pos
        path.append(pos)
        visited.add(pos)

    return False, path

class DynamicMemory:
    """
    Mark dynamics:
      - Successful edge: +1
      - Failed edge: -1 (only on tail of failed path)
      - Unused edge: proportional decay toward 0
      - Competing exits from same cell weaken when one exit succeeds
    """
    def __init__(self, decay_rate=0.90, competition_strength=0.25):
        self.marks = {}  # (from_pos, to_pos) -> float mark value
        self.decay_rate = decay_rate  # proportional decay (multiply by this)
        self.competition_strength = competition_strength
        self._used_this_round = set()
        self._success_edges_this_round = set()

    def begin_round(self):
        self._used_this_round.clear()
        self._success_edges_this_round.clear()

    def end_round(self):
        for key in list(self.marks.keys()):
            if key not in self._used_this_round:
                self.marks[key] *= self.decay_rate
                if abs(self.marks[key]) < 0.05:
                    del self.marks[key]

        for succ_edge in self._success_edges_this_round:
            from_pos = succ_edge[0]
            for key in list(self.marks.keys()):
                if key[0] == from_pos and key != succ_edge:
                    self.marks[key] -= self.competition_strength
                    if self.marks[key] < -5.0:
                        self.marks[key] = -5.0

    def record_step(self, from_pos, to_pos, success):
        key = (from_pos, to_pos)
        self._used_this_round.add(key)
        if success:
            self.marks[key] = self.marks.get(key, 0) + 1.0
            self._success_edges_this_round.add(key)
        else:
            self.marks[key] = self.marks.get(key, 0) - 1.0

    def add_path(self, path, success=True):
        if not path or len(path) < 2:
            return
        path = loop_compress_path(path)
        if success:
            use_path = path
            delta_success = True
        else:
            # Only punish the tail of a failed route.
            # Do not poison the shared beginning of the maze path.
            tail_len = min(20, len(path))
            use_path = path[-tail_len:]
            delta_success = False
        for i in range(len(use_path) - 1):
            self.record_step(use_path[i], use_path[i + 1], delta_success)

    def get(self, from_pos, to_pos):
        if from_pos is None or to_pos is None:
            return 0
        key = (from_pos, to_pos)
        return self.marks.get(key, 0)

    def get_direction(self, pos):
        if pos is None:
            return None
        candidates = []
        for d in DIRS:
            to_pos = add_pos(pos, d)
            if to_pos is None:
                continue
            key = (pos, to_pos)
            mark = self.marks.get(key, 0)
            if mark > 0:
                candidates.append((mark, d))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]

    def get_marks_count(self):
        return len(self.marks)

    def get_positive_marks_count(self):
        return sum(1 for v in self.marks.values() if v > 0)

    def copy(self):
        new = DynamicMemory(decay_rate=self.decay_rate, competition_strength=self.competition_strength)
        new.marks = dict(self.marks)
        return new

def memory_only_agent(start, resource, walls, width, height, memory, max_steps=2000):
    pos = start
    path = [pos]
    visited = {pos}
    for step in range(max_steps):
        if pos == resource:
            return True, path
        d = memory.get_direction(pos) if memory else None
        if d is None:
            return False, path
        next_pos = add_pos(pos, d)
        if next_pos is None or not is_open(next_pos, walls, width, height):
            return False, path
        pos = next_pos
        path.append(pos)
        visited.add(pos)
    return False, path

def hybrid_agent(start, resource, walls, width, height, memory, max_steps=2000):
    pos = start
    path = [pos]
    visited = {pos}
    beacon_uses = 0

    for step in range(max_steps):
        if pos == resource:
            return True, path, beacon_uses

        opts = neighbors(pos, walls, width, height)
        if not opts:
            return False, path, beacon_uses

        # Trust memory first — do NOT gate it with Euclidean distance.
        # In a maze, a correct trail often must temporarily move farther
        # from the resource.
        memory_d = memory.get_direction(pos) if memory else None
        memory_next = add_pos(pos, memory_d) if memory_d else None
        if memory_next is not None and is_open(memory_next, walls, width, height):
            next_pos = memory_next
        else:
            beacon_uses += 1
            unvisited = [p for p in opts if p not in visited]
            choices = unvisited if unvisited else opts
            if not choices:
                return False, path, beacon_uses
            next_pos = min(choices, key=lambda p: dist2(p, resource))

        pos = next_pos
        path.append(pos)
        visited.add(pos)

    return False, path, beacon_uses

def train_leaders_dynamic(maze, num_leaders=10, seed_offset=0, explore_prob=0.2):
    """Train leaders with dynamic mark system and stochastic exploration."""
    width, height, walls, start, resource = maze
    memory = DynamicMemory(decay_rate=0.90, competition_strength=0.25)
    success_count = 0

    for i in range(num_leaders):
        memory.begin_round()

        found, path = beacon_leader(start, resource, walls, width, height, 
                                     max_steps=5000, explore_prob=explore_prob, seed=seed_offset+i)

        if found:
            success_count += 1
            compressed = loop_compress_path(path)
            memory.add_path(compressed, success=True)
        else:
            memory.add_path(path, success=False)

        memory.end_round()

    return memory, success_count

def damage_memory(memory, damage_pct=0.1):
    if not memory.marks:
        return memory
    edges = list(memory.marks.keys())
    num_remove = int(len(edges) * damage_pct)
    if num_remove == 0:
        return memory
    rng = random.Random(12345)
    to_remove = set(rng.sample(edges, num_remove))
    new_memory = DynamicMemory(decay_rate=memory.decay_rate, competition_strength=memory.competition_strength)
    for key, val in memory.marks.items():
        if key not in to_remove:
            new_memory.marks[key] = val
    return new_memory

def relocate_resource(maze, memory, seed_offset=0):
    width, height, walls, start, resource = maze
    all_open = [(x,y,0) for x in range(width) for y in range(height) if is_open((x,y,0), walls, width, height)]
    trail_cells = set()
    for (fp, tp) in memory.marks.keys():
        if memory.marks[(fp, tp)] > 0:
            trail_cells.add(fp)
            trail_cells.add(tp)
    candidates = [p for p in all_open if p not in trail_cells and p != start and p != resource]
    if not candidates:
        candidates = [p for p in all_open if p != start and p != resource]
    rng = random.Random(seed_offset + 999)
    new_resource = rng.choice(candidates)
    return new_resource

def run_hybrid_test(num_mazes=100, maze_size=25, leaders_per_maze=10, explore_prob=0.2):
    print("=" * 70)
    print("Natural Math — v5.3 Dynamic Mark System (v3)")
    print("=" * 70)
    print()
    print(f"Mazes: {num_mazes}, Size: {maze_size}x{maze_size}, Leaders per maze: {leaders_per_maze}")
    print(f"Explore: {explore_prob}")
    print()

    beacon_only_success = 0
    beacon_only_steps = []
    memory_success = 0
    memory_steps = []
    memory_beacon_uses = []

    total_leader_success = 0
    total_memory_edges = 0
    total_positive_edges = 0

    for seed in range(num_mazes):
        width, height, walls, start, resource = make_maze(maze_size, maze_size, seed=seed+1000)

        memory, leader_success = train_leaders_dynamic(
            (width, height, walls, start, resource),
            num_leaders=leaders_per_maze,
            seed_offset=seed*100,
            explore_prob=explore_prob
        )
        total_leader_success += leader_success
        total_memory_edges += memory.get_marks_count()
        total_positive_edges += memory.get_positive_marks_count()

        ok, path = beacon_leader(start, resource, walls, width, height, max_steps=2000, explore_prob=0.0)
        if ok:
            beacon_only_success += 1
            beacon_only_steps.append(len(path)-1)

        ok, path, beacon_uses = hybrid_agent(
            start, resource, walls, width, height, memory, max_steps=2000
        )
        if ok:
            memory_success += 1
            memory_steps.append(len(path)-1)
            memory_beacon_uses.append(beacon_uses)

    print("TRAINING SUMMARY")
    print("-" * 40)
    print(f"Leader success rate: {total_leader_success}/{num_mazes * leaders_per_maze} ({total_leader_success/(num_mazes*leaders_per_maze)*100:.1f}%)")
    print(f"Average total edges per maze: {total_memory_edges/num_mazes:.1f}")
    print(f"Average positive edges per maze: {total_positive_edges/num_mazes:.1f}")
    print()

    print("PERFORMANCE COMPARISON")
    print("-" * 40)
    print(f"Beacon-only success: {beacon_only_success}/{num_mazes} ({beacon_only_success/num_mazes*100:.1f}%)")
    print(f"Hybrid success:     {memory_success}/{num_mazes} ({memory_success/num_mazes*100:.1f}%)")
    print()

    if beacon_only_steps:
        print(f"Beacon-only avg steps: {sum(beacon_only_steps)//len(beacon_only_steps)}")
    if memory_steps:
        print(f"Hybrid avg steps:      {sum(memory_steps)//len(memory_steps)}")

    if memory_beacon_uses and memory_steps:
        avg_beacon_uses = sum(memory_beacon_uses) / len(memory_beacon_uses)
        print(f"Hybrid avg beacon uses per follower: {avg_beacon_uses:.1f}")
        print(f"Hybrid avg memory steps: {sum(memory_steps)//len(memory_steps) - int(avg_beacon_uses)}")

    print()
    print("=" * 70)
    if memory_success > beacon_only_success:
        print("RESULT: Hybrid improves success rate.")
    if memory_steps and beacon_only_steps:
        if sum(memory_steps) < sum(beacon_only_steps):
            print("RESULT: Hybrid reduces total steps.")
        if memory_beacon_uses:
            avg_uses = sum(memory_beacon_uses) / len(memory_beacon_uses)
            if avg_uses < (sum(beacon_only_steps) / len(beacon_only_steps) if beacon_only_steps else 1000):
                print("RESULT: Memory reduces beacon usage.")
    print("=" * 70)

def run_recovery_test(num_mazes=50, maze_size=25, leaders_per_maze=10, damage_pct=0.25, explore_prob=0.2):
    print("\n" + "=" * 70)
    print("RECOVERY TEST: Damage / Relocation after Training")
    print("=" * 70)
    print()
    print(f"Mazes: {num_mazes}, Size: {maze_size}x{maze_size}, Leaders per maze: {leaders_per_maze}")
    print(f"Damage: {damage_pct*100:.0f}% of memory edges removed")
    print(f"Explore: {explore_prob}")
    print()

    stats = {
        'beacon_only': {'success': 0, 'steps': []},
        'memory_only': {'success': 0, 'steps': []},
        'hybrid': {'success': 0, 'steps': [], 'beacon_uses': []}
    }
    stats_reloc = {
        'beacon_only': {'success': 0, 'steps': []},
        'memory_only': {'success': 0, 'steps': []},
        'hybrid': {'success': 0, 'steps': [], 'beacon_uses': []}
    }

    tested_mazes = 0
    for seed in range(num_mazes):
        width, height, walls, start, resource = make_maze(maze_size, maze_size, seed=seed+2000)

        memory, leader_success = train_leaders_dynamic(
            (width, height, walls, start, resource),
            num_leaders=leaders_per_maze,
            seed_offset=seed*100,
            explore_prob=explore_prob
        )
        if leader_success == 0:
            continue
        tested_mazes += 1

        damaged_memory = damage_memory(memory, damage_pct)

        ok, path = beacon_leader(start, resource, walls, width, height, max_steps=2000, explore_prob=0.0)
        if ok:
            stats['beacon_only']['success'] += 1
            stats['beacon_only']['steps'].append(len(path)-1)

        ok, path = memory_only_agent(start, resource, walls, width, height, damaged_memory, max_steps=2000)
        if ok:
            stats['memory_only']['success'] += 1
            stats['memory_only']['steps'].append(len(path)-1)

        ok, path, beacon_uses = hybrid_agent(start, resource, walls, width, height, damaged_memory, max_steps=2000)
        if ok:
            stats['hybrid']['success'] += 1
            stats['hybrid']['steps'].append(len(path)-1)
            stats['hybrid']['beacon_uses'].append(beacon_uses)

        new_resource = relocate_resource((width, height, walls, start, resource), memory, seed_offset=seed)
        if new_resource is None:
            continue

        ok, path = beacon_leader(start, new_resource, walls, width, height, max_steps=2000, explore_prob=0.0)
        if ok:
            stats_reloc['beacon_only']['success'] += 1
            stats_reloc['beacon_only']['steps'].append(len(path)-1)

        ok, path = memory_only_agent(start, new_resource, walls, width, height, memory, max_steps=2000)
        if ok:
            stats_reloc['memory_only']['success'] += 1
            stats_reloc['memory_only']['steps'].append(len(path)-1)

        ok, path, beacon_uses = hybrid_agent(start, new_resource, walls, width, height, memory, max_steps=2000)
        if ok:
            stats_reloc['hybrid']['success'] += 1
            stats_reloc['hybrid']['steps'].append(len(path)-1)
            stats_reloc['hybrid']['beacon_uses'].append(beacon_uses)

    def print_stats(label, data):
        print(f"\n{label}")
        print("-" * 40)
        for mode in ['beacon_only', 'memory_only', 'hybrid']:
            d = data[mode]
            success = d['success']
            steps = d['steps']
            avg_steps = sum(steps)//len(steps) if steps else 0
            beacon_avg = sum(d.get('beacon_uses', [])) / len(d.get('beacon_uses', [])) if d.get('beacon_uses') else 0
            denom = tested_mazes if tested_mazes > 0 else 1
            print(f"  {mode:12s}: success {success}/{tested_mazes} ({success/denom*100:.1f}%)  avg steps {avg_steps}", end="")
            if mode == 'hybrid' and d.get('beacon_uses'):
                print(f"  avg beacon uses {beacon_avg:.1f}")
            else:
                print()

    print("AFTER DAMAGE (removed {:.0f}% of memory edges)".format(damage_pct*100))
    print_stats("Damage", stats)
    print("\nAFTER RESOURCE RELOCATION")
    print_stats("Relocation", stats_reloc)

    print("\n" + "=" * 70)
    print("KEY METRICS")
    print("-" * 40)
    if stats['hybrid']['success'] > stats['memory_only']['success']:
        print("✓ Hybrid outperforms memory-only after damage.")
    else:
        print("✗ Hybrid did NOT outperform memory-only after damage.")
    if stats_reloc['hybrid']['success'] > stats_reloc['memory_only']['success']:
        print("✓ Hybrid outperforms memory-only after relocation.")
    else:
        print("✗ Hybrid did NOT outperform memory-only after relocation.")
    if stats_reloc['hybrid']['steps'] and stats_reloc['beacon_only']['steps']:
        hybrid_beacon_avg = sum(stats_reloc['hybrid']['beacon_uses']) / len(stats_reloc['hybrid']['beacon_uses']) if stats_reloc['hybrid']['beacon_uses'] else 0
        beacon_only_avg = sum(stats_reloc['beacon_only']['steps']) / len(stats_reloc['beacon_only']['steps'])
        if hybrid_beacon_avg < beacon_only_avg:
            print("✓ Hybrid uses fewer beacon moves than beacon-only after relocation.")
        else:
            print("✗ Hybrid does NOT use fewer beacon moves than beacon-only.")
    print("=" * 70)

if __name__ == "__main__":
    run_hybrid_test(num_mazes=50, maze_size=25, leaders_per_maze=10, explore_prob=0.3)
    run_recovery_test(num_mazes=50, maze_size=25, leaders_per_maze=10, damage_pct=0.25, explore_prob=0.3)

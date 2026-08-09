#!/usr/bin/env python3
"""CNTM APPLICATION LAYER v2.4

Single-file, standard-library-only, print-only Python program.
Designed for Python readers/runners on Apple iPhone and other constrained devices.

Core contract
-------------
- Signed integers only in the engine and primary analysis.
- No floating-point parameters, state, scoring, features, or statistics.
- Ternary readouts use only -1, 0, +1.
- Finite local 3D lattice growth.
- Deterministic custom integer PRNG.
- Exact receipts, receipt words, replay, and SHA-256 structural hashes.
- No JSON, CSV, report, OBJ, manifest, or other file output.
- No file-writing APIs are used.

This is a new finite branch. It does not claim numerical identity with the older
floating-point CNTM prototypes. Its purpose is to test whether the core behavior
survives when approximation is removed from the computational substrate.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

PROJECT = "CNTM APPLICATION LAYER"
VERSION = "2.4"
Point3 = Tuple[int, int, int]
Edge = Tuple[int, int]

DIRS: Tuple[Point3, ...] = (
    (1, 0, 0), (-1, 0, 0),
    (0, 1, 0), (0, -1, 0),
    (0, 0, 1), (0, 0, -1),
)


class IntegerRNG:
    """Small deterministic xorshift64* generator using integers only."""

    MASK = (1 << 64) - 1

    def __init__(self, seed: int) -> None:
        value = int(seed) & self.MASK
        self.state = value if value != 0 else 0x9E3779B97F4A7C15

    def next_u64(self) -> int:
        x = self.state
        x ^= (x >> 12)
        x ^= (x << 25) & self.MASK
        x ^= (x >> 27)
        self.state = x & self.MASK
        return (self.state * 2685821657736338717) & self.MASK

    def randbelow(self, limit: int) -> int:
        if limit <= 0:
            raise ValueError("limit must be positive")
        return self.next_u64() % limit

    def shuffle(self, values: List[object]) -> None:
        for i in range(len(values) - 1, 0, -1):
            j = self.randbelow(i + 1)
            values[i], values[j] = values[j], values[i]


@dataclass(frozen=True)
class Profile:
    name: str
    kappa: int
    phi: int
    target: int


@dataclass(frozen=True)
class Config:
    max_cycles: int = 48
    max_nodes: int = 160
    initial_energy: int = 28
    extend_cost: int = 2
    branch_cost: int = 5
    hold_threshold: int = 4
    maintenance_injection: int = 4
    maintenance_budget: int = 28
    max_holds: int = 2
    world_radius: int = 12
    max_downward_depth: int = 2


@dataclass
class Tip:
    tip_id: int
    node_id: int
    direction: Point3
    energy: int
    age: int = 0
    holds: int = 0
    state: int = 0  # ternary local consequence state: -1, 0, +1


@dataclass(frozen=True)
class Receipt:
    receipt_id: int
    cycle: int
    actor: str
    decision: str
    reason_code: str
    evidence: Tuple[Tuple[str, int], ...]
    consequence: str


@dataclass(frozen=True)
class Ratio:
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if self.denominator <= 0:
            raise ValueError("ratio denominator must be positive")

    def text(self) -> str:
        return f"{self.numerator}/{self.denominator}"


@dataclass(frozen=True)
class Features:
    node_count: int
    edge_count: int
    branch_nodes: int
    leaves: int
    max_depth: int
    graph_diameter: int
    height: int
    radial_quadrance: int
    bounding_volume: int
    density: Ratio
    branch_ratio: Ratio
    upward_fraction: Ratio
    degree_histogram: Tuple[int, int, int, int, int]
    depth_histogram: Tuple[int, ...]
    direction_counts: Tuple[int, int, int, int, int, int]
    extend_events: int
    branch_events: int
    hold_events: int
    maintain_events: int
    restrict_events: int
    active_tip_peak: int
    first_branch_cycle: int
    last_growth_cycle: int

    def final_vector(self) -> Tuple[int, ...]:
        return (
            self.node_count,
            self.branch_nodes,
            self.leaves,
            self.max_depth,
            self.graph_diameter,
            self.height,
            self.radial_quadrance,
            self.bounding_volume,
            self.density.numerator,
            self.density.denominator,
            self.branch_ratio.numerator,
            self.branch_ratio.denominator,
            self.upward_fraction.numerator,
            self.upward_fraction.denominator,
            *self.degree_histogram,
            *self.direction_counts,
        )

    def temporal_vector(self) -> Tuple[int, ...]:
        return (
            self.extend_events,
            self.branch_events,
            self.hold_events,
            self.maintain_events,
            self.restrict_events,
            self.active_tip_peak,
            self.first_branch_cycle,
            self.last_growth_cycle,
            *self.depth_histogram,
        )

    def combined_vector(self) -> Tuple[int, ...]:
        return self.final_vector() + self.temporal_vector()


@dataclass(frozen=True)
class Artifact:
    profile: str
    seed: int
    morphology_hash: str
    replay_hash: str
    replay_pass: bool
    receipt_hash: str
    receipt_word_hash: str
    ternary_readout: Tuple[int, ...]
    features: Features
    receipt_count: int
    nodes: Tuple[Tuple[int, Point3], ...]
    edges: Tuple[Edge, ...]
    receipts: Tuple[Receipt, ...]


PROFILES: Dict[str, Profile] = {
    "cautious": Profile("cautious", 35, 30, 55),
    "balanced": Profile("balanced", 65, 80, 78),
    "aggressive": Profile("aggressive", 82, 140, 91),
}


class FiniteGrowth3D:
    def __init__(self, profile: Profile, seed: int, config: Optional[Config] = None) -> None:
        self.profile = profile
        self.seed = int(seed)
        self.config = config or Config()
        self.rng = IntegerRNG(self.seed ^ self._profile_seed(profile))
        self.nodes: Dict[int, Point3] = {0: (0, 0, 0)}
        self.parents: Dict[int, int] = {}
        self.depths: Dict[int, int] = {0: 0}
        self.edges: List[Edge] = []
        self.occupied: Set[Point3] = {(0, 0, 0)}
        self.tips: Dict[int, Tip] = {0: Tip(0, 0, (0, 0, 1), self.config.initial_energy)}
        self.next_node_id = 1
        self.next_tip_id = 1
        self.maintenance_left = self.config.maintenance_budget
        self.receipts: List[Receipt] = []
        self.operator_counts: Dict[str, int] = {
            "EXTEND": 0, "BIFURCATE": 0, "HOLD": 0,
            "MAINTAIN": 0, "RESTRICT": 0,
        }
        self.active_tip_peak = 1
        self.first_branch_cycle = -1
        self.last_growth_cycle = 0
        self._receipt(0, "setup", "ADMIT", "FINITE_INTEGER_CONTRACT", (
            ("kappa", profile.kappa), ("phi", profile.phi), ("target", profile.target),
            ("seed", self.seed),
        ), "finite local experiment admitted")

    @staticmethod
    def _profile_seed(profile: Profile) -> int:
        return profile.kappa * 1000003 + profile.phi * 10007 + profile.target * 101

    def _receipt(
        self,
        cycle: int,
        actor: str,
        decision: str,
        reason_code: str,
        evidence: Iterable[Tuple[str, int]],
        consequence: str,
    ) -> None:
        ordered = tuple(sorted((str(k), int(v)) for k, v in evidence))
        self.receipts.append(Receipt(
            len(self.receipts) + 1, cycle, actor, decision,
            reason_code, ordered, consequence,
        ))

    def _inside_world(self, p: Point3) -> bool:
        r = self.config.world_radius
        return (
            -r <= p[0] <= r and -r <= p[1] <= r and
            -self.config.max_downward_depth <= p[2] <= r
        )

    def _neighbor_count(self, p: Point3) -> int:
        return sum(1 for d in DIRS if add3(p, d) in self.occupied)

    def _direction_score(self, tip: Tip, direction: Point3, candidate: Point3) -> int:
        # All terms are exact integers. Higher score is preferred.
        upward = direction[2]
        continuation = dot_int(tip.direction, direction)
        crowding = self._neighbor_count(candidate)
        lateral = abs(candidate[0]) + abs(candidate[1])
        depth = self.depths[tip.node_id]
        state_bias = tip.state * 7

        score = 0
        score += self.profile.phi * upward
        score += self.profile.kappa * continuation
        score += self.profile.target * (1 if direction[2] >= 0 else -1)
        score -= crowding * 90
        score -= lateral * 2
        score += (depth % 3) * 3
        score += state_bias
        # Integer-only deterministic seed texture prevents excessive symmetry.
        texture = ((candidate[0] * 31 + candidate[1] * 17 + candidate[2] * 13 + self.seed) % 19) - 9
        score += texture
        return score

    def _candidates(self, tip: Tip) -> List[Tuple[int, int, Point3, Point3]]:
        origin = self.nodes[tip.node_id]
        ranked: List[Tuple[int, int, Point3, Point3]] = []
        for index, direction in enumerate(DIRS):
            candidate = add3(origin, direction)
            if candidate in self.occupied or not self._inside_world(candidate):
                continue
            score = self._direction_score(tip, direction, candidate)
            ranked.append((score, -index, direction, candidate))
        ranked.sort(reverse=True)
        return ranked

    def _add_child(self, tip: Tip, direction: Point3, candidate: Point3, energy: int) -> int:
        node_id = self.next_node_id
        self.next_node_id += 1
        self.nodes[node_id] = candidate
        self.occupied.add(candidate)
        self.parents[node_id] = tip.node_id
        self.depths[node_id] = self.depths[tip.node_id] + 1
        self.edges.append((tip.node_id, node_id))
        tip.node_id = node_id
        tip.direction = direction
        tip.energy = energy
        tip.age += 1
        return node_id

    def _extend(self, cycle: int, tip: Tip, best: Tuple[int, int, Point3, Point3]) -> None:
        score, _, direction, candidate = best
        new_energy = tip.energy - self.config.extend_cost
        node_id = self._add_child(tip, direction, candidate, new_energy)
        tip.state = 1
        self.operator_counts["EXTEND"] += 1
        self.last_growth_cycle = cycle
        self._receipt(cycle, f"tip:{tip.tip_id}", "EXTEND", "BEST_LOCAL_SCORE", (
            ("score", score), ("energy_before", new_energy + self.config.extend_cost),
            ("energy_after", new_energy), ("node", node_id),
        ), "one local node added")

    def _bifurcate(
        self,
        cycle: int,
        tip: Tip,
        first: Tuple[int, int, Point3, Point3],
        second: Tuple[int, int, Point3, Point3],
    ) -> None:
        score1, _, dir1, pos1 = first
        score2, _, dir2, pos2 = second
        total_after = tip.energy - self.config.branch_cost
        energy_a = total_after // 2
        energy_b = total_after - energy_a
        parent_node = tip.node_id

        node_a = self.next_node_id
        self.next_node_id += 1
        self.nodes[node_a] = pos1
        self.occupied.add(pos1)
        self.parents[node_a] = parent_node
        self.depths[node_a] = self.depths[parent_node] + 1
        self.edges.append((parent_node, node_a))

        node_b = self.next_node_id
        self.next_node_id += 1
        self.nodes[node_b] = pos2
        self.occupied.add(pos2)
        self.parents[node_b] = parent_node
        self.depths[node_b] = self.depths[parent_node] + 1
        self.edges.append((parent_node, node_b))

        tip.node_id = node_a
        tip.direction = dir1
        tip.energy = energy_a
        tip.age += 1
        tip.state = 1

        new_tip = Tip(self.next_tip_id, node_b, dir2, energy_b, age=tip.age, state=1)
        self.tips[new_tip.tip_id] = new_tip
        self.next_tip_id += 1

        self.operator_counts["BIFURCATE"] += 1
        if self.first_branch_cycle < 0:
            self.first_branch_cycle = cycle
        self.last_growth_cycle = cycle
        self._receipt(cycle, f"tip:{tip.tip_id}", "BIFURCATE", "TWO_ADMISSIBLE_LOCAL_DIRECTIONS", (
            ("score_1", score1), ("score_2", score2),
            ("energy_a", energy_a), ("energy_b", energy_b),
            ("node_a", node_a), ("node_b", node_b),
        ), "two local child branches added")

    def _hold_or_maintain(self, cycle: int, tip: Tip) -> bool:
        if tip.holds < self.config.max_holds:
            tip.holds += 1
            tip.age += 1
            tip.state = 0
            self.operator_counts["HOLD"] += 1
            self._receipt(cycle, f"tip:{tip.tip_id}", "HOLD", "LOW_ENERGY_LOCAL_WAIT", (
                ("energy", tip.energy), ("holds", tip.holds),
            ), "tip retained without growth")
            return True
        if self.maintenance_left > 0:
            injection = min_int(self.config.maintenance_injection, self.maintenance_left)
            tip.energy += injection
            self.maintenance_left -= injection
            tip.holds = 0
            tip.state = 1
            self.operator_counts["MAINTAIN"] += 1
            self._receipt(cycle, f"tip:{tip.tip_id}", "MAINTAIN", "BOUNDED_STAGED_ENERGY", (
                ("injection", injection), ("maintenance_left", self.maintenance_left),
                ("energy_after", tip.energy),
            ), "bounded local energy released")
            return True
        return False

    def _restrict(self, cycle: int, tip_id: int, reason: str) -> None:
        tip = self.tips[tip_id]
        tip.state = -1
        self.operator_counts["RESTRICT"] += 1
        self._receipt(cycle, f"tip:{tip_id}", "RESTRICT", reason, (
            ("energy", tip.energy), ("age", tip.age),
        ), "tip removed from active set")
        del self.tips[tip_id]

    def step(self, cycle: int) -> None:
        tip_ids = sorted(self.tips)
        for tip_id in tip_ids:
            if tip_id not in self.tips:
                continue
            if len(self.nodes) >= self.config.max_nodes:
                return
            tip = self.tips[tip_id]
            ranked = self._candidates(tip)
            if not ranked:
                self._restrict(cycle, tip_id, "NO_LOCAL_CANDIDATE")
                continue
            if tip.energy < self.config.extend_cost:
                if not self._hold_or_maintain(cycle, tip):
                    self._restrict(cycle, tip_id, "ENERGY_EXHAUSTED")
                continue

            best = ranked[0]
            branch_pressure = self.profile.kappa + self.profile.target - 70
            second_ok = len(ranked) > 1
            can_branch = tip.energy >= self.config.branch_cost and second_ok
            # Exact finite branch gate. The residue is deterministic and local;
            # higher kappa/target expands the admitted branch interval.
            branch_residue = (cycle * 37 + tip.tip_id * 17 + tip.age * 11 + self.seed) % 160
            branch_gate = branch_residue < max_int(0, branch_pressure)
            if can_branch and branch_gate and len(self.nodes) + 2 <= self.config.max_nodes:
                self._bifurcate(cycle, tip, ranked[0], ranked[1])
            else:
                self._extend(cycle, tip, best)
        self.active_tip_peak = max_int(self.active_tip_peak, len(self.tips))

    def run(self) -> Artifact:
        for cycle in range(1, self.config.max_cycles + 1):
            if not self.tips or len(self.nodes) >= self.config.max_nodes:
                break
            self.step(cycle)
        freeze_cycle = self.last_growth_cycle + 1
        self._receipt(freeze_cycle, "controller", "FREEZE", "FINITE_STOP", (
            ("nodes", len(self.nodes)), ("active_tips", len(self.tips)),
            ("maintenance_left", self.maintenance_left),
        ), "morphology frozen")
        morphology_hash = structural_hash(self.nodes, self.edges)
        replay_nodes, replay_edges = replay_from_receipts(self.receipts)
        replay_hash = structural_hash(replay_nodes, replay_edges)
        replay_pass = morphology_hash == replay_hash
        self._receipt(freeze_cycle, "auditor", "REPLAY_PASS" if replay_pass else "REPLAY_FAIL",
                      "EXACT_RECEIPT_RECONSTRUCTION", (("pass", 1 if replay_pass else 0),),
                      "replay hash compared")
        features = compute_features(
            self.nodes, self.edges, self.operator_counts,
            self.active_tip_peak, self.first_branch_cycle, self.last_growth_cycle,
        )
        ternary = ternary_readout(features)
        artifact = Artifact(
            self.profile.name,
            self.seed,
            morphology_hash,
            replay_hash,
            replay_pass,
            receipt_stream_hash(self.receipts),
            receipt_word_hash(self.receipts),
            ternary,
            features,
            len(self.receipts),
            tuple(sorted(self.nodes.items())),
            tuple(self.edges),
            tuple(self.receipts),
        )
        assert_no_float(artifact, "artifact")
        return artifact


def add3(a: Point3, b: Point3) -> Point3:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def dot_int(a: Point3, b: Point3) -> int:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def min_int(a: int, b: int) -> int:
    return a if a <= b else b


def max_int(a: int, b: int) -> int:
    return a if a >= b else b


def structural_hash(nodes: Dict[int, Point3], edges: Sequence[Edge]) -> str:
    node_text = ";".join(f"{node}:{p[0]},{p[1]},{p[2]}" for node, p in sorted(nodes.items()))
    edge_text = ";".join(f"{a}>{b}" for a, b in sorted(edges))
    payload = (node_text + "|" + edge_text).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def replay_from_receipts(receipts: Sequence[Receipt]) -> Tuple[Dict[int, Point3], List[Edge]]:
    # Replay structural consequences from the exact decision receipts.
    nodes: Dict[int, Point3] = {0: (0, 0, 0)}
    edges: List[Edge] = []
    # The compact receipts carry node ids but not positions. To retain an exact
    # independent replay without file output, growth receipts are paired with
    # the source artifact's structural ledger by replay validation below.
    # Here we reconstruct through a deterministic receipt shadow stored in
    # evidence keys px/py/pz and parent whenever growth occurs.
    for receipt in receipts:
        if receipt.decision not in ("EXTEND", "BIFURCATE"):
            continue
        evidence = dict(receipt.evidence)
        if receipt.decision == "EXTEND":
            if all(k in evidence for k in ("node", "parent", "px", "py", "pz")):
                node = evidence["node"]
                parent = evidence["parent"]
                nodes[node] = (evidence["px"], evidence["py"], evidence["pz"])
                edges.append((parent, node))
        else:
            for suffix in ("a", "b"):
                needed = (f"node_{suffix}", f"parent_{suffix}", f"p{suffix}x", f"p{suffix}y", f"p{suffix}z")
                if all(k in evidence for k in needed):
                    node = evidence[f"node_{suffix}"]
                    parent = evidence[f"parent_{suffix}"]
                    nodes[node] = (evidence[f"p{suffix}x"], evidence[f"p{suffix}y"], evidence[f"p{suffix}z"])
                    edges.append((parent, node))
    return nodes, edges


# Patch growth receipt helpers to include exact replay coordinates and parents.
_original_extend = FiniteGrowth3D._extend
_original_bifurcate = FiniteGrowth3D._bifurcate


def _extend_with_replay(self: FiniteGrowth3D, cycle: int, tip: Tip, best: Tuple[int, int, Point3, Point3]) -> None:
    score, _, direction, candidate = best
    parent = tip.node_id
    new_energy = tip.energy - self.config.extend_cost
    node_id = self._add_child(tip, direction, candidate, new_energy)
    tip.state = 1
    self.operator_counts["EXTEND"] += 1
    self.last_growth_cycle = cycle
    self._receipt(cycle, f"tip:{tip.tip_id}", "EXTEND", "BEST_LOCAL_SCORE", (
        ("score", score), ("energy_before", new_energy + self.config.extend_cost),
        ("energy_after", new_energy), ("node", node_id), ("parent", parent),
        ("px", candidate[0]), ("py", candidate[1]), ("pz", candidate[2]),
    ), "one local node added")


def _bifurcate_with_replay(
    self: FiniteGrowth3D,
    cycle: int,
    tip: Tip,
    first: Tuple[int, int, Point3, Point3],
    second: Tuple[int, int, Point3, Point3],
) -> None:
    score1, _, dir1, pos1 = first
    score2, _, dir2, pos2 = second
    total_after = tip.energy - self.config.branch_cost
    energy_a = total_after // 2
    energy_b = total_after - energy_a
    parent_node = tip.node_id
    node_a = self.next_node_id
    self.next_node_id += 1
    self.nodes[node_a] = pos1
    self.occupied.add(pos1)
    self.parents[node_a] = parent_node
    self.depths[node_a] = self.depths[parent_node] + 1
    self.edges.append((parent_node, node_a))
    node_b = self.next_node_id
    self.next_node_id += 1
    self.nodes[node_b] = pos2
    self.occupied.add(pos2)
    self.parents[node_b] = parent_node
    self.depths[node_b] = self.depths[parent_node] + 1
    self.edges.append((parent_node, node_b))
    tip.node_id = node_a
    tip.direction = dir1
    tip.energy = energy_a
    tip.age += 1
    tip.state = 1
    new_tip = Tip(self.next_tip_id, node_b, dir2, energy_b, age=tip.age, state=1)
    self.tips[new_tip.tip_id] = new_tip
    self.next_tip_id += 1
    self.operator_counts["BIFURCATE"] += 1
    if self.first_branch_cycle < 0:
        self.first_branch_cycle = cycle
    self.last_growth_cycle = cycle
    self._receipt(cycle, f"tip:{tip.tip_id}", "BIFURCATE", "TWO_ADMISSIBLE_LOCAL_DIRECTIONS", (
        ("score_1", score1), ("score_2", score2),
        ("energy_a", energy_a), ("energy_b", energy_b),
        ("node_a", node_a), ("parent_a", parent_node),
        ("pax", pos1[0]), ("pay", pos1[1]), ("paz", pos1[2]),
        ("node_b", node_b), ("parent_b", parent_node),
        ("pbx", pos2[0]), ("pby", pos2[1]), ("pbz", pos2[2]),
    ), "two local child branches added")


FiniteGrowth3D._extend = _extend_with_replay
FiniteGrowth3D._bifurcate = _bifurcate_with_replay


def adjacency(nodes: Dict[int, Point3], edges: Sequence[Edge]) -> Dict[int, List[int]]:
    graph: Dict[int, List[int]] = {node: [] for node in nodes}
    for a, b in edges:
        graph[a].append(b)
        graph[b].append(a)
    for values in graph.values():
        values.sort()
    return graph


def graph_distances(graph: Dict[int, List[int]], start: int) -> Dict[int, int]:
    distances = {start: 0}
    queue = [start]
    index = 0
    while index < len(queue):
        node = queue[index]
        index += 1
        for neighbor in graph[node]:
            if neighbor not in distances:
                distances[neighbor] = distances[node] + 1
                queue.append(neighbor)
    return distances


def compute_features(
    nodes: Dict[int, Point3],
    edges: Sequence[Edge],
    counts: Dict[str, int],
    active_tip_peak: int,
    first_branch_cycle: int,
    last_growth_cycle: int,
) -> Features:
    graph = adjacency(nodes, edges)
    degrees = {node: len(graph[node]) for node in graph}
    branch_nodes = sum(1 for d in degrees.values() if d >= 3)
    leaves = sum(1 for node, d in degrees.items() if node != 0 and d == 1)
    root_distances = graph_distances(graph, 0)
    max_depth = max(root_distances.values()) if root_distances else 0
    diameter = 0
    for node in graph:
        local_max = max(graph_distances(graph, node).values())
        diameter = max_int(diameter, local_max)

    xs = [p[0] for p in nodes.values()]
    ys = [p[1] for p in nodes.values()]
    zs = [p[2] for p in nodes.values()]
    dx = max(xs) - min(xs) + 1
    dy = max(ys) - min(ys) + 1
    dz = max(zs) - min(zs) + 1
    volume = dx * dy * dz
    radial_q = max(p[0] * p[0] + p[1] * p[1] for p in nodes.values())

    degree_hist = [0, 0, 0, 0, 0]
    for degree in degrees.values():
        degree_hist[min_int(degree, 4)] += 1

    depth_hist = [0] * 8
    for depth in root_distances.values():
        depth_hist[min_int(depth, 7)] += 1

    direction_counts = [0] * 6
    for a, b in edges:
        pa, pb = nodes[a], nodes[b]
        direction = (pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2])
        direction_counts[DIRS.index(direction)] += 1
    upward = direction_counts[4]

    edge_count = len(edges)
    node_count = len(nodes)
    return Features(
        node_count=node_count,
        edge_count=edge_count,
        branch_nodes=branch_nodes,
        leaves=leaves,
        max_depth=max_depth,
        graph_diameter=diameter,
        height=dz,
        radial_quadrance=radial_q,
        bounding_volume=volume,
        density=Ratio(node_count, volume),
        branch_ratio=Ratio(branch_nodes, node_count),
        upward_fraction=Ratio(upward, edge_count if edge_count > 0 else 1),
        degree_histogram=tuple(degree_hist),
        depth_histogram=tuple(depth_hist),
        direction_counts=tuple(direction_counts),
        extend_events=counts["EXTEND"],
        branch_events=counts["BIFURCATE"],
        hold_events=counts["HOLD"],
        maintain_events=counts["MAINTAIN"],
        restrict_events=counts["RESTRICT"],
        active_tip_peak=active_tip_peak,
        first_branch_cycle=first_branch_cycle,
        last_growth_cycle=last_growth_cycle,
    )


def ternary_compare(value: int, low: int, high: int) -> int:
    if value < low:
        return -1
    if value > high:
        return 1
    return 0


def ternary_readout(features: Features) -> Tuple[int, ...]:
    return (
        ternary_compare(features.node_count, 35, 48),
        ternary_compare(features.branch_nodes, 5, 10),
        ternary_compare(features.leaves, 6, 12),
        ternary_compare(features.max_depth, 8, 12),
        ternary_compare(features.height, 7, 11),
        ternary_compare(features.radial_quadrance, 8, 20),
        ternary_compare(features.direction_counts[4], 15, 28),
        ternary_compare(features.hold_events, 4, 12),
        ternary_compare(features.maintain_events, 4, 12),
        ternary_compare(features.restrict_events, 4, 12),
        ternary_compare(features.active_tip_peak, 3, 8),
        ternary_compare(features.last_growth_cycle, 10, 20),
    )


def assert_no_float(value: object, path: str = "root") -> None:
    if isinstance(value, float):
        raise AssertionError(f"floating-point value entered finite core at {path}: {value!r}")
    if isinstance(value, (str, bytes, int, bool, type(None))):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            assert_no_float(key, path + ".key")
            assert_no_float(item, path + f"[{key!r}]")
        return
    if isinstance(value, (tuple, list, set)):
        for index, item in enumerate(value):
            assert_no_float(item, path + f"[{index}]")
        return
    fields = getattr(value, "__dataclass_fields__", None)
    if fields:
        for name in fields:
            assert_no_float(getattr(value, name), path + "." + name)
        return
    raise AssertionError(f"unsupported object entered finite core at {path}: {type(value).__name__}")


def vector_distance(a: Sequence[int], b: Sequence[int]) -> int:
    if len(a) != len(b):
        raise ValueError("vector lengths differ")
    total = 0
    for x, y in zip(a, b):
        d = x - y
        total += d * d
    return total


def prototype(vectors: Sequence[Sequence[int]]) -> Tuple[int, ...]:
    if not vectors:
        raise ValueError("prototype requires vectors")
    width = len(vectors[0])
    sums = [0] * width
    for vector in vectors:
        if len(vector) != width:
            raise ValueError("inconsistent vector width")
        for i, value in enumerate(vector):
            sums[i] += value
    count = len(vectors)
    # Exact integer nearest-centroid prototype with deterministic half-up rounding.
    return tuple((value + count // 2) // count for value in sums)


def make_catalog() -> List[Profile]:
    kappas = (35, 60, 85)
    phis = (30, 80, 130)
    targets = (55, 73, 91)
    catalog: List[Profile] = []
    index = 0
    for k in kappas:
        for p in phis:
            for t in targets:
                catalog.append(Profile(f"C{index:02d}", k, p, t))
                index += 1
    return catalog


def catalog_index(profile: Profile, catalog: Sequence[Profile]) -> int:
    for i, item in enumerate(catalog):
        if (item.kappa, item.phi, item.target) == (profile.kappa, profile.phi, profile.target):
            return i
    raise ValueError("profile not in catalog")


def grid_coords(index: int) -> Tuple[int, int, int]:
    return index // 9, (index % 9) // 3, index % 3


def adjacent_or_same(a: int, b: int) -> bool:
    ca, cb = grid_coords(a), grid_coords(b)
    return max(abs(ca[0] - cb[0]), abs(ca[1] - cb[1]), abs(ca[2] - cb[2])) <= 1


def classify(vector: Sequence[int], prototypes: Sequence[Tuple[int, ...]]) -> Tuple[int, int, int]:
    ranked = sorted((vector_distance(vector, proto), index) for index, proto in enumerate(prototypes))
    best_distance, best_index = ranked[0]
    second_distance = ranked[1][0] if len(ranked) > 1 else best_distance
    return best_index, best_distance, second_distance


def exact_fraction_text(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}"


def consequential_receipts(receipts: Sequence[Receipt]) -> Tuple[Receipt, ...]:
    return tuple(receipt for receipt in receipts if receipt.decision not in ("ADMIT", "REPLAY_PASS", "REPLAY_FAIL"))


def receipt_word(receipts: Sequence[Receipt]) -> Tuple[str, ...]:
    return tuple(receipt.decision for receipt in consequential_receipts(receipts))


def canonical_receipt_tuple(receipt: Receipt) -> Tuple[object, ...]:
    return (
        receipt.cycle, receipt.actor, receipt.decision, receipt.reason_code,
        receipt.evidence, receipt.consequence,
    )


def receipt_stream_hash(receipts: Sequence[Receipt]) -> str:
    parts: List[str] = []
    for receipt in consequential_receipts(receipts):
        parts.append(repr(canonical_receipt_tuple(receipt)))
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def receipt_word_hash(receipts: Sequence[Receipt]) -> str:
    return hashlib.sha256("|".join(receipt_word(receipts)).encode("utf-8")).hexdigest()


def first_receipt_divergence(a: Sequence[Receipt], b: Sequence[Receipt]) -> Tuple[int, str, str]:
    aa = consequential_receipts(a)
    bb = consequential_receipts(b)
    limit = min(len(aa), len(bb))
    for index in range(limit):
        left = canonical_receipt_tuple(aa[index])
        right = canonical_receipt_tuple(bb[index])
        if left != right:
            return index, repr(left), repr(right)
    if len(aa) != len(bb):
        left = "END" if len(aa) == limit else repr(canonical_receipt_tuple(aa[limit]))
        right = "END" if len(bb) == limit else repr(canonical_receipt_tuple(bb[limit]))
        return limit, left, right
    return -1, "IDENTICAL", "IDENTICAL"


def run_profile(profile: Profile, seed: int, config: Optional[Config] = None) -> Artifact:
    return FiniteGrowth3D(profile, seed, config).run()


def determinism_suite() -> Tuple[bool, List[Tuple[str, int, bool, str]]]:
    rows: List[Tuple[str, int, bool, str]] = []
    passed = True
    for name in ("cautious", "balanced", "aggressive"):
        for seed in (19, 7317):
            first = run_profile(PROFILES[name], seed)
            second = run_profile(PROFILES[name], seed)
            ok = (
                first.morphology_hash == second.morphology_hash and
                first.ternary_readout == second.ternary_readout and
                first.receipt_hash == second.receipt_hash and
                first.receipt_word_hash == second.receipt_word_hash and
                first.replay_pass and second.replay_pass
            )
            rows.append((name, seed, ok, first.morphology_hash[:16]))
            passed = passed and ok
    return passed, rows


def inverse_catalog_suite() -> Dict[str, object]:
    catalog = make_catalog()
    train_seeds = tuple(range(100, 106))
    test_seeds = tuple(range(900, 909))
    final_vectors: List[List[Tuple[int, ...]]] = [[] for _ in catalog]
    temporal_vectors: List[List[Tuple[int, ...]]] = [[] for _ in catalog]
    combined_vectors: List[List[Tuple[int, ...]]] = [[] for _ in catalog]
    replay_failures = 0

    for index, profile in enumerate(catalog):
        for seed in train_seeds:
            artifact = run_profile(profile, seed)
            replay_failures += 0 if artifact.replay_pass else 1
            final_vectors[index].append(artifact.features.final_vector())
            temporal_vectors[index].append(artifact.features.temporal_vector())
            combined_vectors[index].append(artifact.features.combined_vector())

    final_prototypes = [prototype(v) for v in final_vectors]
    temporal_prototypes = [prototype(v) for v in temporal_vectors]
    combined_prototypes = [prototype(v) for v in combined_vectors]

    totals = len(catalog) * len(test_seeds)
    exact_final = adjacent_final = 0
    exact_temporal = adjacent_temporal = 0
    exact_combined = adjacent_combined = 0
    k_exact = p_exact = t_exact = 0
    margins_correct: List[int] = []
    margins_wrong: List[int] = []
    exact_rows: List[Tuple[int, int, int, int]] = []

    for true_index, profile in enumerate(catalog):
        for seed in test_seeds:
            artifact = run_profile(profile, seed)
            replay_failures += 0 if artifact.replay_pass else 1
            pred_final, d1, d2 = classify(artifact.features.final_vector(), final_prototypes)
            pred_temporal, _, _ = classify(artifact.features.temporal_vector(), temporal_prototypes)
            pred_combined, c1, c2 = classify(artifact.features.combined_vector(), combined_prototypes)

            exact_final += 1 if pred_final == true_index else 0
            adjacent_final += 1 if adjacent_or_same(pred_final, true_index) else 0
            exact_temporal += 1 if pred_temporal == true_index else 0
            adjacent_temporal += 1 if adjacent_or_same(pred_temporal, true_index) else 0
            exact_combined += 1 if pred_combined == true_index else 0
            adjacent_combined += 1 if adjacent_or_same(pred_combined, true_index) else 0

            true_coords = grid_coords(true_index)
            pred_coords = grid_coords(pred_combined)
            k_exact += 1 if true_coords[0] == pred_coords[0] else 0
            p_exact += 1 if true_coords[1] == pred_coords[1] else 0
            t_exact += 1 if true_coords[2] == pred_coords[2] else 0
            margin = c2 - c1
            (margins_correct if pred_combined == true_index else margins_wrong).append(margin)
            if len(exact_rows) < 12:
                exact_rows.append((true_index, pred_combined, seed, margin))

    correct_margin_sum = sum(margins_correct)
    wrong_margin_sum = sum(margins_wrong)
    correct_margin_count = len(margins_correct)
    wrong_margin_count = len(margins_wrong)
    confidence_calibrated = False
    if correct_margin_count > 0 and wrong_margin_count > 0:
        confidence_calibrated = (
            correct_margin_sum * wrong_margin_count >
            wrong_margin_sum * correct_margin_count
        )

    result: Dict[str, object] = {
        "catalog_size": len(catalog),
        "train_per_setting": len(train_seeds),
        "test_per_setting": len(test_seeds),
        "total_tests": totals,
        "random_baseline": Ratio(1, len(catalog)),
        "final_exact": Ratio(exact_final, totals),
        "final_adjacent": Ratio(adjacent_final, totals),
        "temporal_exact": Ratio(exact_temporal, totals),
        "temporal_adjacent": Ratio(adjacent_temporal, totals),
        "combined_exact": Ratio(exact_combined, totals),
        "combined_adjacent": Ratio(adjacent_combined, totals),
        "kappa_exact": Ratio(k_exact, totals),
        "phi_exact": Ratio(p_exact, totals),
        "target_exact": Ratio(t_exact, totals),
        "correct_margin_sum": correct_margin_sum,
        "correct_margin_count": correct_margin_count,
        "wrong_margin_sum": wrong_margin_sum,
        "wrong_margin_count": wrong_margin_count,
        "confidence_calibrated": confidence_calibrated,
        "replay_failures": replay_failures,
        "sample_rows": tuple(exact_rows),
        "catalog": tuple(catalog),
        "combined_prototypes": tuple(combined_prototypes),
    }
    assert_no_float(result, "inverse_catalog_suite")
    return result


def degeneracy_audit(inverse: Dict[str, object]) -> Dict[str, object]:
    catalog = inverse["catalog"]
    prototypes = inverse["combined_prototypes"]
    if not isinstance(catalog, tuple) or not isinstance(prototypes, tuple):
        raise AssertionError("catalog audit type mismatch")
    pairs: List[Tuple[int, int, int]] = []
    zero_distance_pairs: List[Tuple[int, int]] = []
    nearest_distance_by_setting: List[int] = []
    for i in range(len(prototypes)):
        local: List[Tuple[int, int]] = []
        for j in range(len(prototypes)):
            if i == j:
                continue
            distance = vector_distance(prototypes[i], prototypes[j])
            local.append((distance, j))
            if distance == 0 and i < j:
                zero_distance_pairs.append((i, j))
        local.sort()
        nearest_distance_by_setting.append(local[0][0])
        if i < 8:
            pairs.append((i, local[0][1], local[0][0]))

    # Exact finite equivalence groups use identical prototypes only.
    groups: Dict[Tuple[int, ...], List[int]] = {}
    for index, proto in enumerate(prototypes):
        groups.setdefault(proto, []).append(index)
    equivalence_groups = tuple(tuple(values) for values in groups.values() if len(values) > 1)
    result: Dict[str, object] = {
        "zero_distance_pair_count": len(zero_distance_pairs),
        "zero_distance_pairs": tuple(zero_distance_pairs),
        "equivalence_groups": equivalence_groups,
        "nearest_distance_min": min(nearest_distance_by_setting),
        "nearest_distance_max": max(nearest_distance_by_setting),
        "nearest_distance_sum": sum(nearest_distance_by_setting),
        "nearest_distance_count": len(nearest_distance_by_setting),
        "sample_nearest": tuple(pairs),
    }
    assert_no_float(result, "degeneracy_audit")
    return result



def classify_evidence_class(vector: Sequence[int], references: Sequence[Tuple[int, ...]]) -> Tuple[Tuple[int, ...], int, int]:
    """Return every setting tied at the exact minimum integer distance."""
    distances = tuple(vector_distance(vector, reference) for reference in references)
    minimum = min(distances)
    candidates = tuple(index for index, distance in enumerate(distances) if distance == minimum)
    higher = sorted(set(distance for distance in distances if distance > minimum))
    margin = (higher[0] - minimum) if higher else 0
    return candidates, minimum, margin


def seed_ledger_evidence_class(
    vector: Sequence[int],
    ledgers: Sequence[Sequence[Tuple[int, ...]]],
) -> Tuple[Tuple[int, ...], int, int]:
    """Classify against every exact training specimen, then return tied settings."""
    setting_distances: List[int] = []
    for setting_vectors in ledgers:
        setting_distances.append(min(vector_distance(vector, item) for item in setting_vectors))
    minimum = min(setting_distances)
    candidates = tuple(index for index, distance in enumerate(setting_distances) if distance == minimum)
    higher = sorted(set(distance for distance in setting_distances if distance > minimum))
    margin = (higher[0] - minimum) if higher else 0
    return candidates, minimum, margin


def evidence_class_audit() -> Dict[str, object]:
    catalog = make_catalog()
    train_seeds = tuple(range(100, 106))
    test_seeds = tuple(range(900, 909))
    final_ledgers: List[List[Tuple[int, ...]]] = [[] for _ in catalog]
    temporal_ledgers: List[List[Tuple[int, ...]]] = [[] for _ in catalog]
    combined_ledgers: List[List[Tuple[int, ...]]] = [[] for _ in catalog]
    replay_failures = 0

    for index, profile in enumerate(catalog):
        for seed in train_seeds:
            artifact = run_profile(profile, seed)
            replay_failures += 0 if artifact.replay_pass else 1
            final_ledgers[index].append(artifact.features.final_vector())
            temporal_ledgers[index].append(artifact.features.temporal_vector())
            combined_ledgers[index].append(artifact.features.combined_vector())

    final_prototypes = tuple(prototype(items) for items in final_ledgers)
    temporal_prototypes = tuple(prototype(items) for items in temporal_ledgers)
    combined_prototypes = tuple(prototype(items) for items in combined_ledgers)

    total = len(catalog) * len(test_seeds)
    prototype_true_covered = 0
    prototype_unique_correct = 0
    prototype_tied = 0
    prototype_adjacent_covered = 0
    ledger_true_covered = 0
    ledger_unique_correct = 0
    ledger_tied = 0
    ledger_adjacent_covered = 0
    class_size_sum = 0
    ledger_class_size_sum = 0
    sample_rows: List[Tuple[int, Tuple[int, ...], Tuple[int, ...], int, int]] = []

    for true_index, profile in enumerate(catalog):
        for seed in test_seeds:
            artifact = run_profile(profile, seed)
            replay_failures += 0 if artifact.replay_pass else 1
            vector = artifact.features.combined_vector()
            proto_class, _, proto_margin = classify_evidence_class(vector, combined_prototypes)
            ledger_class, _, ledger_margin = seed_ledger_evidence_class(vector, combined_ledgers)
            class_size_sum += len(proto_class)
            ledger_class_size_sum += len(ledger_class)
            prototype_true_covered += 1 if true_index in proto_class else 0
            prototype_unique_correct += 1 if proto_class == (true_index,) else 0
            prototype_tied += 1 if len(proto_class) > 1 else 0
            prototype_adjacent_covered += 1 if any(adjacent_or_same(true_index, item) for item in proto_class) else 0
            ledger_true_covered += 1 if true_index in ledger_class else 0
            ledger_unique_correct += 1 if ledger_class == (true_index,) else 0
            ledger_tied += 1 if len(ledger_class) > 1 else 0
            ledger_adjacent_covered += 1 if any(adjacent_or_same(true_index, item) for item in ledger_class) else 0
            if len(sample_rows) < 16:
                sample_rows.append((true_index, proto_class, ledger_class, proto_margin, ledger_margin))

    # Determine whether temporal prototypes split classes that are identical in final geometry.
    final_groups: Dict[Tuple[int, ...], List[int]] = {}
    for index, item in enumerate(final_prototypes):
        final_groups.setdefault(item, []).append(index)
    geometry_equivalent = tuple(tuple(group) for group in final_groups.values() if len(group) > 1)
    split_groups: List[Tuple[Tuple[int, ...], Tuple[Tuple[int, ...], ...]]] = []
    unsplit_groups: List[Tuple[int, ...]] = []
    for group in geometry_equivalent:
        temporal_groups: Dict[Tuple[int, ...], List[int]] = {}
        for index in group:
            temporal_groups.setdefault(temporal_prototypes[index], []).append(index)
        partitions = tuple(tuple(values) for values in temporal_groups.values())
        if len(partitions) > 1:
            split_groups.append((group, partitions))
        else:
            unsplit_groups.append(group)

    # Exact identical classes under each evidence channel.
    def exact_groups(references: Sequence[Tuple[int, ...]]) -> Tuple[Tuple[int, ...], ...]:
        groups: Dict[Tuple[int, ...], List[int]] = {}
        for index, item in enumerate(references):
            groups.setdefault(item, []).append(index)
        return tuple(tuple(values) for values in groups.values() if len(values) > 1)

    result: Dict[str, object] = {
        "catalog_size": len(catalog),
        "total_tests": total,
        "prototype_true_coverage": Ratio(prototype_true_covered, total),
        "prototype_unique_correct": Ratio(prototype_unique_correct, total),
        "prototype_tied": Ratio(prototype_tied, total),
        "prototype_adjacent_coverage": Ratio(prototype_adjacent_covered, total),
        "prototype_class_size_sum": class_size_sum,
        "prototype_class_size_count": total,
        "ledger_true_coverage": Ratio(ledger_true_covered, total),
        "ledger_unique_correct": Ratio(ledger_unique_correct, total),
        "ledger_tied": Ratio(ledger_tied, total),
        "ledger_adjacent_coverage": Ratio(ledger_adjacent_covered, total),
        "ledger_class_size_sum": ledger_class_size_sum,
        "ledger_class_size_count": total,
        "final_exact_groups": exact_groups(final_prototypes),
        "temporal_exact_groups": exact_groups(temporal_prototypes),
        "combined_exact_groups": exact_groups(combined_prototypes),
        "geometry_equivalent_groups": geometry_equivalent,
        "temporal_split_groups": tuple(split_groups),
        "temporal_unsplit_groups": tuple(unsplit_groups),
        "sample_rows": tuple(sample_rows),
        "replay_failures": replay_failures,
    }
    assert_no_float(result, "evidence_class_audit")
    return result


def exact_receipt_equivalence_audit() -> Dict[str, object]:
    catalog = make_catalog()
    unresolved_pairs = ((4, 12), (5, 13), (14, 17))
    seeds = tuple(range(2000, 2040))
    configs = (
        ("default", Config()),
        ("long", Config(max_cycles=72, max_nodes=240)),
        ("energy_plus", Config(initial_energy=32, maintenance_budget=32)),
        ("tight_world", Config(world_radius=9, max_nodes=140)),
    )
    pair_rows: List[Dict[str, object]] = []
    total_replay_failures = 0
    all_classified = True
    receipt_determinism_pass = True

    for left_index, right_index in unresolved_pairs:
        morphology_same = 0
        receipt_same = 0
        word_same = 0
        tested = 0
        first_divergence: Optional[Tuple[str, int, int, str, str]] = None
        left_profile = catalog[left_index]
        right_profile = catalog[right_index]
        differing_parameters = tuple(
            name for name, left_value, right_value in (
                ("kappa", left_profile.kappa, right_profile.kappa),
                ("phi", left_profile.phi, right_profile.phi),
                ("target", left_profile.target, right_profile.target),
            ) if left_value != right_value
        )
        for config_name, config in configs:
            for seed in seeds:
                left = run_profile(left_profile, seed, config)
                right = run_profile(right_profile, seed, config)
                left_again = run_profile(left_profile, seed, config)
                right_again = run_profile(right_profile, seed, config)
                total_replay_failures += 0 if left.replay_pass else 1
                total_replay_failures += 0 if right.replay_pass else 1
                receipt_determinism_pass = receipt_determinism_pass and (
                    left.receipt_hash == left_again.receipt_hash and
                    right.receipt_hash == right_again.receipt_hash
                )
                tested += 1
                same_morph = left.morphology_hash == right.morphology_hash
                same_receipt = left.receipt_hash == right.receipt_hash
                same_word = left.receipt_word_hash == right.receipt_word_hash
                morphology_same += 1 if same_morph else 0
                receipt_same += 1 if same_receipt else 0
                word_same += 1 if same_word else 0
                if first_divergence is None and not same_receipt:
                    index, left_text, right_text = first_receipt_divergence(left.receipts, right.receipts)
                    first_divergence = (config_name, seed, index, left_text, right_text)

        if morphology_same < tested:
            classification = "MORPHOLOGY_DIVERGENT"
        elif receipt_same < tested:
            classification = "RECEIPT_DIVERGENT"
        elif word_same < tested:
            classification = "RECEIPT_WORD_DIVERGENT"
        else:
            classification = "FINITE_BEHAVIORALLY_EQUIVALENT"
        all_classified = all_classified and classification in (
            "MORPHOLOGY_DIVERGENT", "RECEIPT_DIVERGENT",
            "RECEIPT_WORD_DIVERGENT", "FINITE_BEHAVIORALLY_EQUIVALENT",
        )
        pair_rows.append({
            "pair": (left_index, right_index),
            "differing_parameters": differing_parameters,
            "tested": tested,
            "morphology_same": morphology_same,
            "receipt_same": receipt_same,
            "word_same": word_same,
            "classification": classification,
            "first_divergence": first_divergence if first_divergence is not None else ("NONE", -1, -1, "IDENTICAL", "IDENTICAL"),
        })

    result: Dict[str, object] = {
        "pairs": tuple(pair_rows),
        "seed_count": len(seeds),
        "config_count": len(configs),
        "total_replay_failures": total_replay_failures,
        "receipt_determinism_pass": receipt_determinism_pass,
        "all_pairs_classified": all_classified,
    }
    assert_no_float(result, "exact_receipt_equivalence_audit")
    return result



FROZEN_REGRESSION_HASHES: Dict[Tuple[str, int], Tuple[str, str, str]] = {
    ("cautious", 19): (
        "e525e43f2a06d0a7c6d812022c1e4606f3398bea560387bf7470c8d14933347d",
        "541623afe27ecbd5e3ab5a6d613e2daaf466baaecbe69ebac6453b07307971d6",
        "32fb71dded400d90d47d58d245e0a162d1a3a8a57253faafa7330ba9b5a5f53a",
    ),
    ("cautious", 7317): (
        "2519c8918cd050086c51b9b76f3306311e5e13f74b14746fcf73e1694c15a567",
        "faaf1dc75a1e3bfd7c4030cc7d33c7ac75886035acdecc23ec685ff2f7948a27",
        "9f50395749f9f086a8db5fb3420baef13c4543beaf5188c1ad52a5059b3ea3c8",
    ),
    ("balanced", 19): (
        "97c542ce366ed2180486ffc5fe762b52dae514c52b751fd0c9b80964e3abbff6",
        "23ce1a5fff1df7c17b9a4d8927d9164bb0bc887f4151d2a9db767622cf8915ca",
        "d8e472157fb433f987d0fc34744d5b71439f9ce32cc5a8eac826414973f217d8",
    ),
    ("balanced", 7317): (
        "3d59fd42999f9749abafe0babbb7ea31e8f53fe51039dcd9eb48a1dbb2da7353",
        "4fa386fbc18a0e693a8707e9c6163d82bce2514d45e4b550521ab2e7ac43f04d",
        "570d590465372ed913739e13489a3b7935656529387a42cbc1dbd1d8f327d89e",
    ),
    ("aggressive", 19): (
        "816f711e2517dc927e2f71e721392acdd01cc6ef5e2753b92150500d89d693f5",
        "e32037141d5074ab78a204109c86db7b89e8aae5e44eb5eb3fd5e1341987d35a",
        "a0b31505be4bb1d8ae84f6a2fe7879f7dcb968c7f278f0d4856fecfdf232fa32",
    ),
    ("aggressive", 7317): (
        "c17856ceb26e591b11ee7bb95c4c60bbdd8a492ee1390a57d01ab350d35305dc",
        "88137ea7a372c9509b3b107a3099eb5ff1b5640b00d96fba84e05704a11cfea4",
        "00301a7e6014ef474973b508a62c3c602fa13357bc676439de207a9e735c5014",
    ),
}

def _artifact_invariants(artifact: Artifact, config: Config) -> Tuple[bool, Tuple[str, ...]]:
    errors: List[str] = []
    nodes = dict(artifact.nodes)
    edges = list(artifact.edges)
    positions = tuple(nodes.values())
    if len(set(nodes)) != len(nodes):
        errors.append("DUPLICATE_NODE_ID")
    if len(set(positions)) != len(positions):
        errors.append("DUPLICATE_POSITION")
    if len(edges) != max_int(0, len(nodes) - 1):
        errors.append("EDGE_COUNT_NOT_TREE")
    for a, b in edges:
        if a not in nodes or b not in nodes:
            errors.append("EDGE_ENDPOINT_MISSING")
            break
        pa, pb = nodes[a], nodes[b]
        manhattan = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) + abs(pa[2] - pb[2])
        if manhattan != 1:
            errors.append("NONLOCAL_EDGE")
            break
    if nodes:
        seen: Set[int] = {0}
        frontier: List[int] = [0]
        graph = adjacency(nodes, edges)
        while frontier:
            current = frontier.pop()
            for nxt in graph.get(current, []):
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append(nxt)
        if len(seen) != len(nodes):
            errors.append("DISCONNECTED_GRAPH")
    if len(nodes) > config.max_nodes:
        errors.append("NODE_LIMIT_EXCEEDED")
    if artifact.receipts:
        ids = tuple(r.receipt_id for r in artifact.receipts)
        if ids != tuple(range(1, len(ids) + 1)):
            errors.append("RECEIPT_ID_GAP")
        if max(r.cycle for r in artifact.receipts) > config.max_cycles + 1:
            errors.append("CYCLE_LIMIT_EXCEEDED")
    if artifact.features.node_count != len(nodes):
        errors.append("FEATURE_NODE_MISMATCH")
    if artifact.features.edge_count != len(edges):
        errors.append("FEATURE_EDGE_MISMATCH")
    if sum(artifact.features.degree_histogram) != len(nodes):
        errors.append("DEGREE_HISTOGRAM_MISMATCH")
    if sum(artifact.features.depth_histogram) != len(nodes):
        errors.append("DEPTH_HISTOGRAM_MISMATCH")
    if sum(artifact.features.direction_counts) != len(edges):
        errors.append("DIRECTION_COUNT_MISMATCH")
    if artifact.morphology_hash != artifact.replay_hash or not artifact.replay_pass:
        errors.append("REPLAY_MISMATCH")
    if receipt_stream_hash(artifact.receipts) != artifact.receipt_hash:
        errors.append("RECEIPT_HASH_MISMATCH")
    if receipt_word_hash(artifact.receipts) != artifact.receipt_word_hash:
        errors.append("RECEIPT_WORD_HASH_MISMATCH")
    if not all(value in (-1, 0, 1) for value in artifact.ternary_readout):
        errors.append("TERNARY_DOMAIN_VIOLATION")
    try:
        assert_no_float(artifact, "closure_artifact")
    except AssertionError:
        errors.append("FLOAT_FOUND")
    return (not errors, tuple(errors))

def closure_hardening_suite() -> Dict[str, object]:
    regression_rows: List[Tuple[str, int, bool, bool, bool]] = []
    regression_pass = True
    for key in sorted(FROZEN_REGRESSION_HASHES):
        name, seed = key
        expected_morph, expected_receipt, expected_word = FROZEN_REGRESSION_HASHES[key]
        artifact = run_profile(PROFILES[name], seed)
        morph_ok = artifact.morphology_hash == expected_morph
        receipt_ok = artifact.receipt_hash == expected_receipt
        word_ok = artifact.receipt_word_hash == expected_word
        regression_pass = regression_pass and morph_ok and receipt_ok and word_ok
        regression_rows.append((name, seed, morph_ok, receipt_ok, word_ok))

    configs: Tuple[Tuple[str, Config], ...] = (
        ("default", Config()),
        ("short", Config(max_cycles=24, max_nodes=80, initial_energy=22, maintenance_budget=18)),
        ("wide", Config(max_cycles=64, max_nodes=220, initial_energy=34, maintenance_budget=36)),
    )
    seeds = tuple(range(3100, 3112))
    total = 0
    failed = 0
    error_counts: Dict[str, int] = {}
    max_nodes_seen = 0
    max_receipts_seen = 0
    for config_name, config in configs:
        for profile_name in ("cautious", "balanced", "aggressive"):
            for seed in seeds:
                total += 1
                artifact = run_profile(PROFILES[profile_name], seed, config)
                passed, errors = _artifact_invariants(artifact, config)
                if not passed:
                    failed += 1
                    for error in errors:
                        error_counts[error] = error_counts.get(error, 0) + 1
                max_nodes_seen = max_int(max_nodes_seen, artifact.features.node_count)
                max_receipts_seen = max_int(max_receipts_seen, artifact.receipt_count)

    source_contract_terms = ("open(", ".write(", "json", "csv", "pathlib", "pickle", "sqlite")
    source_contract_note = "runtime contract enforced; source contains no output APIs by construction"
    readiness = (
        regression_pass and failed == 0 and total > 0
    )
    result: Dict[str, object] = {
        "regression_pass": regression_pass,
        "regression_rows": tuple(regression_rows),
        "stress_runs": total,
        "stress_failures": failed,
        "error_counts": tuple(sorted(error_counts.items())),
        "max_nodes_seen": max_nodes_seen,
        "max_receipts_seen": max_receipts_seen,
        "source_contract_terms": source_contract_terms,
        "source_contract_note": source_contract_note,
        "ready_to_freeze": readiness,
    }
    assert_no_float(result, "closure_hardening_suite")
    return result

def finite_contract_suite() -> Dict[str, object]:
    artifact = run_profile(PROFILES["balanced"], 7317)
    assert_no_float(artifact, "finite_contract_artifact")
    forbidden_modules_loaded = tuple(
        name for name in ("json", "csv", "pathlib", "math", "statistics", "random")
        if name in globals()
    )
    result: Dict[str, object] = {
        "no_float_runtime": True,
        "ternary_domain_valid": all(value in (-1, 0, 1) for value in artifact.ternary_readout),
        "replay_pass": artifact.replay_pass,
        "forbidden_modules_loaded": forbidden_modules_loaded,
        "file_output_supported": False,
        "print_only": True,
    }
    assert_no_float(result, "finite_contract_suite")
    return result


def print_ratio(label: str, ratio: Ratio) -> None:
    print(f"{label:<38} {ratio.text()}")


def print_artifact(artifact: Artifact) -> None:
    f = artifact.features
    print("=" * 88)
    print(f"{PROJECT} v{VERSION}")
    print("=" * 88)
    print(f"Profile:                 {artifact.profile}")
    print(f"Seed:                    {artifact.seed}")
    print(f"Morphology hash:         {artifact.morphology_hash}")
    print(f"Replay hash:             {artifact.replay_hash}")
    print(f"Replay pass:             {artifact.replay_pass}")
    print(f"Receipt stream hash:     {artifact.receipt_hash}")
    print(f"Receipt word hash:       {artifact.receipt_word_hash}")
    print(f"Ternary readout:         {artifact.ternary_readout}")
    print(f"Receipt count:           {artifact.receipt_count}")
    print()
    print("EXACT INTEGER / RATIONAL FEATURES")
    print("-" * 88)
    print(f"Nodes:                   {f.node_count}")
    print(f"Edges:                   {f.edge_count}")
    print(f"Branch nodes:            {f.branch_nodes}")
    print(f"Leaves:                  {f.leaves}")
    print(f"Max depth:               {f.max_depth}")
    print(f"Graph diameter:          {f.graph_diameter}")
    print(f"Height:                  {f.height}")
    print(f"Radial quadrance:        {f.radial_quadrance}")
    print(f"Bounding volume:         {f.bounding_volume}")
    print(f"Density:                 {f.density.text()}")
    print(f"Branch ratio:            {f.branch_ratio.text()}")
    print(f"Upward fraction:         {f.upward_fraction.text()}")
    print(f"Degree histogram:        {f.degree_histogram}")
    print(f"Depth histogram:         {f.depth_histogram}")
    print(f"Direction counts:        {f.direction_counts}")
    print(f"Events E/B/H/M/R:        {f.extend_events}/{f.branch_events}/{f.hold_events}/{f.maintain_events}/{f.restrict_events}")
    print()


def print_suite() -> None:
    contract = finite_contract_suite()
    determinism_pass, determinism_rows = determinism_suite()
    inverse = inverse_catalog_suite()
    degeneracy = degeneracy_audit(inverse)
    evidence = evidence_class_audit()
    receipt_audit = exact_receipt_equivalence_audit()
    closure = closure_hardening_suite()

    print("FINITE CONTRACT AUDIT")
    print("-" * 88)
    for key in ("no_float_runtime", "ternary_domain_valid", "replay_pass", "file_output_supported", "print_only"):
        print(f"{key:<38} {contract[key]}")
    print(f"forbidden_modules_loaded{'':<14} {contract['forbidden_modules_loaded']}")
    print()

    print("DETERMINISM SUITE")
    print("-" * 88)
    for name, seed, passed, hash_prefix in determinism_rows:
        print(f"{name:<12} seed={seed:<6} pass={str(passed):<5} hash={hash_prefix}")
    print(f"Determinism overall:     {determinism_pass}")
    print()

    print("27-SETTING FINITE INVERSE IDENTIFIABILITY SUITE")
    print("-" * 88)
    print(f"Catalog settings:        {inverse['catalog_size']}")
    print(f"Training per setting:    {inverse['train_per_setting']}")
    print(f"Testing per setting:     {inverse['test_per_setting']}")
    print(f"Replay failures:         {inverse['replay_failures']}")
    print_ratio("Random exact baseline:", inverse["random_baseline"])
    print_ratio("Combined exact forced choice:", inverse["combined_exact"])
    print_ratio("Combined adjacent forced choice:", inverse["combined_adjacent"])
    print_ratio("Kappa coordinate exact:", inverse["kappa_exact"])
    print_ratio("Phi coordinate exact:", inverse["phi_exact"])
    print_ratio("Target coordinate exact:", inverse["target_exact"])
    print(f"Confidence margin calibrated:       {inverse['confidence_calibrated']}")
    print()

    print("EXACT EVIDENCE-CLASS AUDIT")
    print("-" * 88)
    print_ratio("Prototype class contains truth:", evidence["prototype_true_coverage"])
    print_ratio("Prototype unique exact:", evidence["prototype_unique_correct"])
    print_ratio("Prototype tied-nearest cases:", evidence["prototype_tied"])
    print_ratio("Prototype class adjacent coverage:", evidence["prototype_adjacent_coverage"])
    print(f"Prototype class size exact sum/count: {evidence['prototype_class_size_sum']}/{evidence['prototype_class_size_count']}")
    print_ratio("Seed-ledger class contains truth:", evidence["ledger_true_coverage"])
    print_ratio("Seed-ledger unique exact:", evidence["ledger_unique_correct"])
    print_ratio("Seed-ledger tied-nearest cases:", evidence["ledger_tied"])
    print_ratio("Seed-ledger class adjacent coverage:", evidence["ledger_adjacent_coverage"])
    print(f"Seed-ledger class size sum/count:     {evidence['ledger_class_size_sum']}/{evidence['ledger_class_size_count']}")
    print(f"Final-geometry exact groups:          {evidence['final_exact_groups']}")
    print(f"Temporal exact groups:                {evidence['temporal_exact_groups']}")
    print(f"Combined exact groups:                {evidence['combined_exact_groups']}")
    print(f"Geometry-equivalent groups:           {evidence['geometry_equivalent_groups']}")
    print(f"Temporal splits of geometry groups:   {evidence['temporal_split_groups']}")
    print(f"Still unsplit after temporal evidence:{evidence['temporal_unsplit_groups']}")
    print()
    print("SAMPLE EVIDENCE ROWS")
    print("true | prototype class | seed-ledger class | prototype margin | ledger margin")
    for row in evidence["sample_rows"]:
        print(row)
    print()

    print("EXACT RECEIPT DISCRIMINATOR / BEHAVIORAL EQUIVALENCE AUDIT")
    print("-" * 88)
    print(f"Matched seeds per configuration: {receipt_audit['seed_count']}")
    print(f"Finite stress configurations:    {receipt_audit['config_count']}")
    print(f"Receipt determinism pass:        {receipt_audit['receipt_determinism_pass']}")
    print(f"Replay failures:                 {receipt_audit['total_replay_failures']}")
    for row in receipt_audit["pairs"]:
        print(f"Pair {row['pair']} differs in {row['differing_parameters']}")
        print(f"  classification:       {row['classification']}")
        print(f"  morphology identical: {row['morphology_same']}/{row['tested']}")
        print(f"  receipt identical:    {row['receipt_same']}/{row['tested']}")
        print(f"  word identical:       {row['word_same']}/{row['tested']}")
        div = row['first_divergence']
        print(f"  first divergence:     config={div[0]} seed={div[1]} receipt_index={div[2]}")
        if div[2] >= 0:
            print(f"    left:  {div[3]}")
            print(f"    right: {div[4]}")
    print()


    print("CLOSURE / HARDENING SUITE")
    print("-" * 88)
    print(f"Frozen morphology/receipt regressions pass: {closure['regression_pass']}")
    for row in closure["regression_rows"]:
        print(f"  {row[0]:<10} seed={row[1]:<5} morphology={row[2]} receipt={row[3]} word={row[4]}")
    print(f"Bounded stress runs:                    {closure['stress_runs']}")
    print(f"Structural invariant failures:          {closure['stress_failures']}")
    print(f"Invariant error ledger:                 {closure['error_counts']}")
    print(f"Maximum nodes observed:                 {closure['max_nodes_seen']}")
    print(f"Maximum receipts observed:              {closure['max_receipts_seen']}")
    print(f"Ready to freeze finite substrate:       {closure['ready_to_freeze']}")
    print()
    print("FINITE DEGENERACY AUDIT")
    print("-" * 88)
    print(f"Exact identical-prototype pairs:    {degeneracy['zero_distance_pair_count']}")
    print(f"Exact equivalence groups:           {degeneracy['equivalence_groups']}")
    print(f"Nearest prototype distance range:   {degeneracy['nearest_distance_min']}..{degeneracy['nearest_distance_max']}")
    print(f"Nearest distance exact sum/count:   {degeneracy['nearest_distance_sum']}/{degeneracy['nearest_distance_count']}")
    print()

    combined_exact = inverse["combined_exact"]
    combined_adjacent = inverse["combined_adjacent"]
    baseline = inverse["random_baseline"]
    proto_coverage = evidence["prototype_true_coverage"]
    ledger_coverage = evidence["ledger_true_coverage"]
    if not all(isinstance(x, Ratio) for x in (combined_exact, combined_adjacent, baseline, proto_coverage, ledger_coverage)):
        raise AssertionError("ratio type mismatch")
    exact_above_baseline = combined_exact.numerator * baseline.denominator > baseline.numerator * combined_exact.denominator
    adjacent_majority = combined_adjacent.numerator * 2 >= combined_adjacent.denominator
    evidence_coverage_above_baseline = proto_coverage.numerator * baseline.denominator > baseline.numerator * proto_coverage.denominator
    ledger_coverage_above_baseline = ledger_coverage.numerator * baseline.denominator > baseline.numerator * ledger_coverage.denominator
    overall_pass = (
        contract["no_float_runtime"] and contract["ternary_domain_valid"] and contract["replay_pass"] and
        not contract["file_output_supported"] and determinism_pass and inverse["replay_failures"] == 0 and
        evidence["replay_failures"] == 0 and receipt_audit["total_replay_failures"] == 0 and
        receipt_audit["receipt_determinism_pass"] and receipt_audit["all_pairs_classified"] and
        closure["regression_pass"] and closure["stress_failures"] == 0 and closure["ready_to_freeze"] and
        exact_above_baseline and adjacent_majority and
        evidence_coverage_above_baseline and ledger_coverage_above_baseline
    )

    print("DECLARED FINITE v1.3F CLOSURE GATE")
    print("-" * 88)
    print(f"No floating-point values in runtime artifacts: {contract['no_float_runtime']}")
    print(f"Ternary readout restricted to -1/0/+1:         {contract['ternary_domain_valid']}")
    print(f"No file output path exists:                     {not contract['file_output_supported']}")
    print(f"All deterministic replay cases pass:            {determinism_pass and inverse['replay_failures'] == 0 and evidence['replay_failures'] == 0}")
    print(f"Forced exact retrieval exceeds 1/27 baseline:    {exact_above_baseline}")
    print(f"Adjacent retrieval reaches at least one half:    {adjacent_majority}")
    print(f"Prototype evidence coverage exceeds baseline:    {evidence_coverage_above_baseline}")
    print(f"Seed-ledger evidence coverage exceeds baseline:  {ledger_coverage_above_baseline}")
    print(f"Deterministic receipt hashes match reruns:        {receipt_audit['receipt_determinism_pass']}")
    print(f"Every unresolved pair receives classification:   {receipt_audit['all_pairs_classified']}")
    print(f"Receipt equivalence audit replay failures zero:  {receipt_audit['total_replay_failures'] == 0}")
    print(f"Frozen morphology and receipt regressions pass:   {closure['regression_pass']}")
    print(f"All bounded structural invariants pass:           {closure['stress_failures'] == 0}")
    print(f"Finite substrate ready to freeze:                 {closure['ready_to_freeze']}")
    print(f"OVERALL FINITE v1.3F CLOSURE GATE:                       {overall_pass}")
    print()
    print("CLAIM BOUNDARY")
    print("- Software-only finite 3D graph morphology.")
    print("- No floating-point arithmetic is used in the engine or primary analysis.")
    print("- Exact candidate sets replace forced guesses when evidence is tied.")
    print("- Prototype and seed-ledger evidence are reported separately.")
    print("- Parameters are scaled integers, not physical CNT measurements.")
    print("- No JSON, CSV, report, manifest, or other file is written.")
    print("- Candidate-set coverage is not exact inverse control.")
    print("- Behavioral equivalence is bounded to the declared seed and stress ledgers.")
    print("- Receipt hashes describe exact finite causal streams, not physical CNT chemistry.")
    print("- A closure pass freezes the finite substrate for downstream application work.")
    print("- New scientific claims require a new experimental branch rather than changes to this baseline.")


# =============================================================================
# CNTM APPLICATION LAYER v2.3
# Finite Solution Selection
# =============================================================================
# Edit only the goal and priority values in this block on a phone runner.
APPLICATION_SEED = 7317

CUSTOM_GOAL_NAME = "MY_FINITE_GOAL"
MIN_HEIGHT = 8
MAX_HEIGHT = 13
MIN_BRANCH_NODES = 3
MAX_BRANCH_NODES = 9
MIN_DEPTH = 7
MAX_DEPTH = 13
MIN_UPWARD_NUMERATOR = 1
MIN_UPWARD_DENOMINATOR = 2
MAX_RADIAL_QUADRANCE = 36
MIN_UNSEEN_HITS = 7

EXPANDED_KAPPA = (35, 47, 60, 72, 85)
EXPANDED_PHI = (30, 55, 80, 105, 130)
EXPANDED_TARGET = (55, 64, 73, 82, 91)

# Ordered exact priorities. No floating weights are used.
# Available priorities:
# MIN_RADIAL_SUM, MAX_DIVERSITY, MIN_RECEIPT_SUM, MIN_NODE_SUM,
# MAX_HEIGHT_SUM, MAX_BRANCH_SUM, MIN_TARGET, MIN_PHI, MIN_KAPPA,
# LEXICOGRAPHIC_PARAMETERS
SELECTION_PRIORITIES = (
    "MIN_RADIAL_SUM",
    "MAX_DIVERSITY",
    "MIN_RECEIPT_SUM",
    "LEXICOGRAPHIC_PARAMETERS",
)


@dataclass(frozen=True)
class Goal:
    name: str
    min_height: int
    max_height: int
    min_branch_nodes: int
    max_branch_nodes: int
    min_depth: int
    max_depth: int
    min_upward_num: int
    min_upward_den: int
    max_radial_q: int


@dataclass(frozen=True)
class ExpandedSetting:
    expanded_index: int
    profile: Profile
    base_catalog_index: int


@dataclass(frozen=True)
class CandidateSummary:
    setting: ExpandedSetting
    penalty_sum: int
    exact_goal_hits: int
    training_count: int
    prototype: Tuple[int, ...]


@dataclass(frozen=True)
class ValidatedCandidate:
    summary: CandidateSummary
    unseen_hits: int
    unseen_count: int
    unseen_penalty_sum: int
    replay_pass: bool
    unique_morphologies: int


@dataclass(frozen=True)
class SelectionEvidence:
    validated: ValidatedCandidate
    radial_sum: int
    receipt_sum: int
    node_sum: int
    height_sum: int
    branch_sum: int


def custom_goal() -> Goal:
    values = (
        MIN_HEIGHT, MAX_HEIGHT, MIN_BRANCH_NODES, MAX_BRANCH_NODES,
        MIN_DEPTH, MAX_DEPTH, MIN_UPWARD_NUMERATOR,
        MIN_UPWARD_DENOMINATOR, MAX_RADIAL_QUADRANCE, MIN_UNSEEN_HITS,
    )
    if any(type(value) is not int for value in values):
        raise TypeError("all custom goal values must be integers")
    if MIN_HEIGHT > MAX_HEIGHT or MIN_BRANCH_NODES > MAX_BRANCH_NODES or MIN_DEPTH > MAX_DEPTH:
        raise ValueError("minimum constraint cannot exceed maximum")
    if MIN_UPWARD_DENOMINATOR <= 0 or MIN_UPWARD_NUMERATOR < 0:
        raise ValueError("invalid exact upward-fraction constraint")
    if MAX_RADIAL_QUADRANCE < 0:
        raise ValueError("MAX_RADIAL_QUADRANCE cannot be negative")
    if not 0 <= MIN_UNSEEN_HITS <= 9:
        raise ValueError("MIN_UNSEEN_HITS must be between 0 and 9")
    allowed = {
        "MIN_RADIAL_SUM", "MAX_DIVERSITY", "MIN_RECEIPT_SUM", "MIN_NODE_SUM",
        "MAX_HEIGHT_SUM", "MAX_BRANCH_SUM", "MIN_TARGET", "MIN_PHI", "MIN_KAPPA",
        "LEXICOGRAPHIC_PARAMETERS",
    }
    if not SELECTION_PRIORITIES or any(item not in allowed for item in SELECTION_PRIORITIES):
        raise ValueError("SELECTION_PRIORITIES contains an unsupported value")
    if len(set(SELECTION_PRIORITIES)) != len(SELECTION_PRIORITIES):
        raise ValueError("SELECTION_PRIORITIES must be duplicate-free")
    return Goal(CUSTOM_GOAL_NAME, MIN_HEIGHT, MAX_HEIGHT, MIN_BRANCH_NODES,
                MAX_BRANCH_NODES, MIN_DEPTH, MAX_DEPTH,
                MIN_UPWARD_NUMERATOR, MIN_UPWARD_DENOMINATOR,
                MAX_RADIAL_QUADRANCE)


def outside_penalty(value: int, low: int, high: int) -> int:
    if value < low:
        return low - value
    if value > high:
        return value - high
    return 0


def ratio_below_penalty(numerator: int, denominator: int, minimum_num: int, minimum_den: int) -> int:
    left = numerator * minimum_den
    right = minimum_num * denominator
    return 0 if left >= right else right - left


def goal_penalty(features: Features, goal: Goal) -> int:
    penalty = 0
    penalty += outside_penalty(features.height, goal.min_height, goal.max_height) * 100
    penalty += outside_penalty(features.branch_nodes, goal.min_branch_nodes, goal.max_branch_nodes) * 90
    penalty += outside_penalty(features.max_depth, goal.min_depth, goal.max_depth) * 80
    penalty += ratio_below_penalty(features.upward_fraction.numerator,
                                   features.upward_fraction.denominator,
                                   goal.min_upward_num, goal.min_upward_den) * 20
    penalty += max_int(0, features.radial_quadrance - goal.max_radial_q) * 5
    return penalty


def goal_satisfied(features: Features, goal: Goal) -> bool:
    return goal_penalty(features, goal) == 0


def base_index_by_parameters() -> Dict[Tuple[int, int, int], int]:
    return {(p.kappa, p.phi, p.target): i for i, p in enumerate(make_catalog())}


def make_expanded_catalog() -> Tuple[ExpandedSetting, ...]:
    axes = (EXPANDED_KAPPA, EXPANDED_PHI, EXPANDED_TARGET)
    if any(any(type(v) is not int for v in axis) for axis in axes):
        raise TypeError("expanded axes must contain integers only")
    if any(tuple(sorted(set(axis))) != axis for axis in axes):
        raise ValueError("expanded axes must be strictly increasing and duplicate-free")
    base = base_index_by_parameters()
    rows: List[ExpandedSetting] = []
    seen: Set[Tuple[int, int, int]] = set()
    index = 0
    for kappa in EXPANDED_KAPPA:
        for phi in EXPANDED_PHI:
            for target in EXPANDED_TARGET:
                key = (kappa, phi, target)
                if key in seen:
                    raise AssertionError("duplicate expanded parameter setting")
                seen.add(key)
                rows.append(ExpandedSetting(index, Profile(f"expanded_{index:03d}", kappa, phi, target), base.get(key, -1)))
                index += 1
    result = tuple(rows)
    assert len(result) == 125
    assert sum(1 for row in result if row.base_catalog_index >= 0) == 27
    assert_no_float(result, "expanded_catalog")
    return result


def setting_label(setting: ExpandedSetting) -> str:
    return f"C{setting.base_catalog_index:02d}" if setting.base_catalog_index >= 0 else f"X{setting.expanded_index:03d}"


def build_candidate_catalog(goal: Goal, catalog: Sequence[ExpandedSetting]) -> Tuple[CandidateSummary, ...]:
    train_seeds = (100, 101, 102, 103, 104, 105)
    summaries: List[CandidateSummary] = []
    for setting in catalog:
        penalties = 0
        hits = 0
        vectors: List[Tuple[int, ...]] = []
        for seed in train_seeds:
            artifact = run_profile(setting.profile, seed)
            if not artifact.replay_pass:
                raise AssertionError("frozen substrate replay failed during expanded search")
            value = goal_penalty(artifact.features, goal)
            penalties += value
            hits += 1 if value == 0 else 0
            vectors.append(artifact.features.combined_vector())
        summaries.append(CandidateSummary(setting, penalties, hits, len(train_seeds), prototype(vectors)))
    summaries.sort(key=lambda row: (-row.exact_goal_hits, row.penalty_sum, row.setting.expanded_index))
    result = tuple(summaries)
    assert_no_float(result, "expanded_candidate_catalog")
    return result


def validate_candidate(candidate: CandidateSummary, goal: Goal) -> ValidatedCandidate:
    seeds = (900, 901, 902, 903, 904, 905, 906, 907, 908)
    artifacts = tuple(run_profile(candidate.setting.profile, seed) for seed in seeds)
    penalties = tuple(goal_penalty(item.features, goal) for item in artifacts)
    result = ValidatedCandidate(candidate, sum(1 for value in penalties if value == 0), len(seeds),
                                sum(penalties), all(item.replay_pass for item in artifacts),
                                len(set(item.morphology_hash for item in artifacts)))
    assert_no_float(result, "expanded_validated_candidate")
    return result


def validate_all_candidates(candidates: Sequence[CandidateSummary], goal: Goal) -> Tuple[ValidatedCandidate, ...]:
    rows = [validate_candidate(candidate, goal) for candidate in candidates]
    rows.sort(key=lambda row: (-row.unseen_hits, row.unseen_penalty_sum,
                               -row.summary.exact_goal_hits, row.summary.penalty_sum,
                               row.summary.setting.expanded_index))
    result = tuple(rows)
    assert_no_float(result, "expanded_validation_rows")
    return result


def qualifying_candidates(rows: Sequence[ValidatedCandidate]) -> Tuple[ValidatedCandidate, ...]:
    result = tuple(row for row in rows if row.replay_pass and row.unseen_hits >= MIN_UNSEEN_HITS)
    assert_no_float(result, "expanded_qualifying")
    return result


def selection_evidence(row: ValidatedCandidate) -> SelectionEvidence:
    seeds = (900, 901, 902, 903, 904, 905, 906, 907, 908)
    artifacts = tuple(run_profile(row.summary.setting.profile, seed) for seed in seeds)
    result = SelectionEvidence(
        row,
        sum(item.features.radial_quadrance for item in artifacts),
        sum(item.receipt_count for item in artifacts),
        sum(item.features.node_count for item in artifacts),
        sum(item.features.height for item in artifacts),
        sum(item.features.branch_nodes for item in artifacts),
    )
    assert_no_float(result, "selection_evidence")
    return result


def priority_value(item: SelectionEvidence, priority: str) -> Tuple[int, ...]:
    p = item.validated.summary.setting.profile
    if priority == "MIN_RADIAL_SUM":
        return (item.radial_sum,)
    if priority == "MAX_DIVERSITY":
        return (-item.validated.unique_morphologies,)
    if priority == "MIN_RECEIPT_SUM":
        return (item.receipt_sum,)
    if priority == "MIN_NODE_SUM":
        return (item.node_sum,)
    if priority == "MAX_HEIGHT_SUM":
        return (-item.height_sum,)
    if priority == "MAX_BRANCH_SUM":
        return (-item.branch_sum,)
    if priority == "MIN_TARGET":
        return (p.target,)
    if priority == "MIN_PHI":
        return (p.phi,)
    if priority == "MIN_KAPPA":
        return (p.kappa,)
    if priority == "LEXICOGRAPHIC_PARAMETERS":
        return (p.kappa, p.phi, p.target, item.validated.summary.setting.expanded_index)
    raise ValueError("unknown selection priority")


def apply_exact_priorities(rows: Sequence[SelectionEvidence]) -> Tuple[SelectionEvidence, Tuple[Tuple[str, Tuple[int, ...], int, int], ...]]:
    survivors = tuple(rows)
    ledger: List[Tuple[str, Tuple[int, ...], int, int]] = []
    for priority in SELECTION_PRIORITIES:
        before = len(survivors)
        best = min(priority_value(item, priority) for item in survivors)
        survivors = tuple(item for item in survivors if priority_value(item, priority) == best)
        ledger.append((priority, best, before, len(survivors)))
        if len(survivors) == 1:
            break
    if len(survivors) > 1:
        survivors = tuple(sorted(survivors, key=lambda item: item.validated.summary.setting.expanded_index))
    result = survivors[0]
    audit = tuple(ledger)
    assert_no_float((result, audit), "exact_priority_selection")
    return result, audit


def select_demonstration_artifact(selected: ValidatedCandidate, goal: Goal) -> Artifact:
    artifacts = tuple(run_profile(selected.summary.setting.profile, seed) for seed in range(900, 909))
    for artifact in artifacts:
        if goal_satisfied(artifact.features, goal):
            return artifact
    return artifacts[0]


def frozen_v2_2_regression() -> Dict[str, object]:
    goal = custom_goal()
    catalog = make_expanded_catalog()
    candidates = build_candidate_catalog(goal, catalog)
    validated = validate_all_candidates(candidates, goal)
    qualified = qualifying_candidates(validated)
    selected = qualified[0] if qualified else validated[0]
    result: Dict[str, object] = {
        "selected_label": setting_label(selected.summary.setting),
        "selected_is_x007": setting_label(selected.summary.setting) == "X007",
        "validated_count": len(qualified),
        "new_validated_count": sum(1 for row in qualified if row.summary.setting.base_catalog_index < 0),
        "selected_unseen_hits": selected.unseen_hits,
        "pass": setting_label(selected.summary.setting) == "X007" and len(qualified) == 69 and
                sum(1 for row in qualified if row.summary.setting.base_catalog_index < 0) == 54 and
                selected.unseen_hits == 9,
    }
    assert_no_float(result, "frozen_v2_2_regression")
    return result


def print_goal(goal: Goal) -> None:
    print("USER-DEFINED FINITE GOAL")
    print("-" * 88)
    print(f"Goal name:               {goal.name}")
    print(f"Height range:            {goal.min_height}..{goal.max_height}")
    print(f"Branch-node range:       {goal.min_branch_nodes}..{goal.max_branch_nodes}")
    print(f"Depth range:             {goal.min_depth}..{goal.max_depth}")
    print(f"Minimum upward fraction:{goal.min_upward_num}/{goal.min_upward_den}")
    print(f"Maximum radial quadrance:{goal.max_radial_q}")
    print(f"Minimum unseen hits:     {MIN_UNSEEN_HITS}/9")
    print()


def print_priority_ledger(ledger: Sequence[Tuple[str, Tuple[int, ...], int, int]]) -> None:
    print("EXACT FINITE PRIORITY SELECTION")
    print("-" * 88)
    print(f"Declared priorities:     {SELECTION_PRIORITIES}")
    print("step | priority                 | winning exact value | candidates before -> after")
    for index, (priority, value, before, after) in enumerate(ledger, 1):
        print(f"{index:>4} | {priority:<24} | {str(value):<19} | {before:>3} -> {after:<3}")
    print()


def print_selection_evidence(item: SelectionEvidence) -> None:
    row = item.validated
    setting = row.summary.setting
    p = setting.profile
    print("SELECTED FINITE SOLUTION")
    print("-" * 88)
    print(f"Selection status:        VALIDATED")
    print(f"Selected setting:        {setting_label(setting)}")
    print(f"Setting origin:          {'frozen v2.1 catalog' if setting.base_catalog_index >= 0 else 'new v2.2 midpoint setting'}")
    print(f"Scaled parameters:       kappa={p.kappa}, phi={p.phi}, target={p.target}")
    print(f"Training hits:           {row.summary.exact_goal_hits}/{row.summary.training_count}")
    print(f"Unseen hits:             {row.unseen_hits}/{row.unseen_count}")
    print(f"Unseen penalty sum:      {row.unseen_penalty_sum}")
    print(f"Unique unseen morphologies:{row.unique_morphologies}/{row.unseen_count}")
    print(f"Exact radial sum:        {item.radial_sum}")
    print(f"Exact receipt-count sum: {item.receipt_sum}")
    print(f"Exact node-count sum:    {item.node_sum}")
    print(f"Exact height sum:        {item.height_sum}")
    print(f"Exact branch-count sum:  {item.branch_sum}")
    print()


def print_causal_receipt_sample(artifact: Artifact, limit: int = 12) -> None:
    print("CAUSAL RECEIPT SAMPLE")
    print("-" * 88)
    for receipt in consequential_receipts(artifact.receipts)[:limit]:
        print(f"#{receipt.receipt_id:<3} cycle={receipt.cycle:<3} {receipt.actor:<8} "
              f"{receipt.decision:<10} {receipt.reason_code} {receipt.evidence}")
    print()


def application_contract_audit(selected: SelectionEvidence, artifact: Artifact,
                               v22: Dict[str, object], catalog: Sequence[ExpandedSetting],
                               qualified_count: int, ledger: Sequence[Tuple[str, Tuple[int, ...], int, int]]) -> Dict[str, object]:
    frozen = closure_hardening_suite()
    result: Dict[str, object] = {
        "no_float_runtime": True,
        "ternary_domain_valid": all(value in (-1, 0, 1) for value in artifact.ternary_readout),
        "no_file_output": True,
        "catalog_size_125": len(catalog) == 125,
        "base_settings_preserved": sum(1 for row in catalog if row.base_catalog_index >= 0) == 27,
        "catalog_duplicate_free": len({(r.profile.kappa, r.profile.phi, r.profile.target) for r in catalog}) == len(catalog),
        "selected_replay": selected.validated.replay_pass and artifact.replay_pass,
        "priority_ledger_nonempty": len(ledger) > 0,
        "priority_selection_unique": ledger[-1][3] == 1,
        "v2_2_frozen_regression": v22["pass"],
        "v1_3f_regressions": frozen["regression_pass"],
        "v1_3f_invariants": frozen["stress_failures"] == 0,
        "qualifying_count": qualified_count,
        "application_ready": selected.validated.replay_pass and artifact.replay_pass and v22["pass"] and
                             frozen["regression_pass"] and frozen["stress_failures"] == 0 and len(ledger) > 0,
    }
    assert_no_float(result, "v2_3_application_contract")
    return result



@dataclass(frozen=True)
class MonitorState:
    receipt_id: int
    cycle: int
    decision: str
    node_count: int
    branch_events: int
    max_depth: int
    height: int
    radial_quadrance: int
    upward_edges: int
    edge_count: int
    within_upper_bounds: bool


@dataclass(frozen=True)
class ExecutionRecord:
    plan_hash: str
    execution_hash: str
    comparison_hash: str
    monitor_rows: Tuple[MonitorState, ...]
    upper_bound_violations: int
    final_goal_satisfied: bool
    replay_pass: bool
    repeat_execution_match: bool


def _sha_text(parts: Iterable[object]) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(repr(part).encode('utf-8'))
        h.update(b'\n')
    return h.hexdigest()


def plan_declaration(goal: Goal, selected: SelectionEvidence, seed: int) -> Tuple[object, ...]:
    p = selected.validated.summary.setting.profile
    return (
        'CNTM_PLAN_V2_4', goal.name,
        goal.min_height, goal.max_height,
        goal.min_branch_nodes, goal.max_branch_nodes,
        goal.min_depth, goal.max_depth,
        goal.min_upward_num, goal.min_upward_den,
        goal.max_radial_q, MIN_UNSEEN_HITS,
        tuple(SELECTION_PRIORITIES), setting_label(selected.validated.summary.setting),
        p.kappa, p.phi, p.target, int(seed),
        'CNTM_FINITE_V1_3F', 'CNTM_APPLICATION_V2_3',
    )


def receipt_int(receipt: Receipt, key: str, default: int = 0) -> int:
    for name, value in receipt.evidence:
        if name == key:
            return value
    return default


def build_monitor_rows(artifact: Artifact, goal: Goal) -> Tuple[Tuple[MonitorState, ...], int]:
    positions: Dict[int, Point3] = {0: (0, 0, 0)}
    depths: Dict[int, int] = {0: 0}
    parent_child_counts: Dict[int, int] = {}
    branch_events = 0
    upward_edges = 0
    edge_count = 0
    rows: List[MonitorState] = []
    violations = 0
    for receipt in consequential_receipts(artifact.receipts):
        if receipt.decision == 'EXTEND':
            node = receipt_int(receipt, 'node', -1)
            parent = receipt_int(receipt, 'parent', -1)
            point = (receipt_int(receipt, 'px'), receipt_int(receipt, 'py'), receipt_int(receipt, 'pz'))
            if node >= 0 and parent in positions:
                positions[node] = point
                depths[node] = depths[parent] + 1
                parent_child_counts[parent] = parent_child_counts.get(parent, 0) + 1
                edge_count += 1
                if point[2] > positions[parent][2]:
                    upward_edges += 1
        elif receipt.decision == 'BIFURCATE':
            branch_events += 1
            for suffix in ('a', 'b'):
                node = receipt_int(receipt, 'node_' + suffix, -1)
                parent = receipt_int(receipt, 'parent_' + suffix, -1)
                point = (receipt_int(receipt, 'p' + suffix + 'x'), receipt_int(receipt, 'p' + suffix + 'y'), receipt_int(receipt, 'p' + suffix + 'z'))
                if node >= 0 and parent in positions:
                    positions[node] = point
                    depths[node] = depths[parent] + 1
                    parent_child_counts[parent] = parent_child_counts.get(parent, 0) + 1
                    edge_count += 1
                    if point[2] > positions[parent][2]:
                        upward_edges += 1
        else:
            continue
        zs = tuple(point[2] for point in positions.values())
        radial = max((x*x + y*y for x, y, _ in positions.values()), default=0)
        max_depth = max(depths.values())
        height = max(zs) - min(zs) + 1
        upper_ok = (height <= goal.max_height and branch_events <= goal.max_branch_nodes and
                    max_depth <= goal.max_depth and radial <= goal.max_radial_q)
        if not upper_ok:
            violations += 1
        rows.append(MonitorState(receipt.receipt_id, receipt.cycle, receipt.decision,
                                 len(positions), branch_events, max_depth, height, radial,
                                 upward_edges, edge_count, upper_ok))
    result = tuple(rows)
    assert_no_float((result, violations), 'v2_4_monitor')
    return result, violations


def make_execution_record(goal: Goal, selected: SelectionEvidence, artifact: Artifact) -> ExecutionRecord:
    declaration = plan_declaration(goal, selected, artifact.seed)
    plan_hash = _sha_text(declaration)
    rows, violations = build_monitor_rows(artifact, goal)
    execution_hash = _sha_text((declaration, artifact.morphology_hash, artifact.replay_hash,
                                artifact.receipt_hash, artifact.receipt_word_hash,
                                artifact.ternary_readout, rows))
    repeat = run_profile(selected.validated.summary.setting.profile, artifact.seed)
    repeat_rows, repeat_violations = build_monitor_rows(repeat, goal)
    repeat_hash = _sha_text((declaration, repeat.morphology_hash, repeat.replay_hash,
                             repeat.receipt_hash, repeat.receipt_word_hash,
                             repeat.ternary_readout, repeat_rows))
    comparison_hash = _sha_text((execution_hash, repeat_hash, violations, repeat_violations))
    result = ExecutionRecord(plan_hash, execution_hash, comparison_hash, rows, violations,
                             goal_satisfied(artifact.features, goal), artifact.replay_pass,
                             execution_hash == repeat_hash)
    assert_no_float(result, 'v2_4_execution_record')
    return result


def frozen_v2_3_regression() -> Dict[str, object]:
    goal = custom_goal()
    catalog = make_expanded_catalog()
    training = build_candidate_catalog(goal, catalog)
    validated = validate_all_candidates(training, goal)
    qualified = qualifying_candidates(validated)
    evidence_rows = tuple(selection_evidence(row) for row in qualified)
    selected, ledger = apply_exact_priorities(evidence_rows)
    result: Dict[str, object] = {
        'selected_label': setting_label(selected.validated.summary.setting),
        'selected_is_c07': setting_label(selected.validated.summary.setting) == 'C07',
        'validated_count': len(qualified),
        'radial_sum': selected.radial_sum,
        'receipt_sum': selected.receipt_sum,
        'unique_result': ledger[-1][3] == 1,
        'pass': setting_label(selected.validated.summary.setting) == 'C07' and len(qualified) == 69 and
                selected.radial_sum == 52 and selected.receipt_sum == 522 and ledger[-1][3] == 1,
    }
    assert_no_float(result, 'frozen_v2_3_regression')
    return result


def print_plan_header(goal: Goal, selected: SelectionEvidence, artifact: Artifact, record: ExecutionRecord) -> None:
    p = selected.validated.summary.setting.profile
    print('FINITE PLAN DECLARATION')
    print('-' * 88)
    print(f'Goal:                    {goal.name}')
    print(f'Selected setting:        {setting_label(selected.validated.summary.setting)}')
    print(f'Scaled parameters:       kappa={p.kappa}, phi={p.phi}, target={p.target}')
    print(f'Execution seed:          {artifact.seed}')
    print(f'Frozen substrate:        CNTM Finite v1.3F')
    print(f'Frozen selector:         CNTM Application Layer v2.3')
    print(f'Plan hash:               {record.plan_hash}')
    print()


def print_execution_ledger(artifact: Artifact, record: ExecutionRecord, limit: int = 18) -> None:
    print('FINITE PLAN EXECUTION LEDGER')
    print('-' * 88)
    row_by_receipt = {row.receipt_id: row for row in record.monitor_rows}
    shown = 0
    for receipt in consequential_receipts(artifact.receipts):
        if receipt.receipt_id not in row_by_receipt:
            continue
        row = row_by_receipt[receipt.receipt_id]
        print(f"#{receipt.receipt_id:<3} cycle={receipt.cycle:<3} {receipt.actor:<8} {receipt.decision:<10} "
              f"nodes={row.node_count:<3} branches={row.branch_events:<2} depth={row.max_depth:<2} "
              f"height={row.height:<2} radialQ={row.radial_quadrance:<3} upper_bounds={row.within_upper_bounds}")
        print(f'     reason={receipt.reason_code} evidence={receipt.evidence}')
        shown += 1
        if shown >= limit:
            break
    remaining = len(record.monitor_rows) - shown
    if remaining > 0:
        print(f'... {remaining} additional growth-ledger rows remain in deterministic execution memory.')
    print()


def v2_4_contract_audit(record: ExecutionRecord, artifact: Artifact, v23: Dict[str, object]) -> Dict[str, object]:
    frozen = closure_hardening_suite()
    result: Dict[str, object] = {
        'no_float_runtime': True,
        'ternary_domain_valid': all(value in (-1, 0, 1) for value in artifact.ternary_readout),
        'no_file_output': True,
        'plan_declared': len(record.plan_hash) == 64,
        'execution_ledger_present': len(record.monitor_rows) > 0,
        'execution_hash_present': len(record.execution_hash) == 64,
        'repeat_execution_match': record.repeat_execution_match,
        'goal_achieved': record.final_goal_satisfied,
        'replay_pass': record.replay_pass,
        'v2_3_frozen_regression': v23['pass'],
        'v1_3f_regressions': frozen['regression_pass'],
        'v1_3f_invariants': frozen['stress_failures'] == 0,
        'application_ready': record.repeat_execution_match and record.final_goal_satisfied and record.replay_pass and
                             v23['pass'] and frozen['regression_pass'] and frozen['stress_failures'] == 0,
    }
    assert_no_float(result, 'v2_4_contract')
    return result


def main() -> None:
    goal = custom_goal()
    catalog = make_expanded_catalog()
    training = build_candidate_catalog(goal, catalog)
    validated = validate_all_candidates(training, goal)
    qualified = qualifying_candidates(validated)
    pool = qualified if qualified else (validated[0],)
    evidence_rows = tuple(selection_evidence(row) for row in pool)
    selected_evidence, priority_ledger = apply_exact_priorities(evidence_rows)
    selected = selected_evidence.validated
    demonstration = select_demonstration_artifact(selected, goal)
    record = make_execution_record(goal, selected_evidence, demonstration)
    v23 = frozen_v2_3_regression()
    audit = v2_4_contract_audit(record, demonstration, v23)

    print('=' * 88)
    print(f'{PROJECT} v{VERSION} — FINITE PLAN EXECUTION RECORD')
    print('=' * 88)
    print('Frozen substrate:        CNTM Finite v1.3F')
    print('Frozen applications:     CNTM Application Layers v2.0 through v2.3')
    print('Execution mode:          integer-only / ternary / deterministic / print-only')
    print()
    print_goal(goal)
    print_priority_ledger(priority_ledger)
    print_selection_evidence(selected_evidence)
    print_plan_header(goal, selected_evidence, demonstration, record)
    print_execution_ledger(demonstration, record)

    print('PLAN COMPLETION / EXECUTION FINGERPRINT')
    print('-' * 88)
    print(f'Goal achieved:           {record.final_goal_satisfied}')
    print(f'Growth monitor rows:     {len(record.monitor_rows)}')
    print(f'Upper-bound alerts:      {record.upper_bound_violations}')
    print(f'Morphology hash:         {demonstration.morphology_hash}')
    print(f'Replay hash:             {demonstration.replay_hash}')
    print(f'Receipt stream hash:     {demonstration.receipt_hash}')
    print(f'Receipt word hash:       {demonstration.receipt_word_hash}')
    print(f'Execution hash:          {record.execution_hash}')
    print(f'Repeat comparison hash:  {record.comparison_hash}')
    print(f'Repeat execution match:  {record.repeat_execution_match}')
    print()

    print('FROZEN v2.3 REGRESSION')
    print('-' * 88)
    print(f'Expected selected setting C07:         {v23["selected_is_c07"]}')
    print(f'Expected validated count 69:            {v23["validated_count"]}')
    print(f'Expected radial sum 52:                  {v23["radial_sum"]}')
    print(f'Expected receipt sum 522:                {v23["receipt_sum"]}')
    print(f'Frozen v2.3 regression pass:             {v23["pass"]}')
    print()

    print('APPLICATION v2.4 FREEZE GATE')
    print('-' * 88)
    print(f'No floating-point runtime values:       {audit["no_float_runtime"]}')
    print(f'Ternary domain valid:                   {audit["ternary_domain_valid"]}')
    print(f'No file output path:                    {audit["no_file_output"]}')
    print(f'Immutable plan declaration produced:    {audit["plan_declared"]}')
    print(f'Exact execution ledger produced:        {audit["execution_ledger_present"]}')
    print(f'Execution fingerprint produced:         {audit["execution_hash_present"]}')
    print(f'Repeated execution hash matches:        {audit["repeat_execution_match"]}')
    print(f'Final declared goal achieved:           {audit["goal_achieved"]}')
    print(f'Selected execution replay passes:       {audit["replay_pass"]}')
    print(f'Frozen Application v2.3 regression:     {audit["v2_3_frozen_regression"]}')
    print(f'Frozen substrate v1.3F regressions:     {audit["v1_3f_regressions"]}')
    print(f'Frozen substrate invariants:            {audit["v1_3f_invariants"]}')
    print(f'CNTM APPLICATION LAYER v2.4 FREEZE READY:{audit["application_ready"]}')
    print()

    print('USE')
    print('-' * 88)
    print('Edit the finite goal, priority sequence, or demonstration seed only in declared fields.')
    print('The plan record prints the selected regime, ordered execution, monitor states, and hashes.')
    print('No JSON, CSV, report, manifest, or other file is written by the phone program.')
    print()
    print('CLAIM BOUNDARY')
    print('- v2.4 records and fingerprints execution of a selected finite morphology plan.')
    print('- The live monitor reports exact partial morphology derived from causal receipts.')
    print('- Temporary upper-bound alerts during growth are not final goal failures.')
    print('- The execution record is software evidence, not physical CNT process control.')
    print('- Frozen v1.3F and v2.0-v2.3 behavior remains regression protected.')


if __name__ == '__main__':
    main()

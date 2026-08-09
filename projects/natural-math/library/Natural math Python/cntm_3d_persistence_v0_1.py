#!/usr/bin/env python3
"""CNTM 3D Morphology-Memory Persistence Harness v0.1.

A standalone, standard-library-only experiment for online Python runners.

Research question
-----------------
Can strictly local, deterministic 3D growth rules leave a final morphology from
which the generating rule family can be recovered above a declared baseline?

This program is intentionally separate from Natural Math maze exploration.  It
imports no maze code and does not modify the frozen Natural Math v10.3.2 build.
It borrows only engineering disciplines: finite limits, local decisions,
receipts, replay, structural hashes, controls, and explicit claim boundaries.

Current claim boundary
----------------------
- This is a software growth-grammar experiment.
- "CNT-like" describes graph morphology only; no CNT chemistry is simulated.
- kappa, phi, and T are experimental boundary-condition parameters, not proof
  of physical resonance.
- Basin signatures are deterministic, lossy readouts, not native material
  symbols and not evidence of consciousness or a working memory device.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

Point3 = Tuple[int, int, int]
Edge3 = Tuple[int, int]
DIRS: Tuple[Point3, ...] = (
    (1, 0, 0), (-1, 0, 0),
    (0, 1, 0), (0, -1, 0),
    (0, 0, 1), (0, 0, -1),
)

PROJECT = "CNTM 3D MORPHOLOGY-MEMORY PERSISTENCE HARNESS"
VERSION = "0.1"


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_json(value: object) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def add3(a: Point3, b: Point3) -> Point3:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def sub3(a: Point3, b: Point3) -> Point3:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def dot3(a: Sequence[float], b: Sequence[float]) -> float:
    return float(a[0] * b[0] + a[1] * b[1] + a[2] * b[2])


def norm3(a: Sequence[float]) -> float:
    return math.sqrt(dot3(a, a))


def unit3(a: Sequence[float]) -> Tuple[float, float, float]:
    length = norm3(a)
    if length <= 1e-12:
        return 0.0, 0.0, 1.0
    return a[0] / length, a[1] / length, a[2] / length


def euclidean(a: Point3, b: Point3) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def point_text(p: Point3) -> str:
    return f"{p[0]},{p[1]},{p[2]}"


@dataclass(frozen=True)
class ConstraintProfile:
    name: str
    kappa: float
    phi: float
    target_stability: float
    description: str


PROFILES: Dict[str, ConstraintProfile] = {
    "cautious": ConstraintProfile(
        "cautious", 0.35, 0.30, 0.55,
        "Low coupling, low directional rotation, conservative branching.",
    ),
    "balanced": ConstraintProfile(
        "balanced", 0.65, 0.80, 0.78,
        "Intermediate coupling, directional bias, and persistence.",
    ),
    "aggressive": ConstraintProfile(
        "aggressive", 0.82, 1.40, 0.91,
        "High coupling and persistence with stronger branching pressure.",
    ),
}


@dataclass
class GrowthConfig:
    max_cycles: int = 70
    max_nodes: int = 220
    initial_energy: float = 25.0
    extend_cost: float = 1.0
    branch_cost: float = 2.2
    hold_threshold: float = 1.9
    maintenance_injection: float = 3.0
    maintenance_budget: float = 30.0
    max_holds_per_tip: int = 2
    world_radius: int = 14
    max_downward_depth: int = 2
    persistent: bool = True


@dataclass
class Tip:
    tip_id: int
    node_id: int
    direction: Point3
    energy: float
    age: int = 0
    hold_count: int = 0
    state: str = "active"


@dataclass(frozen=True)
class Receipt:
    receipt_id: int
    cycle: int
    actor: str
    decision: str
    reason: str
    local_evidence: Dict[str, object]
    consequence: str
    event_type: str
    entity_id: str


@dataclass
class MorphologyFeatures:
    node_count: int
    edge_count: int
    branch_nodes: int
    leaves: int
    max_depth: int
    graph_diameter: int
    height: int
    radial_extent: float
    bounding_volume: int
    density: float
    branch_ratio: float
    upward_fraction: float
    anisotropy: float
    mean_tortuosity: float
    degree_entropy: float
    effective_conductance: float
    hold_events: int
    maintain_events: int

    def classifier_vector(self) -> List[float]:
        return [
            float(self.node_count),
            self.branch_ratio,
            float(self.max_depth),
            float(self.height),
            self.radial_extent,
            self.density,
            self.upward_fraction,
            self.anisotropy,
            self.mean_tortuosity,
            self.degree_entropy,
            self.effective_conductance,
        ]


@dataclass
class RunArtifact:
    profile: str
    seed: int
    persistent: bool
    morphology_hash: str
    replay_hash: str
    replay_pass: bool
    basin_signature: str
    ternary_readout: List[int]
    features: MorphologyFeatures
    operator_counts: Dict[str, int]
    receipt_count: int
    nodes: Dict[int, Point3] = field(repr=False)
    edges: List[Edge3] = field(repr=False)
    receipts: List[Receipt] = field(repr=False)


class LocalGrowth3D:
    """Strictly local 3D graph growth with bounded maintenance energy."""

    def __init__(
        self,
        profile: ConstraintProfile,
        seed: int,
        config: Optional[GrowthConfig] = None,
    ) -> None:
        self.profile = profile
        self.seed = int(seed)
        self.config = config or GrowthConfig()
        self.rng = random.Random((self.seed << 8) ^ 0xC07A3D)

        self.nodes: Dict[int, Point3] = {0: (0, 0, 0)}
        self.node_by_pos: Dict[Point3, int] = {(0, 0, 0): 0}
        self.edges: List[Edge3] = []
        self.adjacency: Dict[int, Set[int]] = {0: set()}
        self.depth: Dict[int, int] = {0: 0}
        self.next_node_id = 1
        self.next_tip_id = 1
        self.tips: List[Tip] = [Tip(0, 0, (0, 0, 1), self.config.initial_energy)]
        self.receipts: List[Receipt] = []
        self.operator_counts: Counter[str] = Counter()
        self.maintenance_remaining = self.config.maintenance_budget
        self.cycle = 0

        field_horizontal = (math.cos(profile.phi), math.sin(profile.phi))
        self.field_direction = unit3((
            profile.kappa * field_horizontal[0],
            profile.kappa * field_horizontal[1],
            0.65 + 0.35 * profile.target_stability,
        ))

        self._receipt(
            "setup_gate",
            "admit software experiment",
            "the profile, seed, finite limits, and local lattice are fully specified",
            {
                "profile": profile.name,
                "kappa": profile.kappa,
                "phi": profile.phi,
                "T": profile.target_stability,
                "persistent": self.config.persistent,
                "max_cycles": self.config.max_cycles,
                "max_nodes": self.config.max_nodes,
                "maintenance_budget": self.config.maintenance_budget,
            },
            "local growth permitted",
            "setup",
            "run",
        )

    def _receipt(
        self,
        actor: str,
        decision: str,
        reason: str,
        evidence: Dict[str, object],
        consequence: str,
        event_type: str,
        entity_id: str,
    ) -> None:
        self.receipts.append(Receipt(
            receipt_id=len(self.receipts) + 1,
            cycle=self.cycle,
            actor=actor,
            decision=decision,
            reason=reason,
            local_evidence=evidence,
            consequence=consequence,
            event_type=event_type,
            entity_id=entity_id,
        ))

    def _within_world(self, p: Point3) -> bool:
        r = self.config.world_radius
        return (
            abs(p[0]) <= r
            and abs(p[1]) <= r
            and -self.config.max_downward_depth <= p[2] <= 2 * r
        )

    def _local_neighbors_occupied(self, p: Point3) -> int:
        return sum(1 for d in DIRS if add3(p, d) in self.node_by_pos)

    def _local_environment(self, p: Point3, direction: Point3, age: int) -> Dict[str, float]:
        crowding = self._local_neighbors_occupied(p) / 6.0
        alignment = (dot3(unit3(direction), self.field_direction) + 1.0) / 2.0
        upward = (direction[2] + 1.0) / 2.0
        radial = math.sqrt(p[0] ** 2 + p[1] ** 2)
        height = max(0, p[2])
        flux = max(0.0, 1.0 - 0.018 * radial - 0.009 * height)
        support = min(1.0, self._local_neighbors_occupied(p) / 3.0)
        age_stress = min(1.0, age / 18.0)
        return {
            "crowding": crowding,
            "alignment": alignment,
            "upward": upward,
            "flux": flux,
            "support": support,
            "age_stress": age_stress,
        }

    def _candidate_directions(self, tip: Tip) -> List[Tuple[float, Point3, Point3, Dict[str, float]]]:
        current = self.nodes[tip.node_id]
        candidates: List[Tuple[float, Point3, Point3, Dict[str, float]]] = []
        for direction in DIRS:
            target = add3(current, direction)
            if not self._within_world(target) or target in self.node_by_pos:
                continue
            env = self._local_environment(target, direction, tip.age)
            turn = 1.0 - (dot3(unit3(tip.direction), unit3(direction)) + 1.0) / 2.0
            deterministic_jitter = self.rng.uniform(-0.18, 0.18)
            score = (
                1.15 * env["flux"]
                + (0.80 + 1.20 * self.profile.kappa) * env["alignment"]
                + 0.85 * env["upward"]
                + 0.30 * env["support"]
                - 1.15 * env["crowding"]
                - 0.60 * turn
                - 0.25 * env["age_stress"]
                + deterministic_jitter
            )
            candidates.append((score, direction, target, env))
        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        return candidates

    def _branch_probability(self, best_env: Dict[str, float], tip: Tip) -> float:
        phase_factor = 0.5 + 0.5 * math.sin(self.profile.phi)
        p = (
            0.035
            + 0.30 * self.profile.kappa
            + 0.13 * phase_factor
            + 0.10 * self.profile.target_stability
            + 0.08 * best_env["flux"]
            - 0.20 * best_env["crowding"]
            - 0.08 * min(1.0, tip.age / 20.0)
        )
        return max(0.02, min(0.62, p))

    def _add_node_and_edge(self, parent: int, target: Point3, direction: Point3) -> int:
        node_id = self.next_node_id
        self.next_node_id += 1
        self.nodes[node_id] = target
        self.node_by_pos[target] = node_id
        self.edges.append((parent, node_id))
        self.adjacency.setdefault(parent, set()).add(node_id)
        self.adjacency[node_id] = {parent}
        self.depth[node_id] = self.depth[parent] + 1
        self._receipt(
            "growth_tip",
            f"deposit node {node_id}",
            "a locally selected unoccupied lattice position was accepted",
            {
                "parent": parent,
                "position": point_text(target),
                "direction": list(direction),
                "depth": self.depth[node_id],
            },
            "morphology graph gains one node and one edge",
            "node_created",
            str(node_id),
        )
        return node_id

    def _terminate(self, tip: Tip, reason: str, evidence: Dict[str, object]) -> None:
        tip.state = "terminated"
        self.operator_counts["RESTRICT"] += 1
        self._receipt(
            "growth_tip",
            f"restrict tip {tip.tip_id}",
            reason,
            {**evidence, "tip": tip.tip_id, "node": tip.node_id},
            "tip becomes inactive",
            "tip_state",
            str(tip.tip_id),
        )

    def _hold_or_terminate(self, tip: Tip, env: Dict[str, float]) -> None:
        stable_enough = (
            env["alignment"] >= 0.48
            and env["flux"] >= 0.30
            and env["crowding"] <= 0.72
        )
        can_maintain = (
            self.config.persistent
            and stable_enough
            and tip.hold_count < self.config.max_holds_per_tip
            and self.maintenance_remaining >= self.config.maintenance_injection
        )
        if not can_maintain:
            self._terminate(
                tip,
                "local energy is below the extension threshold and bounded maintenance is unavailable",
                {
                    "energy": round(tip.energy, 5),
                    "stable_enough": stable_enough,
                    "persistent": self.config.persistent,
                    "maintenance_remaining": round(self.maintenance_remaining, 5),
                },
            )
            return

        tip.state = "held"
        tip.hold_count += 1
        self.operator_counts["HOLD"] += 1
        self._receipt(
            "persistence_gate",
            f"hold tip {tip.tip_id}",
            "the tip cannot extend safely but retains a locally stable growth context",
            {
                "tip": tip.tip_id,
                "node": tip.node_id,
                "energy": round(tip.energy, 5),
                "hold_count": tip.hold_count,
                "alignment": round(env["alignment"], 5),
                "flux": round(env["flux"], 5),
                "crowding": round(env["crowding"], 5),
            },
            "tip pauses without being erased",
            "tip_state",
            str(tip.tip_id),
        )

        injection = min(self.config.maintenance_injection, self.maintenance_remaining)
        self.maintenance_remaining -= injection
        tip.energy += injection
        tip.state = "active"
        self.operator_counts["MAINTAIN"] += 1
        self._receipt(
            "maintenance_controller",
            f"maintain tip {tip.tip_id}",
            "a bounded maintenance reserve is spent to preserve a locally stable unfinished branch",
            {
                "tip": tip.tip_id,
                "injection": round(injection, 5),
                "energy_after": round(tip.energy, 5),
                "maintenance_remaining": round(self.maintenance_remaining, 5),
            },
            "tip returns to active state with finite added energy",
            "maintenance",
            str(tip.tip_id),
        )

    def _process_tip(self, tip: Tip) -> List[Tip]:
        if tip.state != "active":
            return []
        current = self.nodes[tip.node_id]
        current_env = self._local_environment(current, tip.direction, tip.age)

        if tip.energy < self.config.hold_threshold:
            self._hold_or_terminate(tip, current_env)
            return [tip] if tip.state == "active" else []

        candidates = self._candidate_directions(tip)
        if not candidates:
            self._terminate(
                tip,
                "every locally adjacent lattice position is occupied or outside the finite world",
                {"position": point_text(current), "energy": round(tip.energy, 5)},
            )
            return []

        best_score, best_direction, best_target, best_env = candidates[0]
        branch_p = self._branch_probability(best_env, tip)
        can_branch = (
            len(candidates) >= 2
            and tip.energy >= self.config.branch_cost + 0.5
            and len(self.nodes) + 2 <= self.config.max_nodes
        )
        do_branch = can_branch and self.rng.random() < branch_p

        if do_branch:
            second = candidates[1]
            _, direction2, target2, env2 = second
            child_energy = max(0.0, (tip.energy - self.config.branch_cost) / 2.0)
            node1 = self._add_node_and_edge(tip.node_id, best_target, best_direction)
            node2 = self._add_node_and_edge(tip.node_id, target2, direction2)
            tip.state = "branched"
            self.operator_counts["BIFURCATE"] += 1
            self._receipt(
                "growth_tip",
                f"bifurcate tip {tip.tip_id}",
                "two locally admissible directions exceeded the profile's bounded branching decision",
                {
                    "tip": tip.tip_id,
                    "parent_node": tip.node_id,
                    "branch_probability": round(branch_p, 5),
                    "chosen_scores": [round(best_score, 5), round(second[0], 5)],
                    "chosen_positions": [point_text(best_target), point_text(target2)],
                    "energy_before": round(tip.energy, 5),
                    "child_energy": round(child_energy, 5),
                    "local_env_1": {k: round(v, 5) for k, v in best_env.items()},
                    "local_env_2": {k: round(v, 5) for k, v in env2.items()},
                },
                "one active tip becomes two child tips",
                "operator",
                str(tip.tip_id),
            )
            child1 = Tip(self.next_tip_id, node1, best_direction, child_energy)
            self.next_tip_id += 1
            child2 = Tip(self.next_tip_id, node2, direction2, child_energy)
            self.next_tip_id += 1
            return [child1, child2]

        node = self._add_node_and_edge(tip.node_id, best_target, best_direction)
        old_energy = tip.energy
        tip.node_id = node
        tip.direction = best_direction
        tip.energy -= self.config.extend_cost
        tip.age += 1
        self.operator_counts["EXTEND"] += 1
        self._receipt(
            "growth_tip",
            f"extend tip {tip.tip_id}",
            "the highest-scoring local candidate preserves occupancy, world, and energy constraints",
            {
                "tip": tip.tip_id,
                "score": round(best_score, 5),
                "position": point_text(best_target),
                "energy_before": round(old_energy, 5),
                "energy_after": round(tip.energy, 5),
                "branch_probability": round(branch_p, 5),
                "local_env": {k: round(v, 5) for k, v in best_env.items()},
            },
            "tip advances by one lattice segment",
            "operator",
            str(tip.tip_id),
        )
        return [tip]

    def run(self) -> RunArtifact:
        for cycle in range(1, self.config.max_cycles + 1):
            self.cycle = cycle
            if not self.tips or len(self.nodes) >= self.config.max_nodes:
                break
            next_tips: List[Tip] = []
            for tip in sorted(self.tips, key=lambda t: t.tip_id):
                if len(self.nodes) >= self.config.max_nodes:
                    break
                next_tips.extend(self._process_tip(tip))
            self.tips = [t for t in next_tips if t.state == "active"]

        self._receipt(
            "run_controller",
            "freeze morphology",
            "the finite cycle, node, active-tip, or energy boundary ended growth",
            {
                "cycles_completed": self.cycle,
                "nodes": len(self.nodes),
                "edges": len(self.edges),
                "active_tips": len(self.tips),
                "maintenance_remaining": round(self.maintenance_remaining, 5),
            },
            "graph becomes immutable input to measurement and replay",
            "morphology_frozen",
            "morphology",
        )

        features = extract_features(
            self.nodes,
            self.edges,
            self.operator_counts,
        )
        snapshot = morphology_snapshot(self.nodes, self.edges)
        morphology_hash = sha256_json(snapshot)
        replay_nodes, replay_edges, replay_errors = replay_morphology(self.receipts)
        replay_snapshot = morphology_snapshot(replay_nodes, replay_edges)
        replay_hash = sha256_json(replay_snapshot)
        replay_pass = not replay_errors and replay_hash == morphology_hash
        readout = ternary_readout(features)
        signature = basin_signature(readout, features)

        self._receipt(
            "replay_auditor",
            "approve replay" if replay_pass else "reject replay",
            "receipt reconstruction matches the frozen morphology hash"
            if replay_pass else "receipt reconstruction differs from the frozen morphology",
            {
                "morphology_hash": morphology_hash,
                "replay_hash": replay_hash,
                "errors": replay_errors,
                "basin_signature": signature,
            },
            "run is replay-valid" if replay_pass else "run is quarantined",
            "audit",
            "replay",
        )

        return RunArtifact(
            profile=self.profile.name,
            seed=self.seed,
            persistent=self.config.persistent,
            morphology_hash=morphology_hash,
            replay_hash=replay_hash,
            replay_pass=replay_pass,
            basin_signature=signature,
            ternary_readout=readout,
            features=features,
            operator_counts=dict(sorted(self.operator_counts.items())),
            receipt_count=len(self.receipts),
            nodes=dict(self.nodes),
            edges=list(self.edges),
            receipts=list(self.receipts),
        )


def morphology_snapshot(nodes: Dict[int, Point3], edges: Iterable[Edge3]) -> Dict[str, object]:
    return {
        "nodes": [[node_id, *nodes[node_id]] for node_id in sorted(nodes)],
        "edges": [[min(a, b), max(a, b)] for a, b in sorted((min(a, b), max(a, b)) for a, b in edges)],
    }


def replay_morphology(receipts: Sequence[Receipt]) -> Tuple[Dict[int, Point3], List[Edge3], List[str]]:
    nodes: Dict[int, Point3] = {0: (0, 0, 0)}
    edges: List[Edge3] = []
    errors: List[str] = []
    expected_id = 1
    for receipt in receipts:
        if receipt.receipt_id != expected_id:
            errors.append(f"receipt sequence break: expected {expected_id}, got {receipt.receipt_id}")
        expected_id = receipt.receipt_id + 1
        if receipt.event_type != "node_created":
            continue
        try:
            node_id = int(receipt.entity_id)
            parent = int(receipt.local_evidence["parent"])
            position = tuple(int(x) for x in str(receipt.local_evidence["position"]).split(","))
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"receipt {receipt.receipt_id}: malformed node event ({exc})")
            continue
        if len(position) != 3:
            errors.append(f"receipt {receipt.receipt_id}: malformed 3D position")
            continue
        if node_id in nodes:
            errors.append(f"receipt {receipt.receipt_id}: duplicate node {node_id}")
            continue
        if parent not in nodes:
            errors.append(f"receipt {receipt.receipt_id}: unknown parent {parent}")
            continue
        nodes[node_id] = position  # type: ignore[assignment]
        edges.append((parent, node_id))
    return nodes, edges, errors


def build_adjacency(nodes: Dict[int, Point3], edges: Sequence[Edge3]) -> Dict[int, List[int]]:
    adjacency = {node_id: [] for node_id in nodes}
    for a, b in edges:
        adjacency[a].append(b)
        adjacency[b].append(a)
    for values in adjacency.values():
        values.sort()
    return adjacency


def bfs_distances(adjacency: Dict[int, List[int]], start: int) -> Dict[int, int]:
    dist = {start: 0}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current]:
            if neighbor not in dist:
                dist[neighbor] = dist[current] + 1
                queue.append(neighbor)
    return dist


def graph_diameter(adjacency: Dict[int, List[int]]) -> int:
    if not adjacency:
        return 0
    first = min(adjacency)
    d1 = bfs_distances(adjacency, first)
    far = max(d1, key=lambda n: (d1[n], n))
    d2 = bfs_distances(adjacency, far)
    return max(d2.values(), default=0)


def entropy(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def solve_linear_system(matrix: List[List[float]], vector: List[float]) -> Optional[List[float]]:
    """Deterministic Gaussian elimination with partial pivoting."""
    n = len(vector)
    if n == 0:
        return []
    a = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: (abs(a[row][col]), -row))
        if abs(a[pivot][col]) < 1e-12:
            return None
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
        pivot_value = a[col][col]
        for j in range(col, n + 1):
            a[col][j] /= pivot_value
        for row in range(n):
            if row == col:
                continue
            factor = a[row][col]
            if abs(factor) < 1e-15:
                continue
            for j in range(col, n + 1):
                a[row][j] -= factor * a[col][j]
    return [a[i][n] for i in range(n)]


def effective_conductance(nodes: Dict[int, Point3], edges: Sequence[Edge3]) -> float:
    """Simplified exact nodal conductance on the generated unit-resistor graph."""
    if len(nodes) <= 1 or not edges:
        return 0.0
    adjacency = build_adjacency(nodes, edges)
    max_z = max(p[2] for p in nodes.values())
    sink_candidates = sorted(node for node, p in nodes.items() if p[2] == max_z and node != 0)
    if not sink_candidates:
        return 0.0
    sinks = set(sink_candidates)
    source = 0
    unknown = sorted(node for node in nodes if node != source and node not in sinks)
    index = {node: i for i, node in enumerate(unknown)}
    matrix = [[0.0 for _ in unknown] for _ in unknown]
    vector = [0.0 for _ in unknown]

    for node in unknown:
        i = index[node]
        degree = len(adjacency[node])
        matrix[i][i] = float(degree)
        for neighbor in adjacency[node]:
            if neighbor == source:
                vector[i] += 1.0
            elif neighbor in sinks:
                pass
            else:
                matrix[i][index[neighbor]] -= 1.0

    voltages = solve_linear_system(matrix, vector)
    if voltages is None:
        return 0.0
    voltage = {source: 1.0, **{sink: 0.0 for sink in sinks}}
    voltage.update({node: voltages[index[node]] for node in unknown})
    current = sum(1.0 - voltage[neighbor] for neighbor in adjacency[source])
    return max(0.0, current)


def extract_features(
    nodes: Dict[int, Point3],
    edges: Sequence[Edge3],
    operator_counts: Dict[str, int],
) -> MorphologyFeatures:
    adjacency = build_adjacency(nodes, edges)
    degrees = [len(adjacency[node]) for node in sorted(nodes)]
    leaves = [node for node, degree in zip(sorted(nodes), degrees) if degree == 1 and node != 0]
    branch_nodes = sum(1 for degree in degrees if degree >= 3)
    root_dist = bfs_distances(adjacency, 0)
    max_depth = max(root_dist.values(), default=0)

    xs = [p[0] for p in nodes.values()]
    ys = [p[1] for p in nodes.values()]
    zs = [p[2] for p in nodes.values()]
    x_span = max(xs) - min(xs) + 1
    y_span = max(ys) - min(ys) + 1
    z_span = max(zs) - min(zs) + 1
    volume = x_span * y_span * z_span
    radial_extent = max(math.sqrt(p[0] ** 2 + p[1] ** 2) for p in nodes.values())
    upward_edges = sum(1 for a, b in edges if nodes[b][2] > nodes[a][2])

    tortuosities: List[float] = []
    for leaf in leaves:
        direct = euclidean(nodes[0], nodes[leaf])
        if direct > 1e-9:
            tortuosities.append(root_dist[leaf] / direct)

    horizontal_span = (x_span + y_span) / 2.0
    anisotropy = z_span / max(1.0, horizontal_span)

    return MorphologyFeatures(
        node_count=len(nodes),
        edge_count=len(edges),
        branch_nodes=branch_nodes,
        leaves=len(leaves),
        max_depth=max_depth,
        graph_diameter=graph_diameter(adjacency),
        height=max(zs) - min(0, min(zs)),
        radial_extent=round(radial_extent, 6),
        bounding_volume=volume,
        density=round(len(nodes) / max(1, volume), 8),
        branch_ratio=round(branch_nodes / max(1, len(nodes)), 8),
        upward_fraction=round(upward_edges / max(1, len(edges)), 8),
        anisotropy=round(anisotropy, 8),
        mean_tortuosity=round(statistics.fmean(tortuosities) if tortuosities else 0.0, 8),
        degree_entropy=round(entropy(degrees), 8),
        effective_conductance=round(effective_conductance(nodes, edges), 10),
        hold_events=int(operator_counts.get("HOLD", 0)),
        maintain_events=int(operator_counts.get("MAINTAIN", 0)),
    )


def tri(value: float, low: float, high: float) -> int:
    if value < low:
        return -1
    if value > high:
        return 1
    return 0


def ternary_readout(features: MorphologyFeatures) -> List[int]:
    """Fixed, lossy, deterministic feature quantization."""
    return [
        tri(features.node_count, 70, 140),
        tri(features.branch_ratio, 0.045, 0.095),
        tri(features.max_depth, 18, 36),
        tri(features.height, 9, 18),
        tri(features.radial_extent, 5.5, 10.5),
        tri(features.density, 0.025, 0.080),
        tri(features.upward_fraction, 0.42, 0.62),
        tri(features.anisotropy, 0.80, 1.80),
        tri(features.mean_tortuosity, 1.25, 1.75),
        tri(features.degree_entropy, 0.70, 1.20),
        tri(features.effective_conductance, 0.025, 0.090),
        tri(features.maintain_events, 0.5, 4.5),
    ]


def basin_signature(readout: Sequence[int], features: MorphologyFeatures) -> str:
    payload = {
        "schema": "cntm-basin-readout-v0.1",
        "ternary": list(readout),
        "conductance": features.effective_conductance,
        "node_count": features.node_count,
    }
    return "CB-" + sha256_json(payload)[:16].upper()


def artifact_summary(artifact: RunArtifact) -> Dict[str, object]:
    return {
        "profile": artifact.profile,
        "seed": artifact.seed,
        "persistent": artifact.persistent,
        "morphology_hash": artifact.morphology_hash,
        "replay_hash": artifact.replay_hash,
        "replay_pass": artifact.replay_pass,
        "basin_signature": artifact.basin_signature,
        "ternary_readout": artifact.ternary_readout,
        "features": asdict(artifact.features),
        "operator_counts": artifact.operator_counts,
        "receipt_count": artifact.receipt_count,
    }


def standardize_vectors(
    samples: Sequence[Tuple[str, List[float]]],
) -> Tuple[List[float], List[float]]:
    width = len(samples[0][1])
    means = [statistics.fmean(vector[i] for _, vector in samples) for i in range(width)]
    scales: List[float] = []
    for i in range(width):
        values = [vector[i] for _, vector in samples]
        scale = statistics.pstdev(values)
        scales.append(scale if scale > 1e-12 else 1.0)
    return means, scales


def normalize(vector: Sequence[float], means: Sequence[float], scales: Sequence[float]) -> List[float]:
    return [(vector[i] - means[i]) / scales[i] for i in range(len(vector))]


def train_centroids(
    samples: Sequence[Tuple[str, List[float]]],
) -> Tuple[Dict[str, List[float]], List[float], List[float]]:
    means, scales = standardize_vectors(samples)
    by_label: Dict[str, List[List[float]]] = {}
    for label, vector in samples:
        by_label.setdefault(label, []).append(normalize(vector, means, scales))
    centroids = {
        label: [statistics.fmean(row[i] for row in rows) for i in range(len(rows[0]))]
        for label, rows in sorted(by_label.items())
    }
    return centroids, means, scales


def predict_label(
    vector: Sequence[float],
    centroids: Dict[str, List[float]],
    means: Sequence[float],
    scales: Sequence[float],
) -> str:
    z = normalize(vector, means, scales)
    return min(
        centroids,
        key=lambda label: (
            sum((z[i] - centroids[label][i]) ** 2 for i in range(len(z))),
            label,
        ),
    )


def confusion_accuracy(pairs: Sequence[Tuple[str, str]]) -> Tuple[float, Dict[str, Dict[str, int]]]:
    labels = sorted({actual for actual, _ in pairs} | {predicted for _, predicted in pairs})
    matrix = {actual: {predicted: 0 for predicted in labels} for actual in labels}
    for actual, predicted in pairs:
        matrix[actual][predicted] += 1
    accuracy = sum(1 for actual, predicted in pairs if actual == predicted) / max(1, len(pairs))
    return accuracy, matrix


def run_inverse_test(
    train_seeds: Sequence[int],
    test_seeds: Sequence[int],
    config: GrowthConfig,
    collapsed_control: bool = False,
) -> Dict[str, object]:
    train: List[Tuple[str, List[float]]] = []
    test: List[Tuple[str, List[float]]] = []
    replay_failures = 0
    signatures: Dict[str, List[str]] = {name: [] for name in sorted(PROFILES)}

    for label in sorted(PROFILES):
        profile = PROFILES["balanced"] if collapsed_control else PROFILES[label]
        for seed in train_seeds:
            artifact = LocalGrowth3D(profile, seed, config).run()
            replay_failures += int(not artifact.replay_pass)
            train.append((label, artifact.features.classifier_vector()))
            signatures[label].append(artifact.basin_signature)
        for seed in test_seeds:
            artifact = LocalGrowth3D(profile, seed, config).run()
            replay_failures += int(not artifact.replay_pass)
            test.append((label, artifact.features.classifier_vector()))
            signatures[label].append(artifact.basin_signature)

    centroids, means, scales = train_centroids(train)
    predictions = [
        (label, predict_label(vector, centroids, means, scales))
        for label, vector in test
    ]
    accuracy, matrix = confusion_accuracy(predictions)
    majority_baseline = max(Counter(label for label, _ in test).values()) / max(1, len(test))
    collision_count = sum(
        count - 1
        for count in Counter(sig for values in signatures.values() for sig in values).values()
        if count > 1
    )
    return {
        "control": "collapsed identical profiles" if collapsed_control else "distinct profiles",
        "train_per_profile": len(train_seeds),
        "held_out_per_profile": len(test_seeds),
        "accuracy": round(accuracy, 6),
        "majority_baseline": round(majority_baseline, 6),
        "above_baseline": accuracy > majority_baseline,
        "confusion_matrix": matrix,
        "replay_failures": replay_failures,
        "signature_collisions": collision_count,
    }


def run_determinism_test(seeds: Sequence[int], config: GrowthConfig) -> Dict[str, object]:
    cases: List[Dict[str, object]] = []
    all_pass = True
    for name in sorted(PROFILES):
        for seed in seeds:
            a = LocalGrowth3D(PROFILES[name], seed, config).run()
            b = LocalGrowth3D(PROFILES[name], seed, config).run()
            passed = (
                a.morphology_hash == b.morphology_hash
                and a.basin_signature == b.basin_signature
                and a.replay_pass
                and b.replay_pass
            )
            all_pass = all_pass and passed
            cases.append({
                "profile": name,
                "seed": seed,
                "pass": passed,
                "hash": a.morphology_hash,
                "signature": a.basin_signature,
            })
    return {"pass": all_pass, "cases": cases}


def run_persistence_ablation(seed: int, profile_name: str) -> Dict[str, object]:
    persistent_cfg = GrowthConfig(persistent=True)
    plain_cfg = GrowthConfig(persistent=False)
    persistent = LocalGrowth3D(PROFILES[profile_name], seed, persistent_cfg).run()
    plain = LocalGrowth3D(PROFILES[profile_name], seed, plain_cfg).run()
    changed = persistent.morphology_hash != plain.morphology_hash
    maintenance_triggered = persistent.features.maintain_events > 0
    return {
        "profile": profile_name,
        "seed": seed,
        "persistent": {
            "nodes": persistent.features.node_count,
            "height": persistent.features.height,
            "hold_events": persistent.features.hold_events,
            "maintain_events": persistent.features.maintain_events,
            "signature": persistent.basin_signature,
            "hash": persistent.morphology_hash,
        },
        "nonpersistent": {
            "nodes": plain.features.node_count,
            "height": plain.features.height,
            "hold_events": plain.features.hold_events,
            "maintain_events": plain.features.maintain_events,
            "signature": plain.basin_signature,
            "hash": plain.morphology_hash,
        },
        "maintenance_triggered": maintenance_triggered,
        "morphology_changed": changed,
        "pass": maintenance_triggered and changed,
    }


def compact_receipts(receipts: Sequence[Receipt], limit: int = 28) -> None:
    important = {"setup", "operator", "tip_state", "maintenance", "morphology_frozen", "audit"}
    selected = [r for r in receipts if r.event_type in important]
    if len(selected) > limit:
        head = selected[: limit // 2]
        tail = selected[-(limit - len(head)) :]
        selected = head + tail
    print("\nCONSEQUENTIAL RECEIPTS")
    print("-" * 112)
    print(f"{'ID':>4} {'CYCLE':>5} {'ACTOR':<23} {'DECISION':<31} REASON")
    print("-" * 112)
    for receipt in selected:
        decision = receipt.decision[:31]
        reason = receipt.reason if len(receipt.reason) <= 43 else receipt.reason[:40] + "..."
        print(f"{receipt.receipt_id:>4} {receipt.cycle:>5} {receipt.actor:<23} {decision:<31} {reason}")
    if len(selected) < len([r for r in receipts if r.event_type in important]):
        print("... middle consequential receipts omitted from display; they remain in exported JSON.")


def projection_xy(nodes: Dict[int, Point3], radius: int = 12) -> str:
    """Top projection: highest z at each x,y, encoded as compact symbols."""
    highest: Dict[Tuple[int, int], int] = {}
    for x, y, z in nodes.values():
        if -radius <= x <= radius and -radius <= y <= radius:
            highest[(x, y)] = max(z, highest.get((x, y), -999))
    if not highest:
        return "(empty)"
    xs = [x for x, _ in highest]
    ys = [y for _, y in highest]
    min_x, max_x = max(-radius, min(xs)), min(radius, max(xs))
    min_y, max_y = max(-radius, min(ys)), min(radius, max(ys))
    symbols = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    lines: List[str] = []
    for y in range(max_y, min_y - 1, -1):
        row = []
        for x in range(min_x, max_x + 1):
            if (x, y) == (0, 0):
                row.append("B")
            elif (x, y) not in highest:
                row.append(" ")
            else:
                z = max(0, highest[(x, y)])
                row.append(symbols[min(len(symbols) - 1, z)])
        lines.append("".join(row).rstrip())
    return "\n".join(lines)


def projection_xz(nodes: Dict[int, Point3], radius: int = 14) -> str:
    occupied = {(x, z) for x, _, z in nodes.values() if -radius <= x <= radius and -2 <= z <= 2 * radius}
    if not occupied:
        return "(empty)"
    xs = [x for x, _ in occupied]
    zs = [z for _, z in occupied]
    min_x, max_x = max(-radius, min(xs)), min(radius, max(xs))
    min_z, max_z = max(-2, min(zs)), min(2 * radius, max(zs))
    lines: List[str] = []
    for z in range(max_z, min_z - 1, -1):
        row = []
        for x in range(min_x, max_x + 1):
            if (x, z) == (0, 0):
                row.append("B")
            elif (x, z) in occupied:
                row.append("#")
            else:
                row.append(" ")
        lines.append("".join(row).rstrip())
    return "\n".join(lines)


def export_obj(nodes: Dict[int, Point3], edges: Sequence[Edge3], path: Path) -> None:
    lines = ["# CNTM 3D morphology graph v0.1"]
    id_to_vertex: Dict[int, int] = {}
    for vertex_index, node_id in enumerate(sorted(nodes), start=1):
        x, y, z = nodes[node_id]
        lines.append(f"v {x} {y} {z}")
        id_to_vertex[node_id] = vertex_index
    for a, b in edges:
        lines.append(f"l {id_to_vertex[a]} {id_to_vertex[b]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_artifacts(artifact: RunArtifact, suite: Dict[str, object], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    run_payload = artifact_summary(artifact)
    run_payload["receipts"] = [asdict(r) for r in artifact.receipts]
    run_payload["morphology"] = morphology_snapshot(artifact.nodes, artifact.edges)
    (out_dir / "sample_run.json").write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
    (out_dir / "validation_suite.json").write_text(json.dumps(suite, indent=2), encoding="utf-8")
    export_obj(artifact.nodes, artifact.edges, out_dir / "sample_morphology.obj")
    manifest = {
        "project": PROJECT,
        "version": VERSION,
        "sample_run_sha256": hashlib.sha256((out_dir / "sample_run.json").read_bytes()).hexdigest(),
        "validation_suite_sha256": hashlib.sha256((out_dir / "validation_suite.json").read_bytes()).hexdigest(),
        "sample_obj_sha256": hashlib.sha256((out_dir / "sample_morphology.obj").read_bytes()).hexdigest(),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{PROJECT} v{VERSION}")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="balanced")
    parser.add_argument("--seed", type=int, default=7317)
    parser.add_argument("--no-persistence", action="store_true")
    parser.add_argument("--single", action="store_true", help="Run only the sample, not the validation suite.")
    parser.add_argument("--deep-suite", action="store_true", help="Use more training and held-out seeds.")
    parser.add_argument("--all-receipts", action="store_true")
    parser.add_argument("--export-dir", default="")
    args = parser.parse_args()

    config = GrowthConfig(persistent=not args.no_persistence)
    sample = LocalGrowth3D(PROFILES[args.profile], args.seed, config).run()

    print(f"{PROJECT} v{VERSION}")
    print("=" * 88)
    print(json.dumps(artifact_summary(sample), indent=2))
    print("\nTOP PROJECTION (symbol = highest z at x,y; B = base)")
    print(projection_xy(sample.nodes))
    print("\nSIDE PROJECTION (x-z occupancy)")
    print(projection_xz(sample.nodes))

    if args.all_receipts:
        compact_receipts(sample.receipts, limit=10_000)
    else:
        compact_receipts(sample.receipts)

    suite: Dict[str, object] = {"not_run": True}
    if not args.single:
        if args.deep_suite:
            train_seeds = list(range(100, 112))
            test_seeds = list(range(900, 906))
            determinism_seeds = [7317, 19, 41]
        else:
            train_seeds = list(range(100, 106))
            test_seeds = list(range(900, 903))
            determinism_seeds = [7317, 19]

        distinct = run_inverse_test(train_seeds, test_seeds, config, collapsed_control=False)
        collapsed = run_inverse_test(train_seeds, test_seeds, config, collapsed_control=True)
        determinism = run_determinism_test(determinism_seeds, config)
        persistence = run_persistence_ablation(args.seed, args.profile)
        suite = {
            "determinism": determinism,
            "inverse_rule_family_recovery": distinct,
            "collapsed_profile_negative_control": collapsed,
            "persistence_ablation": persistence,
            "declared_pass_gate": {
                "determinism_required": True,
                "replay_failures_allowed": 0,
                "inverse_accuracy_must_exceed_majority_baseline": True,
                "collapsed_control_should_not_exceed_0.50": True,
                "maintenance_must_trigger_and_change_morphology": True,
            },
        }
        overall = (
            bool(determinism["pass"])
            and distinct["replay_failures"] == 0
            and bool(distinct["above_baseline"])
            and float(collapsed["accuracy"]) <= 0.50
            and bool(persistence["pass"])
        )
        suite["overall_pass"] = overall
        print("\nVALIDATION SUITE")
        print("=" * 88)
        print(json.dumps(suite, indent=2))

    print("\nCLAIM BOUNDARY")
    print("- Software-only CNT-like graph morphology; no CNT chemistry or wet-lab validation.")
    print("- kappa, phi, and T are boundary-condition parameters, not physical resonance proof.")
    print("- Basin signatures are deterministic lossy readouts, not intrinsic symbols.")
    print("- The inverse test measures rule-family recoverability, not universal memory.")

    if args.export_dir:
        out_dir = Path(args.export_dir)
        write_artifacts(sample, suite, out_dir)
        print(f"\nArtifacts written to: {out_dir}")
    else:
        print("\nPrint-only mode. Use --export-dir NAME to write JSON, OBJ, and a hash manifest.")


if __name__ == "__main__":
    main()

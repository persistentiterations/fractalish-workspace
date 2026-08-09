#!/usr/bin/env python3
"""CNTM 3D Morphology-Memory Persistence Harness v0.5.

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
VERSION = "0.5"


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
        "schema": "cntm-basin-readout-v0.2",
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



FEATURE_GROUPS: Dict[str, Tuple[int, ...]] = {
    "all": tuple(range(11)),
    "size": (0, 2, 3, 4, 5),
    "branching": (1, 9),
    "directional": (6, 7, 8),
    "conductance": (10,),
    "shape_without_size": (1, 6, 7, 8, 9, 10),
}


def select_features(vector: Sequence[float], indices: Sequence[int]) -> List[float]:
    return [float(vector[i]) for i in indices]


def classification_metrics(pairs: Sequence[Tuple[str, str]]) -> Dict[str, object]:
    accuracy, matrix = confusion_accuracy(pairs)
    labels = sorted(matrix)
    recalls: Dict[str, float] = {}
    precisions: Dict[str, float] = {}
    for label in labels:
        tp = matrix[label][label]
        actual_total = sum(matrix[label].values())
        predicted_total = sum(matrix[a][label] for a in labels)
        recalls[label] = tp / actual_total if actual_total else 0.0
        precisions[label] = tp / predicted_total if predicted_total else 0.0
    return {
        "accuracy": round(accuracy, 6),
        "balanced_accuracy": round(statistics.fmean(recalls.values()), 6),
        "precision": {k: round(v, 6) for k, v in precisions.items()},
        "recall": {k: round(v, 6) for k, v in recalls.items()},
        "confusion_matrix": matrix,
    }


def bootstrap_accuracy_ci(
    pairs: Sequence[Tuple[str, str]], seed: int = 20260714, draws: int = 1000
) -> List[float]:
    if not pairs:
        return [0.0, 0.0]
    rng = random.Random(seed)
    values: List[float] = []
    for _ in range(draws):
        sample = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        values.append(sum(a == b for a, b in sample) / len(sample))
    values.sort()
    lo = values[max(0, int(0.025 * draws) - 1)]
    hi = values[min(draws - 1, int(0.975 * draws))]
    return [round(lo, 6), round(hi, 6)]


def collect_dataset(
    train_seeds: Sequence[int], test_seeds: Sequence[int], config: GrowthConfig,
    profiles: Optional[Dict[str, ConstraintProfile]] = None,
) -> Tuple[List[Tuple[str, List[float]]], List[Tuple[str, List[float]]], int]:
    active_profiles = profiles or PROFILES
    train: List[Tuple[str, List[float]]] = []
    test: List[Tuple[str, List[float]]] = []
    replay_failures = 0
    for label in sorted(active_profiles):
        for seed in train_seeds:
            artifact = LocalGrowth3D(active_profiles[label], seed, config).run()
            replay_failures += int(not artifact.replay_pass)
            train.append((label, artifact.features.classifier_vector()))
        for seed in test_seeds:
            artifact = LocalGrowth3D(active_profiles[label], seed, config).run()
            replay_failures += int(not artifact.replay_pass)
            test.append((label, artifact.features.classifier_vector()))
    return train, test, replay_failures


def evaluate_dataset(
    train: Sequence[Tuple[str, List[float]]], test: Sequence[Tuple[str, List[float]]],
    indices: Sequence[int],
) -> Tuple[List[Tuple[str, str]], Dict[str, object]]:
    train_selected = [(label, select_features(vector, indices)) for label, vector in train]
    test_selected = [(label, select_features(vector, indices)) for label, vector in test]
    centroids, means, scales = train_centroids(train_selected)
    pairs = [(label, predict_label(vector, centroids, means, scales)) for label, vector in test_selected]
    metrics = classification_metrics(pairs)
    metrics["bootstrap_95pct_accuracy_ci"] = bootstrap_accuracy_ci(pairs)
    return pairs, metrics


def run_feature_ablation(
    train_seeds: Sequence[int], test_seeds: Sequence[int], config: GrowthConfig
) -> Dict[str, object]:
    train, test, replay_failures = collect_dataset(train_seeds, test_seeds, config)
    results: Dict[str, object] = {}
    for name, indices in FEATURE_GROUPS.items():
        _, metrics = evaluate_dataset(train, test, indices)
        results[name] = metrics
    return {"replay_failures": replay_failures, "feature_groups": results}


def run_label_permutation_control(
    train_seeds: Sequence[int], test_seeds: Sequence[int], config: GrowthConfig,
    permutation_seed: int = 44021, draws: int = 60,
) -> Dict[str, object]:
    train, test, replay_failures = collect_dataset(train_seeds, test_seeds, config)
    original_labels = [label for label, _ in train]
    baseline = max(Counter(label for label, _ in test).values()) / len(test)
    accuracies: List[float] = []
    balanced_accuracies: List[float] = []
    for draw in range(draws):
        rng = random.Random(permutation_seed + draw)
        labels = list(original_labels)
        rng.shuffle(labels)
        permuted_train = [(labels[i], vector) for i, (_, vector) in enumerate(train)]
        _, metrics = evaluate_dataset(permuted_train, test, FEATURE_GROUPS["all"])
        accuracies.append(float(metrics["accuracy"]))
        balanced_accuracies.append(float(metrics["balanced_accuracy"]))
    ordered = sorted(accuracies)
    return {
        "permutation_seed": permutation_seed,
        "draws": draws,
        "mean_accuracy": round(statistics.fmean(accuracies), 6),
        "mean_balanced_accuracy": round(statistics.fmean(balanced_accuracies), 6),
        "minimum_accuracy": round(min(accuracies), 6),
        "maximum_accuracy": round(max(accuracies), 6),
        "median_accuracy": round(statistics.median(accuracies), 6),
        "majority_baseline": round(baseline, 6),
        "mean_at_or_near_chance": statistics.fmean(accuracies) <= baseline + 0.10,
        "fraction_above_0_50": round(sum(x > 0.50 for x in accuracies) / draws, 6),
        "replay_failures": replay_failures,
    }

def interpolated_profiles() -> Dict[str, ConstraintProfile]:
    ordered = [PROFILES["cautious"], PROFILES["balanced"], PROFILES["aggressive"]]
    out: Dict[str, ConstraintProfile] = {}
    steps = 7
    for i in range(steps):
        t = i / (steps - 1)
        if t <= 0.5:
            a, b, u = ordered[0], ordered[1], t * 2.0
        else:
            a, b, u = ordered[1], ordered[2], (t - 0.5) * 2.0
        name = f"p{i}"
        out[name] = ConstraintProfile(
            name,
            a.kappa + (b.kappa - a.kappa) * u,
            a.phi + (b.phi - a.phi) * u,
            a.target_stability + (b.target_stability - a.target_stability) * u,
            f"Linear interpolation position {i}/{steps-1}.",
        )
    return out


def run_parameter_interpolation(seeds: Sequence[int], config: GrowthConfig) -> Dict[str, object]:
    profiles = interpolated_profiles()
    rows: List[Dict[str, object]] = []
    for name, profile in sorted(profiles.items()):
        artifacts = [LocalGrowth3D(profile, seed, config).run() for seed in seeds]
        rows.append({
            "position": name,
            "kappa": round(profile.kappa, 5),
            "phi": round(profile.phi, 5),
            "T": round(profile.target_stability, 5),
            "mean_nodes": round(statistics.fmean(a.features.node_count for a in artifacts), 4),
            "mean_branch_ratio": round(statistics.fmean(a.features.branch_ratio for a in artifacts), 6),
            "mean_height": round(statistics.fmean(a.features.height for a in artifacts), 4),
            "mean_conductance": round(statistics.fmean(a.features.effective_conductance for a in artifacts), 8),
            "replay_pass": all(a.replay_pass for a in artifacts),
        })
    adjacent_changes = []
    for left, right in zip(rows, rows[1:]):
        adjacent_changes.append({
            "from": left["position"], "to": right["position"],
            "node_delta": round(float(right["mean_nodes"]) - float(left["mean_nodes"]), 4),
            "branch_ratio_delta": round(float(right["mean_branch_ratio"]) - float(left["mean_branch_ratio"]), 6),
            "conductance_delta": round(float(right["mean_conductance"]) - float(left["mean_conductance"]), 8),
        })
    return {"seed_count": len(seeds), "profiles": rows, "adjacent_changes": adjacent_changes}


def hamming(a: Sequence[int], b: Sequence[int]) -> int:
    return sum(x != y for x, y in zip(a, b))


def run_signature_audit(seeds: Sequence[int], config: GrowthConfig) -> Dict[str, object]:
    artifacts: List[RunArtifact] = []
    for name in sorted(PROFILES):
        artifacts.extend(LocalGrowth3D(PROFILES[name], seed, config).run() for seed in seeds)
    sig_counts = Counter(a.basin_signature for a in artifacts)
    same_profile: List[int] = []
    cross_profile: List[int] = []
    for i, a in enumerate(artifacts):
        for b in artifacts[i+1:]:
            distance = hamming(a.ternary_readout, b.ternary_readout)
            (same_profile if a.profile == b.profile else cross_profile).append(distance)
    return {
        "runs": len(artifacts),
        "unique_signatures": len(sig_counts),
        "collision_excess": sum(v - 1 for v in sig_counts.values() if v > 1),
        "same_profile_mean_hamming": round(statistics.fmean(same_profile), 6) if same_profile else 0.0,
        "cross_profile_mean_hamming": round(statistics.fmean(cross_profile), 6) if cross_profile else 0.0,
        "cross_profile_more_separated": statistics.fmean(cross_profile) > statistics.fmean(same_profile),
        "replay_failures": sum(not a.replay_pass for a in artifacts),
    }


def run_equal_energy_persistence_ablation(seed: int, profile_name: str) -> Dict[str, object]:
    reserve = 30.0
    persistent_cfg = GrowthConfig(persistent=True, initial_energy=25.0, maintenance_budget=reserve)
    plain_cfg = GrowthConfig(persistent=False, initial_energy=25.0 + reserve, maintenance_budget=0.0)
    persistent = LocalGrowth3D(PROFILES[profile_name], seed, persistent_cfg).run()
    plain = LocalGrowth3D(PROFILES[profile_name], seed, plain_cfg).run()
    return {
        "profile": profile_name,
        "seed": seed,
        "declared_total_energy_each": 55.0,
        "persistent": artifact_summary(persistent),
        "nonpersistent_front_loaded": artifact_summary(plain),
        "maintenance_triggered": persistent.features.maintain_events > 0,
        "morphology_changed": persistent.morphology_hash != plain.morphology_hash,
        "node_difference": persistent.features.node_count - plain.features.node_count,
        "replay_pass": persistent.replay_pass and plain.replay_pass,
        "interpretation": "Equal declared energy, but timing differs: bounded local maintenance versus front-loaded energy.",
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
    lines = ["# CNTM 3D morphology graph v0.2"]
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



# ============================================================
# v0.3 — CAUSAL PERSISTENCE AND PARAMETER ISOLATION
# ============================================================

NEUTRAL_PROFILE = ConstraintProfile(
    "neutral", 0.65, 0.80, 0.78,
    "Common washout condition used after the imprint phase.",
)

class ScheduledGrowth3D(LocalGrowth3D):
    """Growth with an early imprint profile followed by common neutral conditions."""

    def __init__(self, imprint_profile: ConstraintProfile, seed: int, config: GrowthConfig,
                 imprint_cycles: int = 5) -> None:
        self.imprint_profile = imprint_profile
        self.imprint_cycles = max(0, int(imprint_cycles))
        super().__init__(imprint_profile, seed, config)

    def _activate_profile(self, profile: ConstraintProfile) -> None:
        self.profile = profile
        horizontal = (math.cos(profile.phi), math.sin(profile.phi))
        self.field_direction = unit3((
            profile.kappa * horizontal[0],
            profile.kappa * horizontal[1],
            0.65 + 0.35 * profile.target_stability,
        ))

    def run(self) -> RunArtifact:
        switched = False
        for cycle in range(1, self.config.max_cycles + 1):
            self.cycle = cycle
            if cycle == self.imprint_cycles + 1 and not switched:
                before = self.profile.name
                self._activate_profile(NEUTRAL_PROFILE)
                switched = True
                self._receipt(
                    "phase_controller", "enter neutral washout",
                    "the bounded imprint phase ended and all runs now share one common profile",
                    {"from_profile": before, "to_profile": "neutral", "cycle": cycle,
                     "retained_nodes": len(self.nodes), "retained_tips": len(self.tips)},
                    "existing local morphology is retained while external conditions become common",
                    "phase_transition", "washout",
                )
            if not self.tips or len(self.nodes) >= self.config.max_nodes:
                break
            next_tips: List[Tip] = []
            for tip in sorted(self.tips, key=lambda t: t.tip_id):
                if len(self.nodes) >= self.config.max_nodes:
                    break
                next_tips.extend(self._process_tip(tip))
            self.tips = [t for t in next_tips if t.state == "active"]
        # Restore the declared artifact label while preserving final graph.
        final_profile = self.profile
        self.profile = self.imprint_profile
        artifact = self._finalize_scheduled(final_profile.name)
        return artifact

    def _finalize_scheduled(self, final_condition: str) -> RunArtifact:
        self._receipt(
            "run_controller", "freeze morphology",
            "the finite cycle, node, active-tip, or energy boundary ended scheduled growth",
            {"cycles_completed": self.cycle, "nodes": len(self.nodes), "edges": len(self.edges),
             "active_tips": len(self.tips), "maintenance_remaining": round(self.maintenance_remaining, 5),
             "imprint_profile": self.imprint_profile.name, "final_condition": final_condition},
            "graph becomes immutable input to measurement and replay",
            "morphology_frozen", "morphology",
        )
        features = extract_features(self.nodes, self.edges, self.operator_counts)
        snapshot = morphology_snapshot(self.nodes, self.edges)
        morphology_hash = sha256_json(snapshot)
        replay_nodes, replay_edges, replay_errors = replay_morphology(self.receipts)
        replay_hash = sha256_json(morphology_snapshot(replay_nodes, replay_edges))
        replay_pass = not replay_errors and replay_hash == morphology_hash
        readout = ternary_readout(features)
        signature = basin_signature(readout, features)
        self._receipt(
            "replay_auditor", "approve replay" if replay_pass else "reject replay",
            "receipt reconstruction matches the frozen morphology hash" if replay_pass
            else "receipt reconstruction differs from the frozen morphology",
            {"morphology_hash": morphology_hash, "replay_hash": replay_hash,
             "errors": replay_errors, "basin_signature": signature},
            "run is replay-valid" if replay_pass else "run is quarantined", "audit", "replay",
        )
        return RunArtifact(
            profile=self.imprint_profile.name, seed=self.seed, persistent=self.config.persistent,
            morphology_hash=morphology_hash, replay_hash=replay_hash, replay_pass=replay_pass,
            basin_signature=signature, ternary_readout=readout, features=features,
            operator_counts=dict(sorted(self.operator_counts.items())), receipt_count=len(self.receipts),
            nodes=dict(self.nodes), edges=list(self.edges), receipts=list(self.receipts),
        )


class StagedEnergyGrowth(LocalGrowth3D):
    """Nonpersistent timing control: staged energy without HOLD or MAINTAIN semantics."""

    def _hold_or_terminate(self, tip: Tip, env: Dict[str, float]) -> None:
        stable = env["alignment"] >= 0.48 and env["flux"] >= 0.30 and env["crowding"] <= 0.72
        if stable and self.maintenance_remaining >= self.config.maintenance_injection:
            injection = min(self.config.maintenance_injection, self.maintenance_remaining)
            self.maintenance_remaining -= injection
            tip.energy += injection
            self.operator_counts["STAGE_ENERGY"] += 1
            self._receipt(
                "energy_scheduler", f"stage energy to tip {tip.tip_id}",
                "the nonpersistent timing control releases bounded energy at a local low-energy event",
                {"tip": tip.tip_id, "injection": round(injection, 5),
                 "energy_after": round(tip.energy, 5),
                 "reserve_remaining": round(self.maintenance_remaining, 5)},
                "tip continues without HOLD or MAINTAIN state semantics", "energy_stage", str(tip.tip_id),
            )
        else:
            self._terminate(tip, "energy is below threshold and staged reserve is unavailable",
                            {"energy": round(tip.energy, 5), "stable": stable,
                             "reserve_remaining": round(self.maintenance_remaining, 5)})


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _paired_summary(rows: Sequence[Dict[str, float]], keys: Sequence[str]) -> Dict[str, object]:
    out: Dict[str, object] = {"pairs": len(rows)}
    for key in keys:
        vals = [float(r[key]) for r in rows]
        out[key] = {
            "mean_difference": round(_mean(vals), 8),
            "positive_fraction": round(sum(v > 0 for v in vals) / len(vals), 6) if vals else 0.0,
            "negative_fraction": round(sum(v < 0 for v in vals) / len(vals), 6) if vals else 0.0,
            "zero_fraction": round(sum(v == 0 for v in vals) / len(vals), 6) if vals else 0.0,
            "minimum": round(min(vals), 8) if vals else 0.0,
            "maximum": round(max(vals), 8) if vals else 0.0,
        }
    return out


def run_repeated_energy_controls(seeds: Sequence[int]) -> Dict[str, object]:
    all_rows: List[Dict[str, float]] = []
    replay_failures = 0
    by_profile: Dict[str, object] = {}
    for name in sorted(PROFILES):
        rows: List[Dict[str, float]] = []
        for seed in seeds:
            persistent = LocalGrowth3D(PROFILES[name], seed, GrowthConfig(
                persistent=True, initial_energy=25.0, maintenance_budget=30.0)).run()
            front = LocalGrowth3D(PROFILES[name], seed, GrowthConfig(
                persistent=False, initial_energy=55.0, maintenance_budget=0.0)).run()
            staged = StagedEnergyGrowth(PROFILES[name], seed, GrowthConfig(
                persistent=False, initial_energy=25.0, maintenance_budget=30.0)).run()
            replay_failures += sum(not a.replay_pass for a in (persistent, front, staged))
            row = {
                "persistent_minus_front_nodes": persistent.features.node_count - front.features.node_count,
                "persistent_minus_front_branch_ratio": persistent.features.branch_ratio - front.features.branch_ratio,
                "persistent_minus_front_conductance": persistent.features.effective_conductance - front.features.effective_conductance,
                "persistent_minus_staged_nodes": persistent.features.node_count - staged.features.node_count,
                "persistent_minus_staged_branch_ratio": persistent.features.branch_ratio - staged.features.branch_ratio,
                "persistent_minus_staged_conductance": persistent.features.effective_conductance - staged.features.effective_conductance,
                "persistent_vs_front_hash_changed": float(persistent.morphology_hash != front.morphology_hash),
                "persistent_vs_staged_hash_changed": float(persistent.morphology_hash != staged.morphology_hash),
            }
            rows.append(row); all_rows.append(row)
        by_profile[name] = _paired_summary(rows, list(rows[0]))
    overall = _paired_summary(all_rows, list(all_rows[0]))
    return {"declared_energy_each": 55.0, "seed_count_per_profile": len(seeds),
            "replay_failures": replay_failures, "by_profile": by_profile, "overall": overall,
            "timing_effect_replicated": overall["persistent_vs_front_hash_changed"]["mean_difference"] >= 0.90,
            "operator_semantics_effect_replicated": overall["persistent_vs_staged_hash_changed"]["mean_difference"] >= 0.50}


def _sweep_profile(param: str, value: float) -> ConstraintProfile:
    base = PROFILES["balanced"]
    return ConstraintProfile(f"{param}_{value:.5f}",
        value if param == "kappa" else base.kappa,
        value if param == "phi" else base.phi,
        value if param == "T" else base.target_stability,
        f"One-parameter {param} sweep at {value:.5f}")


def _spearman_monotonic(values: Sequence[float]) -> float:
    n = len(values)
    if n < 2: return 0.0
    order = sorted(range(n), key=lambda i: (values[i], i))
    ranks = [0.0] * n
    for rank, idx in enumerate(order): ranks[idx] = float(rank)
    mean_i = (n - 1) / 2.0; mean_r = sum(ranks) / n
    num = sum((i-mean_i)*(ranks[i]-mean_r) for i in range(n))
    den1 = math.sqrt(sum((i-mean_i)**2 for i in range(n)))
    den2 = math.sqrt(sum((r-mean_r)**2 for r in ranks))
    return num/(den1*den2) if den1 and den2 else 0.0


def run_one_parameter_sweeps(seeds: Sequence[int]) -> Dict[str, object]:
    grids = {"kappa": [0.25+i*0.0875 for i in range(9)],
             "phi": [0.20+i*0.15 for i in range(9)],
             "T": [0.50+i*0.05625 for i in range(9)]}
    out: Dict[str, object] = {}; replay_failures = 0
    for param, values in grids.items():
        positions=[]
        for value in values:
            arts=[LocalGrowth3D(_sweep_profile(param, value), s, GrowthConfig()).run() for s in seeds]
            replay_failures += sum(not a.replay_pass for a in arts)
            positions.append({"value": round(value, 6),
                "mean_nodes": round(_mean([a.features.node_count for a in arts]), 6),
                "mean_branch_ratio": round(_mean([a.features.branch_ratio for a in arts]), 8),
                "mean_height": round(_mean([a.features.height for a in arts]), 6),
                "mean_upward_fraction": round(_mean([a.features.upward_fraction for a in arts]), 8),
                "mean_conductance": round(_mean([a.features.effective_conductance for a in arts]), 8)})
        metrics={k: _spearman_monotonic([p[k] for p in positions]) for k in positions[0] if k.startswith("mean_")}
        best=max(metrics.items(), key=lambda kv: abs(kv[1]))
        out[param]={"positions":positions, "spearman_by_metric":{k:round(v,6) for k,v in metrics.items()},
                    "strongest_ordered_metric":best[0], "strongest_abs_spearman":round(abs(best[1]),6),
                    "ordered_trend_pass":abs(best[1]) >= 0.70}
    return {"seeds_per_position":len(seeds), "replay_failures":replay_failures, "parameters":out,
            "at_least_one_ordered_trend":any(v["ordered_trend_pass"] for v in out.values())}


def run_pairwise_profile_diagnosis(train_seeds: Sequence[int], test_seeds: Sequence[int]) -> Dict[str, object]:
    train,test,replay=collect_dataset(train_seeds, test_seeds, GrowthConfig())
    pairs={}
    for a,b in (("cautious","balanced"),("balanced","aggressive"),("cautious","aggressive")):
        tr=[x for x in train if x[0] in {a,b}]; te=[x for x in test if x[0] in {a,b}]
        _,metrics=evaluate_dataset(tr,te,list(range(11)))
        pairs[f"{a}_vs_{b}"]=metrics
    return {"replay_failures":replay,"pairwise":pairs,
            "extremes_easier_than_balanced_pairs": pairs["cautious_vs_aggressive"]["accuracy"] >= max(
                pairs["cautious_vs_balanced"]["accuracy"],pairs["balanced_vs_aggressive"]["accuracy"])}


def run_permutation_significance(train_seeds: Sequence[int], test_seeds: Sequence[int], draws: int) -> Dict[str, object]:
    train,test,replay=collect_dataset(train_seeds, test_seeds, GrowthConfig())
    _,true_metrics=evaluate_dataset(train,test,list(range(11)))
    rng=random.Random(903177)
    null=[]
    labels=[row[0] for row in train]
    for _ in range(draws):
        shuffled=list(labels); rng.shuffle(shuffled)
        perm=[(shuffled[i], train[i][1]) for i in range(len(train))]
        centroids, means, scales = train_centroids(perm)
        pairs = [(label, predict_label(vector, centroids, means, scales)) for label, vector in test]
        null.append(float(confusion_accuracy(pairs)[0]))
    ordered=sorted(null)
    def q(frac:float)->float:
        return ordered[min(len(ordered)-1, int(frac*(len(ordered)-1)))]
    true=float(true_metrics["accuracy"])
    p=(sum(x>=true for x in null)+1)/(len(null)+1)
    return {"draws":draws,"true_accuracy":round(true,6),"null_mean":round(_mean(null),6),
            "null_95th_percentile":round(q(.95),6),"null_99th_percentile":round(q(.99),6),
            "empirical_p_value":round(p,8),"true_exceeds_95th_percentile":true>q(.95),
            "replay_failures":replay}


def _collect_washout_dataset(seeds: Sequence[int], imprint_cycles: int, reset: bool=False,
                             neutral_only: bool=False) -> Tuple[List[Tuple[str,List[float]]],int]:
    rows=[]; failures=0
    for label in sorted(PROFILES):
        for seed in seeds:
            if reset or neutral_only:
                art=LocalGrowth3D(NEUTRAL_PROFILE,seed,GrowthConfig()).run()
            else:
                art=ScheduledGrowth3D(PROFILES[label],seed,GrowthConfig(),imprint_cycles).run()
            failures += int(not art.replay_pass)
            rows.append((label, art.features.classifier_vector()))
    return rows,failures


def run_imprint_washout(train_seeds: Sequence[int], test_seeds: Sequence[int], imprint_cycles:int=5) -> Dict[str,object]:
    train,rf1=_collect_washout_dataset(train_seeds,imprint_cycles)
    test,rf2=_collect_washout_dataset(test_seeds,imprint_cycles)
    _,retained=evaluate_dataset(train,test,list(range(11)))
    _,retained_shape=evaluate_dataset(train,test,[1,5,6,7,8,9,10])
    reset_train,rf3=_collect_washout_dataset(train_seeds,imprint_cycles,reset=True)
    reset_test,rf4=_collect_washout_dataset(test_seeds,imprint_cycles,reset=True)
    _,reset_metrics=evaluate_dataset(reset_train,reset_test,list(range(11)))
    return {"imprint_cycles":imprint_cycles,"neutral_condition":"balanced common profile",
            "retained_morphology_recovery":retained,"retained_shape_without_size":retained_shape,
            "reset_control":reset_metrics,"replay_failures":rf1+rf2+rf3+rf4,
            "retention_above_chance":float(retained["accuracy"])>1/3,
            "reset_at_or_near_chance":float(reset_metrics["accuracy"])<=0.50}


def run_signature_position_audit(seeds: Sequence[int]) -> Dict[str,object]:
    rows=[]
    for name in sorted(PROFILES):
        for seed in seeds:
            a=LocalGrowth3D(PROFILES[name],seed,GrowthConfig()).run()
            rows.append((name,a.ternary_readout))
    positions=[]
    for i in range(12):
        by={name:[r[i] for n,r in rows if n==name] for name in sorted(PROFILES)}
        within=sum(len(set(vals)) for vals in by.values())/3.0
        modes={name:max((-1,0,1),key=lambda x:(by[name].count(x),-abs(x))) for name in by}
        divergence=len(set(modes.values()))
        allvals=[r[i] for _,r in rows]
        probs=[allvals.count(x)/len(allvals) for x in (-1,0,1) if allvals.count(x)]
        ent=-sum(p*math.log(p,2) for p in probs)
        positions.append({"position":i,"within_profile_distinct_mean":round(within,6),
                          "profile_mode_divergence":divergence,"entropy":round(ent,6),
                          "modes":modes})
    useful=[p["position"] for p in positions if p["profile_mode_divergence"]>=2]
    return {"runs":len(rows),"positions":positions,"candidate_informative_positions":useful,
            "candidate_count":len(useful),"signature_version_recommendation":"retain CB1; create CB2 only after fixed-position validation"}



# ============================================================
# v0.4 — GEOMETRY-STATE SEPARATION AND MEMORY-CARRIER AUDIT
# ============================================================

import copy

class TransferGrowth3D(ScheduledGrowth3D):
    """Two-stage growth with explicit state transfer at the imprint boundary."""

    def grow_imprint(self) -> None:
        for cycle in range(1, self.imprint_cycles + 1):
            self.cycle = cycle
            if not self.tips or len(self.nodes) >= self.config.max_nodes:
                break
            next_tips: List[Tip] = []
            for tip in sorted(self.tips, key=lambda t: t.tip_id):
                if len(self.nodes) >= self.config.max_nodes:
                    break
                next_tips.extend(self._process_tip(tip))
            self.tips = [t for t in next_tips if t.state == "active"]

    def continue_neutral(self, condition: str) -> RunArtifact:
        self._activate_profile(NEUTRAL_PROFILE)
        self._receipt(
            "transfer_controller", f"apply transfer condition {condition}",
            "the imprint phase ended and the declared geometry/state transfer was applied before common neutral growth",
            {"condition": condition, "retained_nodes": len(self.nodes), "active_tips": len(self.tips),
             "maintenance_remaining": round(self.maintenance_remaining,5)},
            "all continuations now share the same neutral external profile", "state_transfer", condition,
        )
        start = self.cycle + 1
        for cycle in range(start, self.config.max_cycles + 1):
            self.cycle = cycle
            if not self.tips or len(self.nodes) >= self.config.max_nodes:
                break
            next_tips: List[Tip] = []
            for tip in sorted(self.tips, key=lambda t: t.tip_id):
                if len(self.nodes) >= self.config.max_nodes:
                    break
                next_tips.extend(self._process_tip(tip))
            self.tips = [t for t in next_tips if t.state == "active"]
        self.profile = self.imprint_profile
        return self._finalize_scheduled("neutral_after_" + condition)


def _leaf_ids(g: LocalGrowth3D) -> List[int]:
    return sorted(n for n in g.nodes if n != 0 and len(g.adjacency.get(n,set())) == 1)


def _apply_transfer(base: TransferGrowth3D, condition: str, seed: int) -> TransferGrowth3D:
    g: TransferGrowth3D = copy.deepcopy(base)
    rng = random.Random((seed << 16) ^ 0x4A17E)
    if condition == "full_state":
        return g
    if condition == "geometry_frozen":
        g.tips = []
        return g
    if condition == "geometry_only_reconstructed_tips":
        leaves = _leaf_ids(g)
        g.tips = [Tip(i, node, (0,0,1), g.config.initial_energy) for i,node in enumerate(leaves)]
        g.next_tip_id = len(g.tips)
        g.maintenance_remaining = g.config.maintenance_budget
        return g
    if condition == "reset_tip_energy":
        for t in g.tips: t.energy = g.config.initial_energy
        g.maintenance_remaining = g.config.maintenance_budget
        return g
    if condition == "reset_tip_direction":
        for t in g.tips: t.direction = (0,0,1)
        return g
    if condition == "erase_lineage":
        for i,t in enumerate(sorted(g.tips,key=lambda x:x.node_id)):
            t.tip_id=i; t.age=0; t.hold_count=0
        g.next_tip_id=len(g.tips)
        return g
    if condition == "randomize_tip_assignment":
        if len(g.tips)>1:
            states=[(t.direction,t.energy,t.age,t.hold_count) for t in g.tips]
            rng.shuffle(states)
            for t,s in zip(g.tips,states): t.direction,t.energy,t.age,t.hold_count=s
        return g
    if condition == "zero_live_state":
        for t in g.tips:
            t.direction=(0,0,1); t.energy=g.config.initial_energy; t.age=0; t.hold_count=0
        g.maintenance_remaining=0.0
        return g
    if condition == "reset_all":
        fresh=TransferGrowth3D(NEUTRAL_PROFILE, seed, copy.deepcopy(g.config), g.imprint_cycles)
        fresh.imprint_profile=g.imprint_profile
        fresh.grow_imprint = lambda: None
        return fresh
    raise ValueError(condition)


TRANSFER_CONDITIONS=(
    "geometry_frozen",
    "full_state",
    "geometry_only_reconstructed_tips",
    "reset_tip_energy",
    "reset_tip_direction",
    "erase_lineage",
    "randomize_tip_assignment",
    "zero_live_state",
    "reset_all",
)


def _collect_transfer_dataset(seeds: Sequence[int], condition: str, imprint_cycles: int=5) -> Tuple[List[Tuple[str,List[float]]],int,List[Dict[str,object]]]:
    rows=[]; failures=0; ledger=[]
    for label in sorted(PROFILES):
        for seed in seeds:
            base=TransferGrowth3D(PROFILES[label],seed,GrowthConfig(),imprint_cycles)
            base.grow_imprint()
            imprint_hash=sha256_json(morphology_snapshot(base.nodes,base.edges))
            g=_apply_transfer(base,condition,seed)
            if condition=="geometry_frozen":
                g.profile=g.imprint_profile
                art=g._finalize_scheduled("frozen_at_imprint")
            elif condition=="reset_all":
                art=LocalGrowth3D(NEUTRAL_PROFILE,seed,GrowthConfig()).run()
                art.profile=label
            else:
                art=g.continue_neutral(condition)
            failures += int(not art.replay_pass)
            rows.append((label,art.features.classifier_vector()))
            ledger.append({"profile":label,"seed":seed,"condition":condition,"imprint_hash":imprint_hash,
                           "final_hash":art.morphology_hash,"nodes":art.features.node_count,
                           "replay_pass":art.replay_pass})
    return rows,failures,ledger


def run_geometry_state_separation(train_seeds: Sequence[int], test_seeds: Sequence[int], imprint_cycles:int=5) -> Dict[str,object]:
    conditions={}; total_fail=0; ledgers={}
    for condition in TRANSFER_CONDITIONS:
        train,rf1,train_ledger=_collect_transfer_dataset(train_seeds,condition,imprint_cycles)
        test,rf2,test_ledger=_collect_transfer_dataset(test_seeds,condition,imprint_cycles)
        _,all_metrics=evaluate_dataset(train,test,list(range(11)))
        _,shape_metrics=evaluate_dataset(train,test,[1,5,6,7,8,9,10])
        total_fail += rf1+rf2
        conditions[condition]={"all_features":all_metrics,"shape_without_size":shape_metrics,
            "above_chance":float(all_metrics["accuracy"])>1/3,
            "shape_above_chance":float(shape_metrics["accuracy"])>1/3,
            "replay_failures":rf1+rf2}
        ledgers[condition]=test_ledger
    frozen=float(conditions["geometry_frozen"]["all_features"]["accuracy"])
    full=float(conditions["full_state"]["all_features"]["accuracy"])
    reset=float(conditions["reset_all"]["all_features"]["accuracy"])
    geometry_only=float(conditions["geometry_only_reconstructed_tips"]["all_features"]["accuracy"])
    live_state_gain=round(full-geometry_only,6)
    return {"imprint_cycles":imprint_cycles,"conditions":conditions,
        "summary":{
            "geometry_immediate_recovery":round(frozen,6),
            "full_state_after_neutral_recovery":round(full,6),
            "geometry_only_continuation_recovery":round(geometry_only,6),
            "reset_all_recovery":round(reset,6),
            "estimated_live_state_gain_over_geometry_only":live_state_gain,
            "geometry_is_memory_carrier":frozen>1/3,
            "live_state_adds_material_recovery":live_state_gain>=0.10,
            "reset_returns_to_chance":reset<=0.50,
        },
        "test_ledgers":ledgers,"replay_failures":total_fail}


def run_transfer_hash_pairing(seeds: Sequence[int], imprint_cycles:int=5) -> Dict[str,object]:
    rows=[]; failures=0
    for label in sorted(PROFILES):
        for seed in seeds:
            base=TransferGrowth3D(PROFILES[label],seed,GrowthConfig(),imprint_cycles); base.grow_imprint()
            arts={}
            for condition in ("full_state","reset_tip_energy","reset_tip_direction","erase_lineage","randomize_tip_assignment","zero_live_state"):
                art=_apply_transfer(base,condition,seed).continue_neutral(condition)
                failures+=int(not art.replay_pass); arts[condition]=art
            rows.append({"profile":label,"seed":seed,
                "full_vs_reset_energy_changed":arts["full_state"].morphology_hash!=arts["reset_tip_energy"].morphology_hash,
                "full_vs_reset_direction_changed":arts["full_state"].morphology_hash!=arts["reset_tip_direction"].morphology_hash,
                "full_vs_erase_lineage_changed":arts["full_state"].morphology_hash!=arts["erase_lineage"].morphology_hash,
                "full_vs_random_assignment_changed":arts["full_state"].morphology_hash!=arts["randomize_tip_assignment"].morphology_hash,
                "full_vs_zero_live_state_changed":arts["full_state"].morphology_hash!=arts["zero_live_state"].morphology_hash})
    summary={k:round(sum(bool(r[k]) for r in rows)/len(rows),6) for k in rows[0] if k.endswith("changed")}
    return {"pairs":len(rows),"change_fraction":summary,"rows":rows,"replay_failures":failures}


def parameter_catalog() -> List[ConstraintProfile]:
    """Fixed 3x3x3 catalog for inverse-controllability testing."""
    values_k=(0.35,0.60,0.85); values_p=(0.30,0.85,1.40); values_t=(0.55,0.73,0.91)
    return [ConstraintProfile(f"q{ik}{ip}{it}",k,p,t,"v0.5 catalog point")
            for ik,k in enumerate(values_k) for ip,p in enumerate(values_p) for it,t in enumerate(values_t)]

def vector_distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((float(x)-float(y))**2 for x,y in zip(a,b)))

def parameter_distance(a: ConstraintProfile,b: ConstraintProfile)->float:
    return math.sqrt(((a.kappa-b.kappa)/0.5)**2+((a.phi-b.phi)/1.1)**2+((a.target_stability-b.target_stability)/0.36)**2)

def run_parameter_retrieval(train_seeds: Sequence[int], test_seeds: Sequence[int]) -> Dict[str,object]:
    catalog=parameter_catalog(); train=[]; tests=[]; replay=0
    for p in catalog:
        for s in train_seeds:
            a=LocalGrowth3D(p,s,GrowthConfig()).run(); replay+=int(not a.replay_pass); train.append((p,a.features.classifier_vector()))
        for s in test_seeds:
            a=LocalGrowth3D(p,s,GrowthConfig()).run(); replay+=int(not a.replay_pass); tests.append((p,s,a.features.classifier_vector()))
    labeled=[(p.name,v) for p,v in train]
    centroids,means,scales=train_centroids(labeled)
    byname={p.name:p for p in catalog}; exact=0; near=0; dists=[]; margins=[]; rows=[]
    for actual,seed,v in tests:
        z=normalize(v,means,scales)
        ranked=sorted(((sum((z[i]-c[i])**2 for i in range(len(z))),name) for name,c in centroids.items()))
        pred=byname[ranked[0][1]]; pd=parameter_distance(actual,pred); margin=ranked[1][0]-ranked[0][0]
        exact+=int(pred.name==actual.name); near+=int(pd<=1.01); dists.append(pd); margins.append(margin)
        rows.append({"actual":actual.name,"predicted":pred.name,"seed":seed,"parameter_distance":round(pd,6),"confidence_margin":round(margin,6)})
    n=len(rows)
    return {"catalog_points":len(catalog),"train_seeds_per_point":len(train_seeds),"test_seeds_per_point":len(test_seeds),
            "exact_retrieval_accuracy":round(exact/n,6),"nearest_grid_neighbor_accuracy":round(near/n,6),
            "mean_normalized_parameter_error":round(statistics.fmean(dists),6),"median_confidence_margin":round(statistics.median(margins),6),
            "replay_failures":replay,"rows":rows}

def run_continuous_inverse_test(train_seeds: Sequence[int], test_seeds: Sequence[int]) -> Dict[str,object]:
    """Interpolate between catalog points and recover continuous parameters by inverse-distance weighting."""
    rng=random.Random(55031); catalog=parameter_catalog(); train=[]; replay=0
    for p in catalog:
        vecs=[]
        for s in train_seeds:
            a=LocalGrowth3D(p,s,GrowthConfig()).run(); replay+=int(not a.replay_pass); vecs.append(a.features.classifier_vector())
        train.append((p,[statistics.fmean(row[i] for row in vecs) for i in range(len(vecs[0]))]))
    means=[statistics.fmean(v[i] for _,v in train) for i in range(len(train[0][1]))]
    scales=[statistics.pstdev([v[i] for _,v in train]) or 1.0 for i in range(len(means))]
    targets=[]
    for j in range(12):
        targets.append(ConstraintProfile(f"u{j}",rng.uniform(.37,.83),rng.uniform(.34,1.36),rng.uniform(.58,.88),"unseen continuous target"))
    rows=[]
    for p in targets:
        for s in test_seeds:
            a=LocalGrowth3D(p,s,GrowthConfig()).run(); replay+=int(not a.replay_pass); z=normalize(a.features.classifier_vector(),means,scales)
            ranked=[]
            for q,v in train:
                qz=normalize(v,means,scales); d=max(1e-9,vector_distance(z,qz)); ranked.append((d,q))
            ranked.sort(key=lambda x:(x[0],x[1].name)); top=ranked[:4]; ws=[1/x[0] for x in top]; den=sum(ws)
            kh=sum(w*q.kappa for w,(_,q) in zip(ws,top))/den; ph=sum(w*q.phi for w,(_,q) in zip(ws,top))/den; tt=sum(w*q.target_stability for w,(_,q) in zip(ws,top))/den
            err=math.sqrt(((kh-p.kappa)/.5)**2+((ph-p.phi)/1.1)**2+((tt-p.target_stability)/.36)**2)
            confidence=(ranked[1][0]-ranked[0][0])/(ranked[1][0]+1e-9)
            rows.append({"target":p.name,"seed":s,"true":[round(p.kappa,5),round(p.phi,5),round(p.target_stability,5)],"predicted":[round(kh,5),round(ph,5),round(tt,5)],"normalized_error":round(err,6),"confidence":round(confidence,6)})
    errs=[r["normalized_error"] for r in rows]; conf=[r["confidence"] for r in rows]
    # confidence calibration: high-confidence half should have lower error
    med=statistics.median(conf); hi=[e for e,c in zip(errs,conf) if c>=med]; lo=[e for e,c in zip(errs,conf) if c<med]
    return {"unseen_parameter_points":len(targets),"test_seeds_per_point":len(test_seeds),"mean_normalized_error":round(statistics.fmean(errs),6),
            "median_normalized_error":round(statistics.median(errs),6),"high_confidence_mean_error":round(statistics.fmean(hi),6),
            "low_confidence_mean_error":round(statistics.fmean(lo),6),"confidence_is_calibrated":statistics.fmean(hi)<statistics.fmean(lo),
            "replay_failures":replay,"rows":rows}

def independent_basic_features(nodes: Dict[int,Point3], edges: Sequence[Edge3])->Dict[str,int]:
    adj={i:set() for i in nodes}
    for a,b in edges: adj[a].add(b); adj[b].add(a)
    return {"node_count":len(nodes),"edge_count":len(edges),"branch_nodes":sum(len(v)>=3 for v in adj.values()),"leaves":sum(len(v)==1 for i,v in adj.items() if i!=0),"height":max(p[2] for p in nodes.values())-min(p[2] for p in nodes.values())}

def run_dual_extractor_audit(seeds: Sequence[int])->Dict[str,object]:
    rows=[]; all_pass=True
    for p in parameter_catalog()[::4]:
        for s in seeds:
            a=LocalGrowth3D(p,s,GrowthConfig()).run(); b=independent_basic_features(a.nodes,a.edges)
            expected={k:getattr(a.features,k) for k in b}; passed=b==expected; all_pass &= passed
            rows.append({"profile":p.name,"seed":s,"pass":passed,"primary":expected,"independent":b})
    return {"pass":all_pass,"cases":len(rows),"rows":rows}

def main() -> None:
    parser = argparse.ArgumentParser(description=f"{PROJECT} v{VERSION}")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="balanced")
    parser.add_argument("--seed", type=int, default=7317)
    parser.add_argument("--no-persistence", action="store_true")
    parser.add_argument("--single", action="store_true")
    parser.add_argument("--deep-suite", action="store_true")
    parser.add_argument("--all-receipts", action="store_true")
    parser.add_argument("--export-dir", default="")
    args = parser.parse_args()

    config = GrowthConfig(persistent=not args.no_persistence)
    sample = LocalGrowth3D(PROFILES[args.profile], args.seed, config).run()
    print(f"{PROJECT} v{VERSION}"); print("="*88)
    print(json.dumps(artifact_summary(sample), indent=2))
    print("\nTOP PROJECTION (symbol = highest z at x,y; B = base)"); print(projection_xy(sample.nodes))
    print("\nSIDE PROJECTION (x-z occupancy)"); print(projection_xz(sample.nodes))
    compact_receipts(sample.receipts, limit=10_000 if args.all_receipts else 28)

    suite: Dict[str, object] = {"not_run": True}
    if not args.single:
        if args.deep_suite:
            train=list(range(100,130)); test=list(range(900,930)); causal=list(range(1500,1530)); sweep=list(range(1600,1620)); sig=list(range(1700,1730)); draws=1000
        else:
            train=list(range(100,112)); test=list(range(900,909)); causal=list(range(1500,1512)); sweep=list(range(1600,1608)); sig=list(range(1700,1712)); draws=300
        determinism=run_determinism_test([7317,19,41] if args.deep_suite else [7317,19],config)
        inverse=run_inverse_test(train,test,config,collapsed_control=False)
        collapsed=run_inverse_test(train,test,config,collapsed_control=True)
        feature=run_feature_ablation(train,test,config)
        causal_energy=run_repeated_energy_controls(causal)
        sweeps=run_one_parameter_sweeps(sweep)
        pairwise=run_pairwise_profile_diagnosis(train,test)
        permutation=run_permutation_significance(train,test,draws)
        washout=run_imprint_washout(train,test,5)
        signature=run_signature_position_audit(sig)
        separation=run_geometry_state_separation(train,test,5)
        transfer_pairing=run_transfer_hash_pairing(causal,5)
        retrieval=run_parameter_retrieval(train[:8] if args.deep_suite else train[:6], test[:6] if args.deep_suite else test[:3])
        continuous=run_continuous_inverse_test(train[:8] if args.deep_suite else train[:6], test[:5] if args.deep_suite else test[:3])
        dual=run_dual_extractor_audit([19,41,7317] if args.deep_suite else [19,7317])
        replay_failures=(inverse["replay_failures"]+collapsed["replay_failures"]+feature["replay_failures"]+
                         causal_energy["replay_failures"]+sweeps["replay_failures"]+pairwise["replay_failures"]+
                         permutation["replay_failures"]+washout["replay_failures"]+separation["replay_failures"]+transfer_pairing["replay_failures"]+retrieval["replay_failures"]+continuous["replay_failures"])
        shape=float(feature["feature_groups"]["shape_without_size"]["accuracy"])
        suite={
          "determinism":determinism,
          "inverse_rule_family_recovery":inverse,
          "collapsed_profile_negative_control":collapsed,
          "feature_ablation":feature,
          "permutation_significance":permutation,
          "pairwise_balanced_diagnosis":pairwise,
          "one_parameter_at_a_time_sweeps":sweeps,
          "repeated_equal_energy_causal_controls":causal_energy,
          "imprint_neutral_washout_test":washout,
          "signature_position_audit":signature,
          "geometry_state_separation":separation,
          "matched_transfer_hash_audit":transfer_pairing,
          "parameter_catalog_retrieval":retrieval,
          "continuous_inverse_controllability":continuous,
          "dual_feature_extractor_audit":dual,
          "total_replay_failures":replay_failures,
          "declared_pass_gate":{
            "all_replay_hashes_match":True,
            "true_accuracy_exceeds_95th_permutation_percentile":True,
            "shape_without_size_exceeds_chance":True,
            "one_parameter_ordered_trend_required":True,
            "equal_energy_timing_effect_replicates":True,
            "imprint_recovery_after_neutral_washout_exceeds_chance":True,
            "collapsed_and_reset_controls_at_or_near_chance":True,
            "geometry_imprint_recovery_exceeds_chance":True,
            "reset_all_returns_to_chance":True,
            "parameter_retrieval_above_random_catalog_baseline":True,
            "confidence_calibration_required":True,
            "independent_feature_extractor_must_match":True,
          }
        }
        suite["overall_pass"]=(bool(determinism["pass"]) and replay_failures==0 and
            bool(permutation["true_exceeds_95th_percentile"]) and shape>1/3 and
            bool(sweeps["at_least_one_ordered_trend"]) and bool(causal_energy["timing_effect_replicated"]) and
            bool(washout["retention_above_chance"]) and bool(washout["reset_at_or_near_chance"]) and
            float(collapsed["accuracy"])<=0.50 and
            bool(separation["summary"]["geometry_is_memory_carrier"]) and bool(separation["summary"]["reset_returns_to_chance"]) and
            float(retrieval["exact_retrieval_accuracy"])>1/27 and bool(continuous["confidence_is_calibrated"]) and bool(dual["pass"]))
        print("\nVALIDATION SUITE"); print("="*88); print(json.dumps(suite,indent=2))

    print("\nCLAIM BOUNDARY")
    print("- Software-only CNT-like graph morphology; no CNT chemistry or wet-lab validation.")
    print("- kappa, phi, and T remain software boundary-condition parameters.")
    print("- Neutral washout tests retained software morphology, not biological cognition.")
    print("- Equal declared energy does not establish thermodynamic equivalence.")
    print("- CB1 signatures remain lossy diagnostics; no intrinsic symbolism is claimed.")
    print("- v0.4 separates information in frozen geometry from information in live continuation state.")
    print("- v0.5 tests morphology-to-parameter retrieval and inverse controllability; it is not arbitrary target compilation.")
    if args.export_dir:
        out=Path(args.export_dir); write_artifacts(sample,suite,out); print(f"\nArtifacts written to: {out}")
    else:
        print("\nPrint-only mode. Use --export-dir NAME to write JSON, OBJ, and a hash manifest.")

if __name__ == "__main__":
    main()

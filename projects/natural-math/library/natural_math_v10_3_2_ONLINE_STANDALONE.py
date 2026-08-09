#!/usr/bin/env python3
"""Natural Math Receipt Replay v9 — standalone Python experiment.

This is a test harness for the experimental maze rules:
- locally sensed imperfect beacon
- persistent explored passages
- decision keepers at branching junctions
- explicit passage states: explored / in_progress / interrupted / exhausted / verified
- legal state-transition enforcement
- deterministic receipt replay and live/replayed state hashing
- relay anchors and safe-return reserve
- frozen route, auditor, and read-only follower
- structured decision receipts printed and exported

The scout never receives a solved route. Global breadth-first search is used only
by the test harness for setup validation and final verification.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

Point = Tuple[int, int]
Edge = Tuple[Point, Point]
DIRS: Tuple[Point, ...] = ((1, 0), (0, 1), (-1, 0), (0, -1))


def edge(a: Point, b: Point) -> Edge:
    return (a, b) if a <= b else (b, a)


def point_text(p: Point) -> str:
    return f"{p[0]},{p[1]}"


def neighbors(grid: Tuple[str, ...], p: Point) -> List[Point]:
    x, y = p
    out: List[Point] = []
    for dx, dy in DIRS:
        nx, ny = x + dx, y + dy
        if 0 <= ny < len(grid) and 0 <= nx < len(grid[0]) and grid[ny][nx] != "#":
            out.append((nx, ny))
    return out


def bfs_grid(grid: Tuple[str, ...], start: Point) -> Dict[Point, int]:
    q = deque([start])
    dist = {start: 0}
    while q:
        p = q.popleft()
        for n in neighbors(grid, p):
            if n not in dist:
                dist[n] = dist[p] + 1
                q.append(n)
    return dist


def shortest_on_edges(
    grid: Tuple[str, ...], start: Point, goal: Point, known_edges: Set[Edge]
) -> Optional[List[Point]]:
    q = deque([start])
    parent: Dict[Point, Optional[Point]] = {start: None}
    while q:
        p = q.popleft()
        if p == goal:
            break
        for n in neighbors(grid, p):
            if n not in parent and edge(p, n) in known_edges:
                parent[n] = p
                q.append(n)
    if goal not in parent:
        return None
    out: List[Point] = []
    cur: Optional[Point] = goal
    while cur is not None:
        out.append(cur)
        cur = parent[cur]
    out.reverse()
    return out


def generate_case(width: int, height: int, seed: int, loop_rate: float) -> Tuple[Tuple[str, ...], Point, Point]:
    rng = random.Random(seed)
    grid = [["#"] * width for _ in range(height)]

    def carve(x: int, y: int) -> None:
        grid[y][x] = "."
        directions = list(DIRS)
        rng.shuffle(directions)
        for dx, dy in directions:
            nx, ny = x + 2 * dx, y + 2 * dy
            if nx <= 0 or ny <= 0 or nx >= width - 1 or ny >= height - 1:
                continue
            if grid[ny][nx] != "#":
                continue
            grid[y + dy][x + dx] = "."
            carve(nx, ny)

    carve(1, 1)
    for _ in range(int(width * height * loop_rate)):
        x = rng.randrange(1, width - 1)
        y = rng.randrange(1, height - 1)
        if grid[y][x] != "#":
            continue
        horizontal = grid[y][x - 1] == "." and grid[y][x + 1] == "."
        vertical = grid[y - 1][x] == "." and grid[y + 1][x] == "."
        if horizontal or vertical:
            grid[y][x] = "."

    base = (1, 1)
    temp = tuple("".join(row) for row in grid)
    distances = bfs_grid(temp, base)
    farthest = max(distances.values())
    candidates = [p for p, d in distances.items() if d >= farthest - 2]
    resource = rng.choice(candidates)
    grid[base[1]][base[0]] = "B"
    grid[resource[1]][resource[0]] = "R"
    return tuple("".join(row) for row in grid), base, resource


@dataclass(frozen=True)
class Receipt:
    receipt_id: int
    movement_step: int
    sortie: int
    actor: str
    decision: str
    reason: str
    local_evidence: Dict[str, Any]
    consequence: str
    event_type: str = "decision"
    entity_type: str = ""
    entity_id: str = ""
    from_state: str = ""
    to_state: str = ""


@dataclass
class Keeper:
    position: Point
    tried: Set[Edge] = field(default_factory=set)
    failed: Set[Edge] = field(default_factory=set)


@dataclass
class RunResult:
    success: bool
    failure: str
    seed: int
    grid: str
    movement_steps: int
    sorties: int
    safe_returns: int
    keepers: int
    relays: int
    assignments: int
    effective_branch_changes: int
    repeated_failed_branches: int
    exhausted_passages: int
    route_length: int
    audit_pass: bool
    follower_pass: bool
    route_unchanged: bool
    receipt_count: int
    unexplained_decisions: int
    duplicate_transitions: int
    illegal_transitions: int
    interrupted_passages: int
    resumed_passages: int
    replay_pass: bool
    replay_errors: List[str]
    live_state_hash: str
    replay_state_hash: str
    receipts: List[Receipt]


class DecisionReceiptMaze:
    def __init__(
        self,
        grid: Tuple[str, ...],
        base: Point,
        resource: Point,
        *,
        seed: int,
        sortie_budget: int,
        reserve: int,
        max_sorties: int,
    ) -> None:
        self.grid = grid
        self.base = base
        self.resource = resource
        self.seed = seed
        self.sortie_budget = sortie_budget
        self.reserve = reserve
        self.max_sorties = max_sorties

        self.receipts: List[Receipt] = []
        self.moves = 0
        self.sortie = 0
        self.safe_returns = 0
        self.known_edges: Set[Edge] = set()
        self.visited: Set[Point] = {base}
        self.dead: Set[Point] = set()
        self.keepers: Dict[Point, Keeper] = {}
        self.relays: Set[Point] = {base}
        self.relay_launches: Dict[Point, int] = {base: 0}
        self.passage_state: Dict[Edge, str] = {}
        self.assignments = 0
        self.switches = 0
        self.repeated_failed = 0
        self.route: List[Point] = []
        self.audit_pass = False
        self.follower_pass = False
        self.route_unchanged = True
        self.failure = ""
        self.duplicate_transitions = 0
        self.illegal_transitions = 0
        self.resumed_passages = 0
        self.replay_pass = False
        self.replay_errors: List[str] = []
        self.live_state_hash = ""
        self.replay_state_hash = ""

        rng = random.Random(seed ^ 0xD3C1510A)
        reachable = bfs_grid(grid, base)
        self.noise = {p: (rng.random() - 0.5) * 4.0 for p in reachable}

    def receipt(
        self,
        actor: str,
        decision: str,
        reason: str,
        local_evidence: Dict[str, Any],
        consequence: str,
        *,
        event_type: str = "decision",
        entity_type: str = "",
        entity_id: str = "",
        from_state: str = "",
        to_state: str = "",
    ) -> None:
        self.receipts.append(
            Receipt(
                receipt_id=len(self.receipts) + 1,
                movement_step=self.moves,
                sortie=self.sortie,
                actor=actor,
                decision=decision,
                reason=reason,
                local_evidence=local_evidence,
                consequence=consequence,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                from_state=from_state,
                to_state=to_state,
            )
        )


    @staticmethod
    def edge_id(e: Edge) -> str:
        return f"{point_text(e[0])}|{point_text(e[1])}"

    def transition_passage(
        self,
        e: Edge,
        to_state: str,
        *,
        actor: str,
        decision: str,
        reason: str,
        evidence: Dict[str, Any],
        consequence: str,
    ) -> bool:
        current = self.passage_state.get(e, "untried")
        legal = {
            "untried": {"explored", "in_progress"},
            "explored": {"in_progress", "verified"},
            "in_progress": {"interrupted", "exhausted", "verified"},
            "interrupted": {"in_progress", "verified"},
            "exhausted": set(),
            "verified": set(),
        }
        if current == to_state:
            self.duplicate_transitions += 1
            self.receipt(
                actor, f"observe existing {to_state} passage",
                "the requested state was already present; no new transition was applied",
                {**evidence, "passage": self.edge_id(e), "state": current},
                "state unchanged", event_type="state_observation",
                entity_type="passage", entity_id=self.edge_id(e),
                from_state=current, to_state=current,
            )
            return False
        if to_state not in legal.get(current, set()):
            self.illegal_transitions += 1
            self.receipt(
                actor, f"reject illegal transition {current} -> {to_state}",
                "the passage-state policy does not permit this transition",
                {**evidence, "passage": self.edge_id(e)},
                "state unchanged", event_type="transition_rejected",
                entity_type="passage", entity_id=self.edge_id(e),
                from_state=current, to_state=to_state,
            )
            return False
        if current == "interrupted" and to_state == "in_progress":
            self.resumed_passages += 1
        self.passage_state[e] = to_state
        self._invalidate_active_targets({e[0], e[1]})
        self.receipt(
            actor, decision, reason,
            {**evidence, "passage": self.edge_id(e)}, consequence,
            event_type="state_transition", entity_type="passage",
            entity_id=self.edge_id(e), from_state=current, to_state=to_state,
        )
        return True

    def _affected_target_cells(self, cells: Set[Point]) -> Set[Point]:
        affected = set(cells)
        for cell in list(cells):
            affected.update(neighbors(self.grid, cell))
        return affected

    def _invalidate_active_targets(self, cells: Optional[Set[Point]] = None) -> None:
        if not hasattr(self, "_active_targets_initialized"):
            return
        if cells is None:
            self._active_targets_full_dirty = True
            self._active_target_dirty_cells.clear()
        elif not self._active_targets_full_dirty:
            self._active_target_dirty_cells.update(self._affected_target_cells(cells))

    def _add_known_edge(self, e: Edge) -> None:
        if e not in self.known_edges:
            self.known_edges.add(e)
            self._known_edges_version += 1
            self._current_bfs_key = None
            self._anchor_bfs_key = None
            self._adjacency_cache_version = -1
            self._invalidate_active_targets({e[0], e[1]})

    def _add_visited(self, cell: Point) -> None:
        if cell not in self.visited:
            self.visited.add(cell)
            self._invalidate_active_targets({cell})

    def _mark_dead(self, cell: Point) -> None:
        if cell not in self.dead:
            self.dead.add(cell)
            self._invalidate_active_targets({cell})

    def _adjacency(self) -> Dict[Point, List[Point]]:
        if self._adjacency_cache_version == self._known_edges_version:
            self.adjacency_cache_hits += 1
            return self._adjacency_cache
        adjacency: Dict[Point, List[Point]] = {}
        for a, b in self.known_edges:
            adjacency.setdefault(a, []).append(b)
            adjacency.setdefault(b, []).append(a)
        for values in adjacency.values():
            values.sort()
        self._adjacency_cache = adjacency
        self._adjacency_cache_version = self._known_edges_version
        self.adjacency_rebuilds += 1
        return adjacency

    def _bfs_all_targets(self, start: Point) -> Tuple[Dict[Point, int], Dict[Point, Optional[Point]]]:
        adjacency = self._adjacency()
        dist: Dict[Point, int] = {start: 0}
        parent: Dict[Point, Optional[Point]] = {start: None}
        queue = deque([start])
        expanded = 0
        while queue:
            cur = queue.popleft(); expanded += 1
            for nxt in adjacency.get(cur, []):
                if nxt in dist: continue
                dist[nxt] = dist[cur] + 1
                parent[nxt] = cur
                queue.append(nxt)
        self.bfs_calls += 1
        self.bfs_nodes_expanded += expanded
        return dist, parent

    @staticmethod
    def _reconstruct_path(parent: Dict[Point, Optional[Point]], goal: Point) -> Optional[List[Point]]:
        if goal not in parent: return None
        out = [goal]
        while parent[out[-1]] is not None:
            out.append(parent[out[-1]])
        out.reverse()
        return out

    def _ensure_bfs_cache(self, current: Point, anchor: Point) -> None:
        current_key = (current, self._known_edges_version)
        anchor_key = (anchor, self._known_edges_version)
        if self._current_bfs_key == current_key:
            self.current_bfs_cache_hits += 1
        else:
            self._bfs_from_current = self._bfs_all_targets(current)
            self._current_bfs_key = current_key
        if self._anchor_bfs_key == anchor_key:
            self.anchor_bfs_cache_hits += 1
        else:
            self._bfs_from_anchor = self._bfs_all_targets(anchor)
            self._anchor_bfs_key = anchor_key

    def structural_snapshot(self) -> Dict[str, Any]:
        return {
            "passages": {self.edge_id(e): s for e, s in sorted(self.passage_state.items())},
            "keepers": sorted(point_text(p) for p in self.keepers),
            "relays": sorted(point_text(p) for p in self.relays),
            "route": [point_text(p) for p in self.route],
        }

    @staticmethod
    def snapshot_hash(snapshot: Dict[str, Any]) -> str:
        import hashlib
        payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def replay_receipts(self) -> Tuple[bool, List[str], Dict[str, Any]]:
        passages: Dict[str, str] = {}
        keepers: Set[str] = set()
        relays: Set[str] = {point_text(self.base)}
        route: List[str] = []
        errors: List[str] = []
        last_id = 0
        legal = {
            "untried": {"explored", "in_progress"},
            "explored": {"in_progress", "verified"},
            "in_progress": {"interrupted", "exhausted", "verified"},
            "interrupted": {"in_progress", "verified"},
            "exhausted": set(),
            "verified": set(),
        }
        for r in self.receipts:
            if r.receipt_id != last_id + 1:
                errors.append(f"receipt sequence break at {r.receipt_id}")
            last_id = r.receipt_id
            if r.event_type == "state_transition" and r.entity_type == "passage":
                current = passages.get(r.entity_id, "untried")
                if current != r.from_state:
                    errors.append(f"receipt {r.receipt_id}: expected {current}, claims {r.from_state}")
                    continue
                if r.to_state not in legal.get(current, set()):
                    errors.append(f"receipt {r.receipt_id}: illegal {current}->{r.to_state}")
                    continue
                passages[r.entity_id] = r.to_state
            elif r.event_type == "keeper_created":
                keepers.add(r.entity_id)
            elif r.event_type == "relay_created":
                relays.add(r.entity_id)
            elif r.event_type == "route_frozen":
                route = list(r.local_evidence.get("route_points", []))
        snapshot = {
            "passages": dict(sorted(passages.items())),
            "keepers": sorted(keepers),
            "relays": sorted(relays),
            "route": route,
        }
        return not errors, errors, snapshot

    def signal(self, p: Point) -> float:
        return math.dist(p, self.resource) + self.noise.get(p, 0.0)

    def unresolved_candidates(self, p: Point) -> List[Point]:
        out: List[Point] = []
        keeper = self.keepers.get(p)
        for n in neighbors(self.grid, p):
            e = edge(p, n)
            state = self.passage_state.get(e, "untried")
            if n in self.dead or state in {"in_progress", "exhausted", "verified"}:
                continue
            if e in self.known_edges and state != "interrupted":
                continue
            if keeper and state != "interrupted" and (e in keeper.tried or e in keeper.failed):
                continue
            out.append(n)
        return out

    def choose_relay(self) -> Point:
        frontier_options: List[Tuple[int, float, Point, Point]] = []
        for relay in self.relays:
            for q in self.visited:
                if not self.unresolved_candidates(q):
                    continue
                path = shortest_on_edges(self.grid, relay, q, self.known_edges)
                if path is None:
                    continue
                distance = len(path) - 1
                if distance + self.reserve + 2 <= self.sortie_budget:
                    frontier_options.append((distance, self.signal(q), relay, q))
        if not frontier_options:
            chosen, frontier, distance = self.base, self.base, 0
        else:
            distance, _, chosen, frontier = min(frontier_options, key=lambda x: (x[0], x[1], x[2], x[3]))
        self.relay_launches[chosen] = self.relay_launches.get(chosen, 0) + 1
        self.receipt(
            "relay_arbitrator",
            f"select relay {point_text(chosen)}",
            "closest safe relay to a known unresolved frontier",
            {
                "selected_relay": point_text(chosen),
                "frontier": point_text(frontier),
                "known_travel_distance": distance,
                "sortie_budget": self.sortie_budget,
                "reserve": self.reserve,
                "available_relays": [point_text(p) for p in sorted(self.relays)],
            },
            "sortie launched",
        )
        return chosen

    def interrupt_active_branch(self, keeper_pos: Point, branch_edge: Edge) -> None:
        self.transition_passage(
            branch_edge, "interrupted", actor="keeper",
            decision=f"interrupt passage {self.edge_id(branch_edge)}",
            reason="the sortie ended for return-reserve reasons before the branch was fully resolved",
            evidence={"keeper": point_text(keeper_pos)},
            consequence="the branch remains eligible for a later sortie",
        )


    def run(self) -> RunResult:
        reachable = bfs_grid(self.grid, self.base)
        if self.resource not in reachable:
            self.failure = "setup error: base and resource are disconnected"
            self.receipt(
                "setup_gate",
                "reject challenge",
                "resource is not reachable from base",
                {"reachable_cells": len(reachable)},
                "agent run not started",
            )
            return self.result(False)

        self.receipt(
            "setup_gate",
            "admit challenge",
            "base and resource are connected",
            {
                "reachable_cells": len(reachable),
                "grid": f"{len(self.grid[0])}x{len(self.grid)}",
                "base": point_text(self.base),
                "resource": point_text(self.resource),
            },
            "exploration permitted",
        )

        found = False
        discovery_position: Optional[Point] = None

        for sortie in range(1, self.max_sorties + 1):
            self.sortie = sortie
            anchor = self.choose_relay()
            p = anchor
            previous: Optional[Point] = None
            remaining = self.sortie_budget
            active_assignments: List[Tuple[Point, Edge]] = []

            while remaining > 0:
                if p == self.resource:
                    found = True
                    discovery_position = p
                    break

                back = shortest_on_edges(self.grid, p, anchor, self.known_edges)
                return_cost = 0 if p == anchor else (len(back) - 1 if back else 10**9)
                adjacent = neighbors(self.grid, p)

                if len(adjacent) >= 3 and p not in self.keepers:
                    self.keepers[p] = Keeper(position=p)
                    self.receipt(
                        "scout",
                        f"station decision keeper at {point_text(p)}",
                        "a local junction contains multiple adjacent passages and requires persistent branch memory",
                        {
                            "junction": point_text(p),
                            "adjacent_passages": [point_text(n) for n in adjacent],
                            "remaining": remaining,
                            "return_cost": return_cost,
                        },
                        "future visits can exclude tried and exhausted branches",
                        event_type="keeper_created", entity_type="keeper", entity_id=point_text(p),
                    )

                candidates = self.unresolved_candidates(p)
                safe = [n for n in candidates if remaining >= return_cost + self.reserve + 2]

                if safe:
                    safe.sort(key=lambda n: (self.signal(n), DIRS.index((n[0] - p[0], n[1] - p[1]))))
                    n = safe[0]
                    e = edge(p, n)
                    keeper = self.keepers.get(p)
                    if keeper:
                        if keeper.tried:
                            self.switches += 1
                        keeper.tried.add(e)
                        self.assignments += 1
                        self.transition_passage(
                            e, "in_progress", actor="keeper",
                            decision=f"assign branch {point_text(n)}",
                            reason="branch is locally available, not exhausted, and preserves the return reserve",
                            evidence={
                                "keeper": point_text(p),
                                "chosen_passage": [point_text(e[0]), point_text(e[1])],
                                "eligible_branches": [point_text(x) for x in safe],
                                "signal_values": {point_text(x): round(self.signal(x), 4) for x in safe},
                                "remaining": remaining,
                                "return_cost": return_cost,
                                "reserve": self.reserve,
                                "tried_passages": len(keeper.tried),
                                "failed_passages": len(keeper.failed),
                            },
                            consequence="passage becomes in progress and cannot be independently reassigned",
                        )
                        active_assignments.append((p, e))

                    if self.passage_state.get(e) == "exhausted":
                        self.repeated_failed += 1
                    if e not in self.known_edges and self.passage_state.get(e, "untried") == "untried":
                        self.transition_passage(
                            e, "explored", actor="scout", decision=f"record explored passage {self.edge_id(e)}",
                            reason="the scout traversed this passage for the first time",
                            evidence={"from": point_text(p), "to": point_text(n)},
                            consequence="the passage becomes part of locally persistent explored structure",
                        )
                    self._add_known_edge(e)
                    self.visited.add(n)
                    previous, p = p, n
                    self.moves += 1
                    remaining -= 1
                    continue

                # A terminal newly explored branch becomes a persistent failed consequence.
                if p != anchor and not candidates and len(adjacent) <= 1:
                    self._mark_dead(p)
                    if previous is not None:
                        dead_edge = edge(previous, p)
                        if self.passage_state.get(dead_edge) == "in_progress":
                            self.transition_passage(
                                dead_edge, "exhausted", actor="keeper",
                                decision=f"mark passage {self.edge_id(dead_edge)} exhausted",
                                reason="the assigned passage terminates at a locally confirmed dead end",
                                evidence={"dead_end": point_text(p)},
                                consequence="future decisions must exclude this passage",
                            )

                # Move through known structure to another unresolved decision point if safe.
                alternatives: List[Tuple[int, float, Point, List[Point]]] = []
                for q in self.visited:
                    if q == p or not self.unresolved_candidates(q):
                        continue
                    travel = shortest_on_edges(self.grid, p, q, self.known_edges)
                    home = shortest_on_edges(self.grid, q, anchor, self.known_edges)
                    if travel and home:
                        needed = (len(travel) - 1) + (len(home) - 1) + self.reserve + 2
                        if remaining >= needed:
                            alternatives.append((len(travel) - 1, self.signal(q), q, travel))
                if alternatives:
                    _, _, target, travel = min(alternatives, key=lambda x: (x[0], x[1], x[2]))
                    self.receipt(
                        "scout",
                        f"travel to unresolved frontier {point_text(target)}",
                        "no safe new branch is available at the current position, but another known frontier remains reachable",
                        {
                            "from": point_text(p),
                            "frontier": point_text(target),
                            "travel_cost": len(travel) - 1,
                            "remaining": remaining,
                            "reserve": self.reserve,
                        },
                        "exploration continues without returning to the relay",
                    )
                    for step_point in travel[1:]:
                        previous, p = p, step_point
                        self.moves += 1
                        remaining -= 1
                    continue

                # Create a relay only when the current location is meaningfully separated from anchor.
                if p not in self.relays and return_cost >= 6 and remaining > self.reserve + 4:
                    self.relays.add(p)
                    self.relay_launches.setdefault(p, 0)
                    self.receipt(
                        "scout",
                        f"establish relay {point_text(p)}",
                        "current position extends the connected safe exploration radius and retains a known route to the active relay",
                        {
                            "new_relay": point_text(p),
                            "active_relay": point_text(anchor),
                            "known_return_cost": return_cost,
                            "remaining": remaining,
                            "reserve": self.reserve,
                        },
                        "relay becomes eligible for later frontier arbitration",
                        event_type="relay_created", entity_type="relay", entity_id=point_text(p),
                    )

                # Close unresolved active assignments on retreat if they produced no route to resource.
                for keeper_pos, assigned_edge in active_assignments:
                    if self.passage_state.get(assigned_edge) == "in_progress":
                        self.interrupt_active_branch(keeper_pos, assigned_edge)
                active_assignments.clear()

                back = shortest_on_edges(self.grid, p, anchor, self.known_edges)
                if back is None:
                    self.failure = "no known path to active relay"
                    self.receipt(
                        "scout",
                        "fail run",
                        "the scout cannot reconstruct a path to its active relay",
                        {"position": point_text(p), "active_relay": point_text(anchor)},
                        "exploration terminated",
                    )
                    return self.result(False)

                self.receipt(
                    "scout",
                    f"return to relay {point_text(anchor)}",
                    "no currently reachable unresolved branch satisfies travel plus return reserve",
                    {
                        "position": point_text(p),
                        "remaining": remaining,
                        "known_return_cost": len(back) - 1,
                        "reserve": self.reserve,
                        "known_unresolved_frontiers": sum(1 for q in self.visited if self.unresolved_candidates(q)),
                    },
                    "safe return initiated",
                )
                self.moves += len(back) - 1
                self.safe_returns += 1
                remaining -= len(back) - 1
                break

            if found:
                break

        if not found or discovery_position is None:
            self.failure = "maximum safe sorties exhausted before discovery"
            self.receipt(
                "run_controller",
                "fail run",
                "the resource was not discovered within the permitted number of safe sorties",
                {
                    "sorties": self.sortie,
                    "moves": self.moves,
                    "visited_cells": len(self.visited),
                    "relays": len(self.relays),
                    "keepers": len(self.keepers),
                },
                "no route promoted",
            )
            return self.result(False)

        route = shortest_on_edges(self.grid, self.base, self.resource, self.known_edges)
        if route is None:
            self.failure = "resource found but no base-to-resource route exists in explored evidence"
            return self.result(False)
        self.route = route
        frozen = tuple(route)
        for i in range(1, len(route)):
            route_edge = edge(route[i - 1], route[i])
            self.transition_passage(
                route_edge, "verified", actor="scout", decision=f"verify route passage {self.edge_id(route_edge)}",
                reason="the passage belongs to the completed base-to-resource route",
                evidence={"route_index": i - 1}, consequence="passage becomes part of the frozen verified route",
            )
        self.receipt(
            "scout",
            "freeze route",
            "the resource was found and a complete base-to-resource route exists in explored evidence",
            {
                "route_length": len(route) - 1,
                "visited_cells": len(self.visited),
                "known_edges": len(self.known_edges),
                "route_points": [point_text(x) for x in route],
            },
            "route becomes immutable input to audit",
            event_type="route_frozen", entity_type="route", entity_id="base_to_resource",
        )

        self.audit_pass = self._verify_route(route)
        self.receipt(
            "auditor",
            "approve route" if self.audit_pass else "reject route",
            "auditor traversed the frozen route out and home" if self.audit_pass else "auditor found an invalid route step",
            {"route_length": len(route) - 1, "verified_passages": len(route) - 1},
            "follower permitted" if self.audit_pass else "follower blocked",
        )
        if not self.audit_pass:
            self.failure = "audit failed"
            return self.result(False)

        self.follower_pass = self._verify_route(route)
        self.route_unchanged = tuple(route) == frozen
        self.receipt(
            "follower",
            "accept reusable route" if self.follower_pass and self.route_unchanged else "reject reusable route",
            "follower completed the auditor-approved route without modifying it"
            if self.follower_pass and self.route_unchanged
            else "follower traversal or route integrity failed",
            {"route_length": len(route) - 1, "route_unchanged": self.route_unchanged},
            "route reuse confirmed" if self.follower_pass and self.route_unchanged else "run failed",
        )
        return self.result(self.audit_pass and self.follower_pass and self.route_unchanged)

    def _verify_route(self, route: List[Point]) -> bool:
        if not route or route[0] != self.base or route[-1] != self.resource:
            return False
        for i in range(1, len(route)):
            if route[i] not in neighbors(self.grid, route[i - 1]):
                return False
            if self.passage_state.get(edge(route[i - 1], route[i])) != "verified":
                return False
        return True

    def result(self, success: bool) -> RunResult:
        unexplained = sum(1 for r in self.receipts if not r.decision.strip() or not r.reason.strip())
        live_snapshot = self.structural_snapshot()
        replay_ok, replay_errors, replay_snapshot = self.replay_receipts()
        self.live_state_hash = self.snapshot_hash(live_snapshot)
        self.replay_state_hash = self.snapshot_hash(replay_snapshot)
        if self.live_state_hash != self.replay_state_hash:
            replay_errors.append("live and replayed structural state hashes differ")
            replay_ok = False
        self.replay_pass = replay_ok
        self.replay_errors = replay_errors
        return RunResult(
            success=success,
            failure=self.failure,
            seed=self.seed,
            grid=f"{len(self.grid[0])}x{len(self.grid)}",
            movement_steps=self.moves,
            sorties=self.sortie,
            safe_returns=self.safe_returns,
            keepers=len(self.keepers),
            relays=len(self.relays),
            assignments=self.assignments,
            effective_branch_changes=self.switches,
            repeated_failed_branches=self.repeated_failed,
            exhausted_passages=sum(1 for x in self.passage_state.values() if x == "exhausted"),
            route_length=max(0, len(self.route) - 1),
            audit_pass=self.audit_pass,
            follower_pass=self.follower_pass,
            route_unchanged=self.route_unchanged,
            receipt_count=len(self.receipts),
            unexplained_decisions=unexplained,
            duplicate_transitions=self.duplicate_transitions,
            illegal_transitions=self.illegal_transitions,
            interrupted_passages=sum(1 for x in self.passage_state.values() if x == "interrupted"),
            resumed_passages=self.resumed_passages,
            replay_pass=self.replay_pass,
            replay_errors=self.replay_errors,
            live_state_hash=self.live_state_hash,
            replay_state_hash=self.replay_state_hash,
            receipts=self.receipts,
        )


def print_receipts(receipts: Iterable[Receipt], *, verbose: bool) -> None:
    print("\nDECISION RECEIPTS")
    print("-" * 118)
    print(f"{'ID':>4} {'STEP':>6} {'SORTIE':>6} {'ACTOR':<18} {'DECISION':<34} REASON")
    print("-" * 118)
    for r in receipts:
        reason = r.reason if len(r.reason) <= 62 else r.reason[:59] + "..."
        decision = r.decision if len(r.decision) <= 34 else r.decision[:31] + "..."
        print(f"{r.receipt_id:>4} {r.movement_step:>6} {r.sortie:>6} {r.actor:<18} {decision:<34} {reason}")
        if verbose:
            print("     evidence:", json.dumps(r.local_evidence, sort_keys=True))
            print("     consequence:", r.consequence)


def write_outputs(result: RunResult, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = asdict(result)
    (out_dir / "decision_receipts_result.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with (out_dir / "decision_receipts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "receipt_id",
                "movement_step",
                "sortie",
                "actor",
                "decision",
                "reason",
                "local_evidence",
                "consequence",
                "event_type",
                "entity_type",
                "entity_id",
                "from_state",
                "to_state",
            ],
        )
        writer.writeheader()
        for r in result.receipts:
            row = asdict(r)
            row["local_evidence"] = json.dumps(row["local_evidence"], sort_keys=True)
            writer.writerow(row)



# ============================================================
# v10 PHONE-FRIENDLY STANDALONE RUNNER
# ============================================================

class LimitedRelaySet(set):
    def __init__(self, values, limit: int):
        super().__init__(values)
        self.limit = max(1, int(limit))
        self.blocked_additions = 0

    def add(self, value):
        if value in self:
            return
        if len(self) >= self.limit:
            self.blocked_additions += 1
            return
        super().add(value)


class BoundaryMaze(DecisionReceiptMaze):
    def __init__(self, *args, signal_quality: float = 0.75, max_relays: int = 6, **kwargs):
        super().__init__(*args, **kwargs)
        self.signal_quality = min(1.0, max(0.0, float(signal_quality)))
        self.max_relays = max(1, int(max_relays))
        self.relays = LimitedRelaySet(self.relays, self.max_relays)

    def signal(self, p):
        distance = math.dist(p, self.resource)
        noise = self.noise.get(p, 0.0)
        return (
            self.signal_quality * distance
            + (1.0 - self.signal_quality) * 12.0 * noise
            + self.signal_quality * noise
        )



class RelayClosureBoundaryMaze(BoundaryMaze):
    """v10.3.2: relay trial, fatigue, rotation, and exclusive-frontier arbitration.

    This deliberately changes only the v10.1 relay-selection/stagnation lane.
    Navigation, keepers, passage states, receipts, replay, and safety reserve remain.
    """

    def __init__(self, *args, stale_after: int = 2, stagnation_sorties: int = 3,
                 momentum_allowance: int = 8, relay_trial_bonus: float = 1000.0,
                 max_consecutive_relay: int = 3, low_yield_threshold: float = 0.06,
                 fatigue_window: int = 3, **kwargs):
        super().__init__(*args, **kwargs)
        self.stale_after = max(1, int(stale_after))
        self.stagnation_sorties = max(1, int(stagnation_sorties))
        self.momentum_allowance = max(0, int(momentum_allowance))
        self.relay_trial_bonus = float(relay_trial_bonus)
        self.max_consecutive_relay = max(1, int(max_consecutive_relay))
        self.low_yield_threshold = max(0.0, float(low_yield_threshold))
        self.fatigue_window = max(1, int(fatigue_window))
        self.branch_attempts = {}
        self.branch_zero_yield = {}
        self.branch_last_new_cells = {}
        self.stale_passages = set()
        self.relay_stats = {self.base: self._new_relay_stat('active')}
        self.sortie_summaries = []
        self.consecutive_zero_yield = 0
        self.stagnation_detected = False
        self.final_coverage = 0.0
        self.remaining_frontiers = 0
        self.last_selected_relay = None
        self.same_relay_streak = 0
        self.relay_trials = 0
        self.base_fatigue_events = 0
        self.forced_rotations = 0
        self.relay_slots_reclaimed = 0
        self.relay_reclaim_attempts = 0
        self.failure_class = ""
        # v10.3.2 performance caches and counters
        self._active_targets = set()
        self._active_targets_initialized = False
        self._active_targets_full_dirty = True
        self._active_target_dirty_cells = set()
        self._known_edges_version = 0
        self._current_bfs_key = None
        self._anchor_bfs_key = None
        self._bfs_from_current = ({}, {})
        self._bfs_from_anchor = ({}, {})
        self._adjacency_cache_version = -1
        self._adjacency_cache = {}
        self.active_target_rebuilds = 0
        self.active_target_cache_hits = 0
        self.active_target_incremental_updates = 0
        self.active_target_cells_rechecked = 0
        self.active_target_cells_scanned = 0
        self.alternatives_scans = 0
        self.visited_cells_examined = 0
        self.active_targets_examined = 0
        self.bfs_calls = 0
        self.current_bfs_cache_hits = 0
        self.anchor_bfs_cache_hits = 0
        self.adjacency_cache_hits = 0
        self.adjacency_rebuilds = 0
        self.bfs_nodes_expanded = 0
        self.fallback_time_ms = 0.0
        self.maximum_visited_size = 1
        self.maximum_active_target_size = 0

    @staticmethod
    def _new_relay_stat(status='untested'):
        return {'status': status, 'launches': 0, 'new_cells': 0, 'new_edges': 0,
                'zero_yield': 0, 'yield_history': [], 'owned_frontiers': 0,
                'last_selected_sortie': 0}

    def _stat(self, relay):
        return self.relay_stats.setdefault(relay, self._new_relay_stat())

    def true_frontier(self, p):
        for n in neighbors(self.grid, p):
            e = edge(p, n)
            if e not in self.known_edges and self.passage_state.get(e, 'untried') == 'untried':
                return True
        return False

    def _is_active_target(self, q: Point) -> bool:
        return q in self.visited and (self.true_frontier(q) or super(BoundaryMaze, self).unresolved_candidates(q))

    def _ensure_active_targets(self) -> None:
        if not self._active_targets_initialized or self._active_targets_full_dirty:
            self.active_target_rebuilds += 1
            self.active_target_cells_scanned += len(self.visited)
            self.visited_cells_examined += len(self.visited)
            self._active_targets = {q for q in self.visited if self._is_active_target(q)}
            self._active_targets_initialized = True
            self._active_targets_full_dirty = False
            self._active_target_dirty_cells.clear()
        elif self._active_target_dirty_cells:
            dirty = sorted(self._active_target_dirty_cells)
            self.active_target_incremental_updates += 1
            self.active_target_cells_rechecked += len(dirty)
            for q in dirty:
                if self._is_active_target(q):
                    self._active_targets.add(q)
                else:
                    self._active_targets.discard(q)
            self._active_target_dirty_cells.clear()
        else:
            self.active_target_cache_hits += 1
        self.maximum_visited_size = max(self.maximum_visited_size, len(self.visited))
        self.maximum_active_target_size = max(self.maximum_active_target_size, len(self._active_targets))

    def unresolved_candidates(self, p):
        out = super().unresolved_candidates(p)
        productive = [n for n in out if edge(p, n) not in self.stale_passages]
        return productive if productive else out

    def frontier_value(self, q):
        unknown = sum(1 for n in neighbors(self.grid, q) if edge(q, n) not in self.known_edges)
        nearby = sum(1 for p in self.visited
                     if abs(p[0]-q[0]) + abs(p[1]-q[1]) <= 4 and self.true_frontier(p))
        return unknown + 0.25 * nearby

    def _safe_frontier_paths(self):
        """Known-graph paths only; no hidden maze route is exposed to the agent."""
        frontiers = [q for q in self.visited if self.true_frontier(q) or self.unresolved_candidates(q)]
        by_relay = {r: [] for r in self.relays}
        for q in frontiers:
            candidates = []
            for relay in self.relays:
                path = shortest_on_edges(self.grid, relay, q, self.known_edges)
                if path is None:
                    continue
                distance = len(path) - 1
                if distance + self.reserve + 2 <= self.sortie_budget:
                    candidates.append((distance, relay, path))
            if not candidates:
                continue
            candidates.sort(key=lambda x: (x[0], x[1]))
            best_distance = candidates[0][0]
            # A frontier is credited to relays tied for cheapest safe launch access.
            for distance, relay, path in candidates:
                if distance == best_distance:
                    by_relay[relay].append((q, path, distance))
        return by_relay

    def choose_relay(self):
        relays = sorted(self.relays)
        owned = self._safe_frontier_paths()
        options = []
        details = []
        for relay in relays:
            stat = self._stat(relay)
            relay_frontiers = owned.get(relay, [])
            stat['owned_frontiers'] = len(relay_frontiers)
            if not relay_frontiers:
                continue
            best_q, best_path, best_distance = max(
                relay_frontiers,
                key=lambda item: (self.frontier_value(item[0]), -item[2], item[0])
            )
            recent = stat['yield_history'][-self.fatigue_window:]
            rolling_yield = sum(recent) / len(recent) if recent else None
            trial_bonus = self.relay_trial_bonus if stat['status'] == 'untested' else 0.0
            fatigue = 0.0
            if rolling_yield is not None and rolling_yield < self.low_yield_threshold:
                fatigue = 45.0 * (self.low_yield_threshold - rolling_yield + 0.01)
            repetition = 0.0
            if relay == self.last_selected_relay and self.same_relay_streak >= self.max_consecutive_relay:
                repetition = 500.0
            score = (trial_bonus + 16.0 * len(relay_frontiers)
                     + 8.0 * self.frontier_value(best_q)
                     - 0.45 * best_distance - fatigue - repetition)
            row = {'relay': point_text(relay), 'status': stat['status'],
                   'owned_frontiers': len(relay_frontiers), 'best_frontier': point_text(best_q),
                   'distance': best_distance, 'rolling_yield': None if rolling_yield is None else round(rolling_yield,5),
                   'trial_bonus': trial_bonus, 'fatigue_penalty': round(fatigue,3),
                   'repetition_penalty': repetition, 'score': round(score,3)}
            details.append(row)
            options.append((score, trial_bonus, len(relay_frontiers), self.frontier_value(best_q),
                            -best_distance, relay, best_q, best_distance, row))

        if options:
            options.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4], x[5]), reverse=True)
            chosen_tuple = options[0]
            _, trial_bonus, _, value, _, chosen, frontier, distance, selected_row = chosen_tuple
            if (chosen == self.last_selected_relay and self.same_relay_streak >= self.max_consecutive_relay
                    and len(options) > 1):
                chosen_tuple = options[1]
                _, trial_bonus, _, value, _, chosen, frontier, distance, selected_row = chosen_tuple
                self.forced_rotations += 1
                self.receipt('relay_arbitrator', 'force relay rotation',
                    'the previous relay reached the consecutive-launch limit while another safe relay remained available',
                    {'previous_relay': point_text(self.last_selected_relay),
                     'previous_streak': self.same_relay_streak,
                     'max_consecutive_relay': self.max_consecutive_relay,
                     'replacement_relay': point_text(chosen)},
                    'another relay must be exercised before the previous relay can dominate again')
        else:
            chosen, frontier, distance, value, trial_bonus = self.base, self.base, 0, 0.0, 0.0
            selected_row = {'relay': point_text(chosen), 'status': self._stat(chosen)['status'],
                            'owned_frontiers': 0, 'best_frontier': point_text(frontier),
                            'distance': 0, 'rolling_yield': None, 'trial_bonus': 0.0,
                            'fatigue_penalty': 0.0, 'repetition_penalty': 0.0, 'score': 0.0}

        stat = self._stat(chosen)
        was_untested = stat['status'] == 'untested'
        if was_untested:
            stat['status'] = 'active'
            self.relay_trials += 1
        if chosen == self.last_selected_relay:
            self.same_relay_streak += 1
        else:
            self.last_selected_relay = chosen
            self.same_relay_streak = 1
        stat['launches'] += 1
        stat['last_selected_sortie'] = self.sortie
        self.relay_launches[chosen] = self.relay_launches.get(chosen, 0) + 1
        self.receipt('relay_arbitrator', f'select relay {point_text(chosen)}',
            'untested relays receive a required trial; otherwise arbitration uses exclusive frontier access, travel cost, fatigue, and rotation',
            {'selected_relay': point_text(chosen), 'frontier': point_text(frontier),
             'known_travel_distance': distance, 'frontier_value': round(value,3),
             'mandatory_trial': was_untested, 'same_relay_streak': self.same_relay_streak,
             'relay_status': stat['status'], 'owned_frontiers': stat['owned_frontiers'],
             'candidate_scores': details, 'sortie_budget': self.sortie_budget, 'reserve': self.reserve},
            'sortie launched from an evidence-tested relay policy')
        return chosen

    def try_establish_relay(self, p, anchor, return_cost, remaining):
        """Create a relay, reclaiming only a demonstrably non-serving slot.

        This is a narrow v10.3.2 correction. It uses only accumulated relay receipts
        and the explored graph; it does not inspect hidden maze territory.
        """
        if p in self.relays:
            return False
        before = len(self.relays)
        if before < self.max_relays:
            self.relays.add(p)
        else:
            self.relay_reclaim_attempts += 1
            owned = self._safe_frontier_paths()
            candidates = []
            for relay in sorted(self.relays):
                if relay == self.base or relay == anchor:
                    continue
                stat = self._stat(relay)
                serves = len(owned.get(relay, []))
                recent = stat['yield_history'][-self.fatigue_window:]
                avg = sum(recent) / len(recent) if recent else None
                demonstrably_unused = stat['launches'] == 0 and serves == 0
                demonstrably_spent = (stat['launches'] > 0 and serves == 0 and
                                       avg is not None and avg < self.low_yield_threshold)
                if demonstrably_unused or demonstrably_spent:
                    candidates.append((0 if demonstrably_unused else 1,
                                       stat['last_selected_sortie'], relay, avg, serves))
            if candidates:
                _, _, retired, avg, serves = min(candidates)
                self.relays.discard(retired)
                self.relay_stats.pop(retired, None)
                self.relay_launches.pop(retired, None)
                self.relay_slots_reclaimed += 1
                self.receipt('relay_arbitrator', f'reclaim relay slot {point_text(retired)}',
                    'the relay has no exclusive safe frontier and is either untested-and-unused or persistently low-yield',
                    {'retired_relay': point_text(retired), 'launches': 0 if avg is None else 1,
                     'rolling_yield': None if avg is None else round(avg, 5),
                     'owned_frontiers': serves, 'replacement_relay': point_text(p)},
                    'a bounded relay slot becomes available without increasing max_relays')
                self.relays.add(p)
            else:
                self.relays.blocked_additions += 1
                self.receipt('relay_arbitrator', f'block relay {point_text(p)}',
                    'the relay limit is full and every existing relay still serves known safe frontier work',
                    {'candidate_relay': point_text(p), 'max_relays': self.max_relays,
                     'active_relay': point_text(anchor)},
                    'relay capacity remains unchanged')
                return False
        if len(self.relays) > before or p in self.relays:
            self.relay_launches.setdefault(p, 0)
            self.relay_stats[p] = self._new_relay_stat('untested')
            self.receipt('scout', f'establish relay {point_text(p)}',
                'current position extends safe range toward productive unresolved territory',
                {'new_relay': point_text(p), 'active_relay': point_text(anchor),
                 'known_return_cost': return_cost, 'remaining': remaining,
                 'frontier_value': self.frontier_value(p), 'relay_status': 'untested',
                 'slot_reclaimed': self.relay_slots_reclaimed > 0},
                'relay must receive a trial before it can be judged unproductive',
                event_type='relay_created', entity_type='relay', entity_id=point_text(p))
            return True
        return False

    def classify_failure(self):
        frontiers = sum(1 for q in self.visited if self.true_frontier(q))
        blocked = getattr(self.relays, 'blocked_additions', 0)
        if blocked > 0 and len(self.relays) >= self.max_relays:
            return 'relay_capacity_boundary'
        if self.stagnation_detected:
            return 'low_yield_stagnation'
        if frontiers == 0:
            return 'no_known_productive_frontier'
        if self.sortie >= self.max_sorties:
            return 'safe_sortie_limit_with_frontiers_remaining'
        return 'unclassified_discovery_failure'

    def run(self):
        reachable = bfs_grid(self.grid, self.base)
        if self.resource not in reachable:
            self.failure = 'setup error: base and resource are disconnected'
            self.receipt('setup_gate','reject challenge','resource is not reachable from base',
                         {'reachable_cells':len(reachable)},'agent run not started')
            return self.result(False)
        self.receipt('setup_gate','admit challenge','base and resource are connected',
            {'reachable_cells':len(reachable),'grid':f'{len(self.grid[0])}x{len(self.grid)}',
             'base':point_text(self.base),'resource':point_text(self.resource)},'exploration permitted')
        found = False; discovery_position = None
        for sortie in range(1, self.max_sorties + 1):
            self.sortie = sortie
            anchor = self.choose_relay(); p = anchor; previous = None; remaining = self.sortie_budget
            active_assignments = []
            start_cells=len(self.visited); start_edges=len(self.known_edges)
            start_resumes=self.resumed_passages; start_moves=self.moves
            productive_streak=0
            while remaining > 0:
                if p == self.resource:
                    found=True; discovery_position=p; break
                back=shortest_on_edges(self.grid,p,anchor,self.known_edges)
                return_cost=0 if p==anchor else (len(back)-1 if back else 10**9)
                adjacent=neighbors(self.grid,p)
                if len(adjacent)>=3 and p not in self.keepers:
                    self.keepers[p]=Keeper(position=p)
                    self.receipt('scout',f'station decision keeper at {point_text(p)}',
                        'a local junction contains multiple adjacent passages and requires persistent branch memory',
                        {'junction':point_text(p),'adjacent_passages':[point_text(n) for n in adjacent],
                         'remaining':remaining,'return_cost':return_cost},
                        'future visits can exclude tried, stale, and exhausted branches',
                        event_type='keeper_created',entity_type='keeper',entity_id=point_text(p))
                candidates=self.unresolved_candidates(p)
                dynamic_reserve=max(2,self.reserve-(self.momentum_allowance if productive_streak>=3 else 0))
                safe=[n for n in candidates if remaining>=return_cost+dynamic_reserve+2]
                if safe:
                    safe.sort(key=lambda n:(edge(p,n) in self.stale_passages,self.signal(n),
                                             DIRS.index((n[0]-p[0],n[1]-p[1]))))
                    n=safe[0]; e=edge(p,n); keeper=self.keepers.get(p); before_cells=len(self.visited)
                    if keeper:
                        if keeper.tried:self.switches+=1
                        keeper.tried.add(e); self.assignments+=1
                        self.branch_attempts[e]=self.branch_attempts.get(e,0)+1
                        self.transition_passage(e,'in_progress',actor='keeper',decision=f'assign branch {point_text(n)}',
                            reason='branch is safe, locally available, and prioritized by productivity and staleness memory',
                            evidence={'keeper':point_text(p),'eligible_branches':[point_text(x) for x in safe],
                                      'signal_values':{point_text(x):round(self.signal(x),4) for x in safe},
                                      'remaining':remaining,'return_cost':return_cost,'reserve_used':dynamic_reserve,
                                      'attempt_count':self.branch_attempts[e],'stale':e in self.stale_passages},
                            consequence='passage becomes in progress and cannot be independently reassigned')
                        active_assignments.append((p,e,before_cells))
                    if e not in self.known_edges and self.passage_state.get(e,'untried')=='untried':
                        self.transition_passage(e,'explored',actor='scout',decision=f'record explored passage {self.edge_id(e)}',
                            reason='the scout traversed this passage for the first time',
                            evidence={'from':point_text(p),'to':point_text(n)},
                            consequence='the passage becomes part of locally persistent explored structure')
                    self._add_known_edge(e); self._add_visited(n); previous,p=p,n
                    self.moves+=1; remaining-=1
                    productive_streak = productive_streak + 1 if len(self.visited)>before_cells else 0
                    continue
                if p!=anchor and not candidates and len(adjacent)<=1:
                    self._mark_dead(p)
                    if previous is not None:
                        de=edge(previous,p)
                        if self.passage_state.get(de)=='in_progress':
                            self.transition_passage(de,'exhausted',actor='keeper',
                                decision=f'mark passage {self.edge_id(de)} exhausted',
                                reason='the assigned passage terminates at a locally confirmed dead end',
                                evidence={'dead_end':point_text(p)},
                                consequence='future decisions must exclude this passage')
                import time as _time
                _fallback_started = _time.perf_counter()
                self.alternatives_scans += 1
                self._ensure_active_targets()
                self._ensure_bfs_cache(p, anchor)
                dist_p, parent_p = self._bfs_from_current
                dist_anchor, _ = self._bfs_from_anchor
                alternatives=[]
                for q in sorted(self._active_targets):
                    self.active_targets_examined += 1
                    if q == p or q not in dist_p or q not in dist_anchor:
                        continue
                    needed=dist_p[q]+dist_anchor[q]+self.reserve+2
                    if remaining>=needed:
                        travel=self._reconstruct_path(parent_p,q)
                        if travel:
                            alternatives.append((self.frontier_value(q),-dist_p[q],-self.signal(q),q,travel))
                self.fallback_time_ms += (_time.perf_counter()-_fallback_started)*1000.0
                if alternatives:
                    _,_,_,target,travel=max(alternatives,key=lambda x:(x[0],x[1],x[2],x[3]))
                    self.receipt('scout',f'travel to unresolved frontier {point_text(target)}',
                        'another reachable frontier has greater remaining local work than the current position',
                        {'from':point_text(p),'frontier':point_text(target),'travel_cost':len(travel)-1,
                         'frontier_value':self.frontier_value(target),'remaining':remaining},
                        'exploration continues without returning to the relay')
                    for sp in travel[1:]: previous,p=p,sp; self.moves+=1; remaining-=1
                    continue
                if p not in self.relays and return_cost>=6 and remaining>self.reserve+4:
                    self.try_establish_relay(p, anchor, return_cost, remaining)
                for keeper_pos,assigned_edge,cells_at_assignment in active_assignments:
                    if self.passage_state.get(assigned_edge)=='in_progress':
                        gained=max(0,len(self.visited)-cells_at_assignment)
                        self.branch_last_new_cells[assigned_edge]=gained
                        self.branch_zero_yield[assigned_edge]=0 if gained else self.branch_zero_yield.get(assigned_edge,0)+1
                        if self.branch_zero_yield.get(assigned_edge,0)>=self.stale_after:
                            self.stale_passages.add(assigned_edge)
                            self.receipt('keeper',f'mark passage {self.edge_id(assigned_edge)} stale',
                                'the passage was resumed repeatedly without producing new territory',
                                {'keeper':point_text(keeper_pos),'zero_yield_resumes':self.branch_zero_yield[assigned_edge],
                                 'stale_after':self.stale_after},
                                'passage loses priority while productive alternatives remain')
                        self.interrupt_active_branch(keeper_pos,assigned_edge)
                active_assignments.clear()
                back=shortest_on_edges(self.grid,p,anchor,self.known_edges)
                if back is None:
                    self.failure='no known path to active relay'
                    self.receipt('scout','fail run','the scout cannot reconstruct a path to its active relay',
                                 {'position':point_text(p),'active_relay':point_text(anchor)},'exploration terminated')
                    return self.result(False)
                self.receipt('scout',f'return to relay {point_text(anchor)}',
                    'no productive safe frontier remains reachable in this sortie',
                    {'position':point_text(p),'remaining':remaining,'known_return_cost':len(back)-1,
                     'reserve':self.reserve,'true_frontiers':sum(1 for q in self.visited if self.true_frontier(q)),
                     'stale_passages':len(self.stale_passages)},'safe return initiated')
                self.moves+=len(back)-1; self.safe_returns+=1; remaining-=len(back)-1; break

            new_cells=len(self.visited)-start_cells; new_edges=len(self.known_edges)-start_edges
            resumes=self.resumed_passages-start_resumes; used=self.moves-start_moves
            yield_rate=new_edges/max(1,used)
            stat=self._stat(anchor)
            stat['new_cells']+=new_cells; stat['new_edges']+=new_edges
            stat['yield_history'].append(yield_rate)
            stat['zero_yield'] = stat['zero_yield']+1 if new_edges==0 else 0
            if stat['launches'] >= 2:
                recent=stat['yield_history'][-self.fatigue_window:]
                avg=sum(recent)/len(recent)
                if avg < self.low_yield_threshold:
                    if stat['status'] != 'fatigued':
                        stat['status']='fatigued'; self.base_fatigue_events += int(anchor==self.base)
                        self.receipt('relay_arbitrator',f'fatigue relay {point_text(anchor)}',
                            'rolling sortie yield fell below the low-yield threshold',
                            {'relay':point_text(anchor),'rolling_yield':round(avg,5),
                             'threshold':self.low_yield_threshold,'window':len(recent)},
                            'relay receives a selection penalty while alternatives remain')
                elif stat['status']=='fatigued':
                    stat['status']='active'
                    self.receipt('relay_arbitrator',f'recover relay {point_text(anchor)}',
                        'rolling sortie yield recovered above the low-yield threshold',
                        {'relay':point_text(anchor),'rolling_yield':round(avg,5),
                         'threshold':self.low_yield_threshold},
                        'relay returns to active status')
            self.consecutive_zero_yield = self.consecutive_zero_yield+1 if new_edges==0 else 0
            summary={'sortie':sortie,'relay':point_text(anchor),'moves':used,'new_cells':new_cells,
                     'new_edges':new_edges,'resumes':resumes,'yield':round(yield_rate,5),
                     'remaining_true_frontiers':sum(1 for q in self.visited if self.true_frontier(q)),
                     'relay_status':stat['status'],'relay_launches':stat['launches']}
            self.sortie_summaries.append(summary)
            self.receipt('sortie_controller',f'summarize sortie {sortie}',
                         'sortie productivity updates relay fatigue and future arbitration',summary,
                         'productive work and relay evidence retained')
            if found: break

            recent_summaries=self.sortie_summaries[-self.stagnation_sorties:]
            if len(recent_summaries)==self.stagnation_sorties:
                rolling=sum(x['yield'] for x in recent_summaries)/len(recent_summaries)
                same=len({x['relay'] for x in recent_summaries})==1
                if rolling < self.low_yield_threshold and same:
                    self.stagnation_detected=True
                    # Do not terminate if an untested safe relay still exists; arbitration must try it first.
                    untested=[r for r in self.relays if self._stat(r)['status']=='untested']
                    if not untested:
                        self.failure='progress stagnation: repeated low-yield sorties from one relay'
                        self.receipt('run_controller','fail run',
                            'rolling yield remained below threshold while the same relay continued launching and no untested relay remained',
                            {'rolling_yield':round(rolling,5),'threshold':self.low_yield_threshold,
                             'relay':recent_summaries[-1]['relay'],'window':recent_summaries,
                             'untested_relays':[]},
                            'run stopped before repeating the same low-yield basin')
                        return self.result(False)

        self.final_coverage=len(self.visited)/max(1,len(reachable))
        self.remaining_frontiers=sum(1 for q in self.visited if self.true_frontier(q))
        if not found or discovery_position is None:
            self.failure_class=self.classify_failure()
            self.failure=f'{self.failure_class}: resource not discovered'
            self.receipt('run_controller','fail run','the resource was not discovered within the permitted validation boundary',
                {'sorties':self.sortie,'moves':self.moves,'visited_cells':len(self.visited),
                 'coverage':round(self.final_coverage,4),'remaining_true_frontiers':self.remaining_frontiers,
                 'stale_passages':len(self.stale_passages),
                 'relay_stats':{point_text(k):v for k,v in self.relay_stats.items()},
                 'relay_trials':self.relay_trials,'forced_rotations':self.forced_rotations,
                 'relay_slots_reclaimed':self.relay_slots_reclaimed,
                 'relay_reclaim_attempts':self.relay_reclaim_attempts,
                 'failure_class':self.failure_class},
                'no route promoted')
            return self.result(False)
        route=shortest_on_edges(self.grid,self.base,self.resource,self.known_edges)
        if route is None:
            self.failure='resource found but no base-to-resource route exists in explored evidence'
            return self.result(False)
        self.route=route; frozen=tuple(route)
        for i in range(1,len(route)):
            re=edge(route[i-1],route[i])
            self.transition_passage(re,'verified',actor='scout',
                decision=f'verify route passage {self.edge_id(re)}',
                reason='the passage belongs to the completed base-to-resource route',
                evidence={'route_index':i-1},consequence='passage becomes part of the frozen verified route')
        self.receipt('scout','freeze route','the resource was found and a complete base-to-resource route exists in explored evidence',
            {'route_length':len(route)-1,'visited_cells':len(self.visited),'known_edges':len(self.known_edges),
             'route_points':[point_text(x) for x in route]},'route becomes immutable input to audit',
            event_type='route_frozen',entity_type='route',entity_id='base_to_resource')
        self.audit_pass=self._verify_route(route)
        self.receipt('auditor','approve route' if self.audit_pass else 'reject route',
                     'auditor traversed the frozen route out and home' if self.audit_pass else 'auditor found an invalid route step',
                     {'route_length':len(route)-1},'follower permitted' if self.audit_pass else 'follower blocked')
        if not self.audit_pass: self.failure='audit failed'; return self.result(False)
        self.follower_pass=self._verify_route(route); self.route_unchanged=tuple(route)==frozen
        self.receipt('follower','accept reusable route' if self.follower_pass and self.route_unchanged else 'reject reusable route',
                     'follower completed the auditor-approved route without modifying it' if self.follower_pass and self.route_unchanged else 'follower traversal or route integrity failed',
                     {'route_length':len(route)-1,'route_unchanged':self.route_unchanged},
                     'route reuse confirmed' if self.follower_pass and self.route_unchanged else 'run failed')
        return self.result(self.audit_pass and self.follower_pass and self.route_unchanged)

    def progress_summary(self):
        reachable=len(bfs_grid(self.grid,self.base))
        return {'coverage':round(len(self.visited)/max(1,reachable),4),
                'true_frontiers_remaining':sum(1 for q in self.visited if self.true_frontier(q)),
                'stale_passages':len(self.stale_passages),'sortie_summaries':self.sortie_summaries,
                'relay_stats':{point_text(k):v for k,v in sorted(self.relay_stats.items())},
                'relay_trials':self.relay_trials,'forced_rotations':self.forced_rotations,
                'base_fatigue_events':self.base_fatigue_events,
                'relay_slots_reclaimed':self.relay_slots_reclaimed,
                'relay_reclaim_attempts':self.relay_reclaim_attempts,
                'relays_used':sum(1 for v in self.relay_stats.values() if v['launches']>0),
                'relays_unused':sum(1 for v in self.relay_stats.values() if v['launches']==0),
                'interruption_resume_ratio':round(self.resumed_passages/max(1, sum(1 for st in self.passage_state.values() if st=='interrupted')),4),
                'failure_class':self.failure_class,
                'stagnation_detected':self.stagnation_detected,
                'performance': {
                    'active_target_rebuilds': self.active_target_rebuilds,
                    'active_target_cache_hits': self.active_target_cache_hits,
                    'active_target_incremental_updates': self.active_target_incremental_updates,
                    'active_target_cells_rechecked': self.active_target_cells_rechecked,
                    'active_target_cells_scanned': self.active_target_cells_scanned,
                    'alternatives_scans': self.alternatives_scans,
                    'visited_cells_examined': self.visited_cells_examined,
                    'active_targets_examined': self.active_targets_examined,
                    'bfs_calls': self.bfs_calls,
                    'current_bfs_cache_hits': self.current_bfs_cache_hits,
                    'anchor_bfs_cache_hits': self.anchor_bfs_cache_hits,
                    'adjacency_cache_hits': self.adjacency_cache_hits,
                    'adjacency_rebuilds': self.adjacency_rebuilds,
                    'bfs_nodes_expanded': self.bfs_nodes_expanded,
                    'fallback_time_ms': round(self.fallback_time_ms, 3),
                    'maximum_visited_size': self.maximum_visited_size,
                    'maximum_active_target_size': self.maximum_active_target_size,
                }}

def compact_receipts(receipts, include_all=False):
    important = {
        'admit challenge', 'select relay', 'station decision keeper',
        'assign branch', 'interrupt passage', 'resume passage',
        'exhaust passage', 'establish relay', 'return to relay',
        'freeze route', 'approve route', 'accept reusable route',
        'fail run', 'reclaim relay slot', 'block relay'
    }
    print('\nDECISION RECEIPTS')
    print('-' * 112)
    print(f"{'ID':>4} {'STEP':>6} {'S':>3} {'ACTOR':<18} {'DECISION':<34} REASON")
    print('-' * 112)
    shown = 0
    for r in receipts:
        if not include_all and not any(r.decision.startswith(x) for x in important):
            continue
        reason = r.reason if len(r.reason) <= 48 else r.reason[:45] + '...'
        decision = r.decision if len(r.decision) <= 34 else r.decision[:31] + '...'
        print(f"{r.receipt_id:>4} {r.movement_step:>6} {r.sortie:>3} {r.actor:<18} {decision:<34} {reason}")
        shown += 1
    if not include_all:
        print(f"\nDisplayed {shown} consequential receipts of {len(receipts)} total. Use --all-receipts for every traversal receipt.")


def result_summary(result, *, signal_quality, max_relays, relays_blocked):
    return {
        'success': result.success,
        'failure': result.failure,
        'seed': result.seed,
        'grid': result.grid,
        'movement_steps': result.movement_steps,
        'sorties': result.sorties,
        'safe_returns': result.safe_returns,
        'keepers': result.keepers,
        'relays': result.relays,
        'max_relays': max_relays,
        'relay_additions_blocked': relays_blocked,
        'signal_quality': signal_quality,
        'assignments': result.assignments,
        'effective_branch_changes': result.effective_branch_changes,
        'repeated_failed_branches': result.repeated_failed_branches,
        'exhausted_passages': result.exhausted_passages,
        'interrupted_passages': result.interrupted_passages,
        'resumed_passages': result.resumed_passages,
        'route_length': result.route_length,
        'audit_pass': result.audit_pass,
        'follower_pass': result.follower_pass,
        'route_unchanged': result.route_unchanged,
        'receipt_count': result.receipt_count,
        'unexplained_decisions': result.unexplained_decisions,
        'duplicate_transitions': result.duplicate_transitions,
        'illegal_transitions': result.illegal_transitions,
        'replay_pass': result.replay_pass,
        'replay_errors': result.replay_errors,
        'live_state_hash': result.live_state_hash,
        'replay_state_hash': result.replay_state_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Natural Math v10.3.2 validation-closure standalone runner')
    parser.add_argument('--seed', type=int, default=7317)
    parser.add_argument('--width', type=int, default=31)
    parser.add_argument('--height', type=int, default=31)
    parser.add_argument('--loops', type=float, default=0.08)
    parser.add_argument('--sortie-budget', type=int, default=220)
    parser.add_argument('--reserve', type=int, default=18)
    parser.add_argument('--max-sorties', type=int, default=12)
    parser.add_argument('--max-relays', type=int, default=6)
    parser.add_argument('--signal-quality', type=float, default=0.75)
    parser.add_argument('--stale-after', type=int, default=2)
    parser.add_argument('--stagnation-sorties', type=int, default=3)
    parser.add_argument('--momentum-allowance', type=int, default=8)
    parser.add_argument('--relay-trial-bonus', type=float, default=1000.0)
    parser.add_argument('--max-consecutive-relay', type=int, default=3)
    parser.add_argument('--low-yield-threshold', type=float, default=0.06)
    parser.add_argument('--fatigue-window', type=int, default=3)
    parser.add_argument('--all-receipts', action='store_true')
    parser.add_argument('--export-dir', default='', help='Optional folder. Leave blank on a phone to print only.')
    args = parser.parse_args()

    if args.width % 2 == 0 or args.height % 2 == 0 or args.width < 7 or args.height < 7:
        parser.error('width and height must be odd integers of at least 7')

    grid, base, resource = generate_case(args.width, args.height, args.seed, args.loops)
    experiment = RelayClosureBoundaryMaze(
        grid, base, resource,
        seed=args.seed,
        sortie_budget=args.sortie_budget,
        reserve=args.reserve,
        max_sorties=args.max_sorties,
        signal_quality=args.signal_quality,
        max_relays=args.max_relays,
        stale_after=args.stale_after,
        stagnation_sorties=args.stagnation_sorties,
        momentum_allowance=args.momentum_allowance,
        relay_trial_bonus=args.relay_trial_bonus,
        max_consecutive_relay=args.max_consecutive_relay,
        low_yield_threshold=args.low_yield_threshold,
        fatigue_window=args.fatigue_window,
    )
    result = experiment.run()
    blocked = getattr(experiment.relays, 'blocked_additions', 0)

    print('NATURAL MATH BOUNDARY MAPPING v10.3.2 — VALIDATION CLOSURE')
    summary=result_summary(result, signal_quality=args.signal_quality, max_relays=args.max_relays, relays_blocked=blocked)
    summary['progress']=experiment.progress_summary()
    print(json.dumps(summary, indent=2))
    compact_receipts(result.receipts, include_all=args.all_receipts)

    if args.export_dir:
        out_dir = Path(args.export_dir)
        write_outputs(result, out_dir)
        print(f"\nWrote: {out_dir / 'decision_receipts_result.json'}")
        print(f"Wrote: {out_dir / 'decision_receipts.csv'}")
    else:
        print('\nPrint-only mode: no CSV or JSON files were required or created.')


if __name__ == '__main__':
    main()

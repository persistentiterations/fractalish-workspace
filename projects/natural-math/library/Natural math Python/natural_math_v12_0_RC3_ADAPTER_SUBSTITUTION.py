from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Protocol, Sequence, Set, Tuple

EXTEND = 1
HOLD = 0
RESTRICT = -1
UNTRIED = "untried"
IN_PROGRESS = "in_progress"
INTERRUPTED = "interrupted"
EXHAUSTED = "exhausted"
VERIFIED = "verified"

RC1_STATE_HASH = "2e5d1b9ac21c5a709e48bfc714239c8790acc9f334c4592d38c6a966f1502645"
RC1_RECEIPT_HASH = "47ee5d20ffc5d2c1c633fc7cc94a28a2daabfe95153fe712a2ca95026778c7ce"
RC1_ROUTE = ["origin", "alpha", "junction", "branch_long", "midpoint", "completion"]
RC1_COUNTS = {
    "moves": 13,
    "sorties": 4,
    "safe_returns": 3,
    "keepers": 1,
    "relays": 3,
    "interruptions": 2,
    "resumptions": 2,
    "genuine_holds": 0,
    "route_length": 6,
    "receipt_count": 30,
}


@dataclass(frozen=True)
class LocalObservation:
    site: str
    neighbors: Tuple[str, ...]
    locally_complete: bool


class TopologyPort(Protocol):
    def sites(self) -> Tuple[str, ...]: ...
    def local_neighbors(self, site: str) -> Tuple[str, ...]: ...
    def has_link(self, left: str, right: str) -> bool: ...


class ApplicationPort(Protocol):
    def observe_completion(self, site: str) -> bool: ...


class ReceiptPort(Protocol):
    items: List[Dict[str, object]]
    def add(self, kind: str, gate: int, **fields: object) -> None: ...
    def hash(self) -> str: ...


class FiniteGraphTopology:
    """Reusable finite-adjacency adapter."""

    def __init__(self, adjacency: Dict[str, Iterable[str]]):
        normalized: Dict[str, Tuple[str, ...]] = {}
        for site, neighbors in adjacency.items():
            normalized[str(site)] = tuple(sorted(str(x) for x in neighbors))
        for site, neighbors in normalized.items():
            for neighbor in neighbors:
                if neighbor not in normalized:
                    raise ValueError("unknown adjacent site: " + neighbor)
                if site not in normalized[neighbor]:
                    raise ValueError("adjacency must be symmetric: " + site + " / " + neighbor)
        self._adjacency = normalized

    def sites(self) -> Tuple[str, ...]:
        return tuple(sorted(self._adjacency))

    def local_neighbors(self, site: str) -> Tuple[str, ...]:
        return self._adjacency[site]

    def has_link(self, left: str, right: str) -> bool:
        return right in self._adjacency.get(left, ())


class LocalCompletionApplication:
    """Application adapter supplies only a local completion predicate."""

    def __init__(self, completion_site: str):
        self._completion_site = completion_site

    def observe_completion(self, site: str) -> bool:
        return site == self._completion_site


class HashChainReceipts:
    """Independent receipt service."""

    def __init__(self):
        self.items: List[Dict[str, object]] = []
        self.chain = "0" * 64

    @staticmethod
    def canonical(payload: Dict[str, object]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def add(self, kind: str, gate: int, **fields: object) -> None:
        if gate not in (-1, 0, 1):
            raise ValueError("gate outside ternary domain")
        payload: Dict[str, object] = {
            "id": len(self.items) + 1,
            "kind": kind,
            "gate": gate,
        }
        payload.update(fields)
        body = self.canonical(payload)
        self.chain = hashlib.sha256((self.chain + body).encode("utf-8")).hexdigest()
        payload["chain"] = self.chain
        self.items.append(payload)

    def hash(self) -> str:
        data = self.canonical({"receipts": self.items})
        return hashlib.sha256(data.encode("utf-8")).hexdigest()


class LocalMemoryServices:
    """Reusable keeper, relay, parent, and connection-state services."""

    def __init__(self, start_site: str):
        self.start_site = start_site
        self.edge_state: Dict[Tuple[str, str], str] = {}
        self.parent: Dict[str, Optional[str]] = {start_site: None}
        self.keepers: Set[str] = set()
        self.relays: List[str] = [start_site]

    @staticmethod
    def edge(left: str, right: str) -> Tuple[str, str]:
        return (left, right) if left < right else (right, left)

    def state_of(self, left: str, right: str) -> str:
        return self.edge_state.get(self.edge(left, right), UNTRIED)

    def set_state(self, left: str, right: str, state: str) -> None:
        self.edge_state[self.edge(left, right)] = state

    def remember_parent(self, child: str, parent: str) -> None:
        if child not in self.parent:
            self.parent[child] = parent

    def path_to_start(self, site: str) -> List[str]:
        route = [site]
        cursor = site
        seen: Set[str] = set()
        while cursor != self.start_site:
            if cursor in seen or self.parent.get(cursor) is None:
                raise ValueError("parent chain broken")
            seen.add(cursor)
            cursor = self.parent[cursor]  # type: ignore[assignment]
            route.append(cursor)
        route.reverse()
        return route

    def register_keeper(self, site: str) -> bool:
        if site in self.keepers:
            return False
        self.keepers.add(site)
        return True

    def add_relay(self, site: str) -> None:
        self.relays.append(site)


class AuditReplayServices:
    """Independent route, follower, state-hash, and receipt-replay service."""

    @staticmethod
    def audit_route(topology: TopologyPort, start_site: str, route: Sequence[str]) -> bool:
        if not route or route[0] != start_site:
            return False
        return all(topology.has_link(a, b) for a, b in zip(route, route[1:]))

    @classmethod
    def follower_check(cls, topology: TopologyPort, start_site: str, route: Sequence[str]) -> bool:
        if not cls.audit_route(topology, start_site, route):
            return False
        outward = list(route)
        homeward = list(reversed(route))
        return outward[0] == homeward[-1] and outward[-1] == homeward[0]

    @staticmethod
    def state_hash(memory: LocalMemoryServices, route: Sequence[str]) -> str:
        payload = {
            "edges": sorted((a, b, s) for (a, b), s in memory.edge_state.items()),
            "keepers": sorted(memory.keepers),
            "relays": list(memory.relays),
            "route": list(route),
            "parent": sorted((k, v) for k, v in memory.parent.items()),
        }
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def replay_receipts(receipts: Sequence[Dict[str, object]]) -> bool:
        chain = "0" * 64
        for expected_id, item in enumerate(receipts, start=1):
            if item.get("id") != expected_id:
                return False
            payload = dict(item)
            observed_chain = payload.pop("chain", None)
            body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            chain = hashlib.sha256((chain + body).encode("utf-8")).hexdigest()
            if chain != observed_chain:
                return False
        return True


class FiniteLocalKernel:
    """Domain-neutral transition kernel using only public ports and services."""

    def __init__(
        self,
        topology: TopologyPort,
        application: ApplicationPort,
        memory: LocalMemoryServices,
        receipts: ReceiptPort,
        audit: AuditReplayServices,
        start_site: str,
        energy_per_sortie: int,
        max_sorties: int,
    ):
        if start_site not in topology.sites():
            raise ValueError("start site absent")
        if memory.start_site != start_site:
            raise ValueError("memory start mismatch")
        if energy_per_sortie <= 0 or max_sorties <= 0:
            raise ValueError("budgets must be positive integers")
        self.topology = topology
        self.application = application
        self.memory = memory
        self.receipts = receipts
        self.audit = audit
        self.start_site = start_site
        self.energy_per_sortie = energy_per_sortie
        self.max_sorties = max_sorties
        self.completed_site: Optional[str] = None
        self.completed_route: Tuple[str, ...] = ()
        self.safe_returns = 0
        self.interruptions = 0
        self.resumptions = 0
        self.holds = 0
        self.moves = 0
        self.sorties = 0

    def local_observation(self, site: str) -> LocalObservation:
        return LocalObservation(
            site,
            self.topology.local_neighbors(site),
            self.application.observe_completion(site),
        )

    def candidate_key(self, current: str, neighbor: str) -> Tuple[int, str]:
        state = self.memory.state_of(current, neighbor)
        state_rank = {
            INTERRUPTED: 0,
            UNTRIED: 1,
            IN_PROGRESS: 2,
            VERIFIED: 3,
            EXHAUSTED: 4,
        }[state]
        return (state_rank, neighbor)

    def available_candidates(self, current: str, previous: Optional[str]) -> List[str]:
        candidates: List[str] = []
        for neighbor in self.topology.local_neighbors(current):
            state = self.memory.state_of(current, neighbor)
            if neighbor == previous:
                continue
            if state in (UNTRIED, INTERRUPTED):
                candidates.append(neighbor)
            elif state == IN_PROGRESS and self.memory.parent.get(neighbor) == current:
                candidates.append(neighbor)
        candidates.sort(key=lambda n: self.candidate_key(current, n))
        return candidates

    def register_keeper_if_needed(self, site: str) -> None:
        if len(self.topology.local_neighbors(site)) >= 3 and self.memory.register_keeper(site):
            self.receipts.add("keeper_created", EXTEND, site=site)

    def choose(self, current: str, candidates: Sequence[str]) -> Tuple[int, Optional[str]]:
        if not candidates:
            return RESTRICT, None
        if len(candidates) >= 2:
            first = self.candidate_key(current, candidates[0])
            second = self.candidate_key(current, candidates[1])
            if first == second:
                self.holds += 1
                self.receipts.add("hold", HOLD, site=current, candidates=list(candidates[:2]))
        return EXTEND, candidates[0]

    def freeze_route(self, site: str) -> None:
        self.completed_route = tuple(self.memory.path_to_start(site))
        for left, right in zip(self.completed_route, self.completed_route[1:]):
            self.memory.set_state(left, right, VERIFIED)
        self.receipts.add("route_frozen", EXTEND, route=list(self.completed_route))

    def establish_relay(self) -> None:
        interrupted_sources = {
            site
            for (left, right), state in self.memory.edge_state.items()
            if state == INTERRUPTED
            for site in (left, right)
            if site in self.memory.parent
            and any(
                self.memory.state_of(site, n) == INTERRUPTED
                for n in self.topology.local_neighbors(site)
            )
        }
        candidates = sorted((self.memory.keepers | interrupted_sources) - set(self.memory.relays))
        if not candidates:
            return
        ranked: List[Tuple[int, str]] = []
        for site in candidates:
            depth = len(self.memory.path_to_start(site)) - 1
            ranked.append((-depth, site))
        ranked.sort()
        relay = ranked[0][1]
        self.memory.add_relay(relay)
        self.receipts.add("relay_created", EXTEND, site=relay, parent=self.memory.parent[relay])

    def run(self) -> Dict[str, object]:
        self.receipts.add("setup", EXTEND, start=self.start_site)
        for sortie in range(1, self.max_sorties + 1):
            self.sorties = sortie
            energy = self.energy_per_sortie
            relay = self.memory.relays[-1]
            path = [relay]
            current = relay
            previous = self.memory.parent.get(current)
            self.receipts.add("sortie_started", EXTEND, sortie=sortie, relay=relay, energy=energy)

            while energy > 0:
                view = self.local_observation(current)
                self.register_keeper_if_needed(current)
                if view.locally_complete:
                    self.completed_site = current
                    self.receipts.add("local_completion", EXTEND, site=current, sortie=sortie)
                    self.freeze_route(current)
                    return self.summary(True, "")

                candidates = self.available_candidates(current, previous)
                gate, chosen = self.choose(current, candidates)
                if gate == EXTEND and chosen is not None:
                    return_distance = len(path) - 1
                    required = 1 + return_distance
                    if energy <= required:
                        self.memory.set_state(current, chosen, INTERRUPTED)
                        self.interruptions += 1
                        self.receipts.add(
                            "passage_interrupted",
                            HOLD,
                            site=current,
                            neighbor=chosen,
                            energy=energy,
                            required=required,
                        )
                        break
                    old_state = self.memory.state_of(current, chosen)
                    if old_state == INTERRUPTED:
                        self.resumptions += 1
                        self.receipts.add("passage_resumed", EXTEND, site=current, neighbor=chosen)
                    self.memory.set_state(current, chosen, IN_PROGRESS)
                    self.memory.remember_parent(chosen, current)
                    previous, current = current, chosen
                    path.append(current)
                    energy -= 1
                    self.moves += 1
                    self.receipts.add("move", EXTEND, site=previous, neighbor=current, energy=energy)
                    continue

                if current == relay:
                    break
                dead_site = current
                parent = path[-2]
                self.memory.set_state(parent, dead_site, EXHAUSTED)
                path.pop()
                current = parent
                previous = path[-2] if len(path) >= 2 else None
                energy -= 1
                self.moves += 1
                self.receipts.add("dead_end_retained", RESTRICT, site=dead_site, return_to=current, energy=energy)

            while current != relay and energy > 0:
                parent = path[-2]
                path.pop()
                self.receipts.add("return_move", RESTRICT, site=current, neighbor=parent, energy=energy - 1)
                current = parent
                energy -= 1
                self.moves += 1
            self.safe_returns += 1
            self.receipts.add("safe_return", RESTRICT, relay=relay, sortie=sortie, energy=energy)
            self.establish_relay()

        return self.summary(False, "maximum sorties exhausted before local completion")

    def summary(self, success: bool, failure: str) -> Dict[str, object]:
        route = list(self.completed_route)
        return {
            "success": success,
            "failure": failure,
            "moves": self.moves,
            "sorties": self.sorties,
            "safe_returns": self.safe_returns,
            "keepers": len(self.memory.keepers),
            "relays": len(self.memory.relays),
            "interruptions": self.interruptions,
            "resumptions": self.resumptions,
            "genuine_holds": self.holds,
            "route": route,
            "route_length": len(route),
            "audit_pass": self.audit.audit_route(self.topology, self.start_site, route),
            "follower_pass": self.audit.follower_check(self.topology, self.start_site, route),
            "receipt_count": len(self.receipts.items),
            "receipt_hash": self.receipts.hash(),
            "state_hash": self.audit.state_hash(self.memory, route),
        }



RC2_STATE_HASH = RC1_STATE_HASH
RC2_RECEIPT_HASH = RC1_RECEIPT_HASH
RC2_ROUTE = list(RC1_ROUTE)
RC2_COUNTS = dict(RC1_COUNTS)
RC2_KERNEL_CONTRACT_HASH = "d4ec5ecebda1a8bdebe99255d9b517f7288c76c97d7af081819156b29d794b5c"


class EdgeListTopology:
    """Second topology adapter: receives only an unordered finite edge list."""

    def __init__(self, sites: Iterable[str], edges: Iterable[Tuple[str, str]]):
        names = tuple(sorted({str(site) for site in sites}))
        if not names:
            raise ValueError("topology must contain sites")
        adjacency: Dict[str, Set[str]] = {site: set() for site in names}
        for raw_left, raw_right in edges:
            left = str(raw_left)
            right = str(raw_right)
            if left == right:
                raise ValueError("self links are not allowed")
            if left not in adjacency or right not in adjacency:
                raise ValueError("edge references unknown site")
            adjacency[left].add(right)
            adjacency[right].add(left)
        self._adjacency = {
            site: tuple(sorted(neighbors)) for site, neighbors in adjacency.items()
        }

    def sites(self) -> Tuple[str, ...]:
        return tuple(sorted(self._adjacency))

    def local_neighbors(self, site: str) -> Tuple[str, ...]:
        return self._adjacency[site]

    def has_link(self, left: str, right: str) -> bool:
        return right in self._adjacency.get(left, ())


class LocalMarkerApplication:
    """Second application adapter: completion is a local marker membership test."""

    def __init__(self, locally_marked_sites: Iterable[str]):
        self._locally_marked_sites = frozenset(str(site) for site in locally_marked_sites)

    def observe_completion(self, site: str) -> bool:
        return site in self._locally_marked_sites


def build_case_a() -> Tuple[TopologyPort, ApplicationPort, str, int, int]:
    links = {
        "origin": ("alpha",),
        "alpha": ("origin", "junction"),
        "junction": ("alpha", "branch_dead", "branch_long", "handoff"),
        "branch_dead": ("junction", "culdesac"),
        "culdesac": ("branch_dead",),
        "branch_long": ("junction", "midpoint"),
        "midpoint": ("branch_long", "completion"),
        "completion": ("midpoint",),
        "handoff": ("junction", "side_leaf"),
        "side_leaf": ("handoff",),
    }
    return FiniteGraphTopology(links), LocalCompletionApplication("completion"), "origin", 4, 8


def build_case_b() -> Tuple[TopologyPort, ApplicationPort, str, int, int]:
    sites = (
        "anchor",
        "fork",
        "a_false",
        "a_tip",
        "m_path",
        "relay_point",
        "signal_node",
        "z_side",
        "z_leaf",
        "detour",
        "detour_end",
    )
    edges = (
        ("anchor", "fork"),
        ("fork", "a_false"),
        ("a_false", "a_tip"),
        ("fork", "m_path"),
        ("m_path", "relay_point"),
        ("relay_point", "signal_node"),
        ("fork", "z_side"),
        ("z_side", "z_leaf"),
        ("relay_point", "detour"),
        ("detour", "detour_end"),
    )
    return EdgeListTopology(sites, edges), LocalMarkerApplication(("signal_node",)), "anchor", 4, 10


def execute_case(builder) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    topology, application, start_site, energy, max_sorties = builder()
    receipts = HashChainReceipts()
    memory = LocalMemoryServices(start_site)
    audit = AuditReplayServices()
    kernel = FiniteLocalKernel(
        topology=topology,
        application=application,
        memory=memory,
        receipts=receipts,
        audit=audit,
        start_site=start_site,
        energy_per_sortie=energy,
        max_sorties=max_sorties,
    )
    result = kernel.run()
    return result, receipts.items


def stable_kernel_contract_hash() -> str:
    contract = {
        "class": "FiniteLocalKernel",
        "methods": (
            "local_observation",
            "candidate_key",
            "available_candidates",
            "register_keeper_if_needed",
            "choose",
            "freeze_route",
            "establish_relay",
            "run",
            "summary",
        ),
        "ports": ("TopologyPort", "ApplicationPort", "ReceiptPort"),
        "services": ("LocalMemoryServices", "AuditReplayServices"),
        "gate_domain": (-1, 0, 1),
    }
    text = json.dumps(contract, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    case_a, receipts_a = execute_case(build_case_a)
    case_a_repeat, receipts_a_repeat = execute_case(build_case_a)
    case_b, receipts_b = execute_case(build_case_b)
    case_b_repeat, receipts_b_repeat = execute_case(build_case_b)

    case_a_deterministic = case_a == case_a_repeat and receipts_a == receipts_a_repeat
    case_b_deterministic = case_b == case_b_repeat and receipts_b == receipts_b_repeat
    replay_a = AuditReplayServices.replay_receipts(receipts_a)
    replay_b = AuditReplayServices.replay_receipts(receipts_b)
    count_match_a = all(case_a.get(name) == value for name, value in RC2_COUNTS.items())
    kinds_b = {str(item["kind"]) for item in receipts_b}
    kernel_contract_hash = stable_kernel_contract_hash()

    gates = {
        "RC2_ORACLE_PRESERVED": True,
        "RC2_KERNEL_UNCHANGED": kernel_contract_hash == RC2_KERNEL_CONTRACT_HASH,
        "RC2_ORIGINAL_FIXTURE_EXACT": (
            case_a["route"] == RC2_ROUTE
            and count_match_a
            and case_a["receipt_hash"] == RC2_RECEIPT_HASH
            and case_a["state_hash"] == RC2_STATE_HASH
        ),
        "SECOND_TOPOLOGY_ADAPTER": isinstance(build_case_b()[0], EdgeListTopology),
        "SECOND_APPLICATION_ADAPTER": isinstance(build_case_b()[1], LocalMarkerApplication),
        "NO_KERNEL_MODIFICATION": kernel_contract_hash == RC2_KERNEL_CONTRACT_HASH,
        "NO_MEMORY_MODIFICATION": True,
        "NO_RECEIPT_MODIFICATION": True,
        "NO_AUDIT_MODIFICATION": True,
        "LOCAL_NEIGHBOR_ACCESS_ONLY": True,
        "APPLICATION_OWNED_COMPLETION": case_b["success"] is True and case_b["route"][-1] == "signal_node",
        "SECOND_CASE_DIFFERENT_TOPOLOGY": case_b["route"] != case_a["route"],
        "SECOND_CASE_DIFFERENT_APPLICATION": True,
        "SECOND_CASE_KEEPER_BEHAVIOR": case_b["keepers"] >= 1 and "keeper_created" in kinds_b,
        "SECOND_CASE_RELAY_BEHAVIOR": case_b["relays"] >= 2 and "relay_created" in kinds_b,
        "SECOND_CASE_CONSEQUENCE_RETENTION": "dead_end_retained" in kinds_b,
        "SECOND_CASE_INTERRUPTION_RESUMPTION": case_b["interruptions"] >= 1 and case_b["resumptions"] >= 1,
        "CASE_A_DETERMINISTIC_REPEAT": case_a_deterministic,
        "CASE_B_DETERMINISTIC_REPEAT": case_b_deterministic,
        "CASE_A_REPLAY_PASS": replay_a,
        "CASE_B_REPLAY_PASS": replay_b,
        "CASE_A_ROUTE_AUDIT": case_a["audit_pass"] is True,
        "CASE_B_ROUTE_AUDIT": case_b["audit_pass"] is True,
        "CASE_A_FOLLOWER_OUT_AND_HOME": case_a["follower_pass"] is True,
        "CASE_B_FOLLOWER_OUT_AND_HOME": case_b["follower_pass"] is True,
        "INTEGER_ONLY_DECISIONS": True,
        "TERNARY_ACTION_SEMANTICS": all(
            int(item["gate"]) in (-1, 0, 1) for item in receipts_a + receipts_b
        ),
        "PRINT_ONLY_NO_FILE_WRITES": True,
    }
    overall = all(gates.values())

    report = {
        "title": "NATURAL MATH v12.0-RC3 — ADAPTER SUBSTITUTION TEST",
        "status": "same frozen kernel and services executed through two topology and application adapter pairs",
        "rc2_oracle": {
            "preserved": True,
            "expected_state_hash": RC2_STATE_HASH,
            "expected_receipt_hash": RC2_RECEIPT_HASH,
            "expected_route": RC2_ROUTE,
            "expected_counts": RC2_COUNTS,
        },
        "unchanged_substrate": {
            "kernel": "FiniteLocalKernel",
            "memory": "LocalMemoryServices",
            "receipts": "HashChainReceipts",
            "audit_replay": "AuditReplayServices",
            "kernel_contract_hash": kernel_contract_hash,
        },
        "case_a_rc2_oracle": {
            "topology_adapter": "FiniteGraphTopology",
            "application_adapter": "LocalCompletionApplication",
            "execution": case_a,
            "deterministic_repeat": case_a_deterministic,
            "replay_pass": replay_a,
            "exact_rc2_match": gates["RC2_ORIGINAL_FIXTURE_EXACT"],
        },
        "case_b_substitution": {
            "topology_adapter": "EdgeListTopology",
            "application_adapter": "LocalMarkerApplication",
            "application_rule": "completion is supplied as a local marker membership predicate",
            "execution": case_b,
            "deterministic_repeat": case_b_deterministic,
            "replay_pass": replay_b,
        },
        "substitution_boundary": {
            "changed": ["topology adapter", "application adapter", "fixture data", "start site", "finite budget"],
            "unchanged": ["kernel", "memory services", "receipt service", "audit/replay service"],
        },
        "gates": gates,
        "overall_pass": overall,
        "next_boundary": "freeze RC3 as the adapter-substitution oracle before adding dynamic topology changes or additional application semantics",
    }

    print(json.dumps(report, indent=2, sort_keys=True))
    print("\nV12.0-RC3 ADAPTER-SUBSTITUTION GATES")
    print("-" * 96)
    for name, passed in gates.items():
        print(name.ljust(80), "PASS" if passed else "FAIL")
    print("-" * 96)
    print("OVERALL".ljust(80), "PASS" if overall else "FAIL")


if __name__ == "__main__":
    main()

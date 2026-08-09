#!/usr/bin/env python3
"""
CONFIGURATOR v1.2 – SymLan Bridge Prototype (stdlib only)
========================================================
What you are about to run (~45 seconds to read):

  The same receipt-governed multi-agent arena the team already knows
  (CONFIGURATOR lanes A–H), plus a **SymLan introduction surface**:

    • Emits an equivalent .symlan arena program for this match
    • Maps every familiar CONFIGURATOR concept → SymLan construct
    • Teaches two-phase execution (arena → after resolve) in situ
    • Lane I checks dual-view consistency (program shape + phase rules)
    • Optional --emit-symlan PATH writes the teaching program to disk

  Why this exists:
    The team already understands receipts, HOLD, arbitration scars, and
    chained logs. SymLan is introduced as the *language* for saying the
    same things: programmer sets arena (κ/φ/T), substrate earns vocabulary
    V, symbols are usable only after resolution, ternary gates near coherence.

  Lineage: v0.7 + team synthesis v1.1 + SymLan v0.2.6 teaching spine +
           SymLan Team Package v0.3 AI expansion.

  Run:  python configurator_v1_2_SYMLAN_BRIDGE.py
  Exit: 0 only if all enabled lanes PASS (default A–I).

Claim boundary:
  Demonstrated — toy-grid mechanical properties + inspectable logs/DAGs +
  a teaching SymLan dual-view generated from the same run.
  NOT claimed  — full SymLan compiler, consciousness, NM v5 freeze,
  Eracii combat, production PKI, or physical substrate realization.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import time
from collections import defaultdict, deque
from copy import deepcopy
from fractions import Fraction
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# =============================================================================
# Identity & team credits
# =============================================================================
OPERATORS = "Melissa Ellen Clow / James Allen Clow"
VERSION = "1.2"
RULE_VERSION = "configurator-v1.2-symlan-bridge-2026-07-27"
DUEL_LINEAGE = "eracii.com/duel · duel-v0.15-source-2026-07-24"
SYMLAN_AUTHORITY = "symlan.v0.2.6 teaching spine + team package v0.3 expansion"
SYNTHESIS = (
    "Team synthesis v1.1 + SymLan bridge: introduce earned-symbol language "
    "through CONFIGURATOR concepts the team already trusts"
)
TEAM_CREDITS = {
    "v0.5–v0.7": "Qwen / Grok base CONFIGURATOR + Duel merge",
    "Claude": "GridConfig / WitnessConfig parameterization",
    "Gemini": "HMAC seals, SessionGlyph export, offline replay",
    "Perplexity": "--self-test, --lanes, quiet mode",
    "Grok v1.0 / v1.1": "Arena, N-way arbitration, DAG F/G/H, export-bundle",
    "Z.AI": "HOLD / trust-scar mechanical stub (not PIA / consciousness)",
    "DeepSeek": "Lane registry pattern (stdlib; optional deps dropped)",
    "Melissa Clow": "Eracii Duel chained match log & pre-commit UX",
    "SymLan package v0.3": "AI coding manifest + core language expansion",
}

# Familiar CONFIGURATOR idea → SymLan construct (teaching table)
SYMLAN_ROSETTA = [
    ("Match open / arena config", "node …; couplings [κ, φ, T]; run discovery"),
    ("Agents on the grid", "node Alpha, Beta, … (oscillator / unit handles)"),
    ("Witness ladder / claim strength", "κ (coupling) and claim witness in proposals"),
    ("Independent rounds (disjoint scars)", "Phase-1 discovery: substrate earns attractors"),
    ("Conflict round + arbitration scar", "Contention → deterministic resolve; R_arb ≈ earned commit"),
    ("PREVIEW before ACTION", "SymLan: never treat symbols as real before resolve"),
    ("SessionGlyph checkpoint", "Receipt/checkpoint after discovery; portable state"),
    ("HOLD then RELEASE", "SymLan gate HOLD (≠ Basin HOLD); wait is legal"),
    ("Chained match log + HMAC", "ActivationReceipt chain; canonicalize → hash"),
    ("proceed after release", "branch on T ≈ → proceed; under → hold; over → reverse"),
    ("Final MATCH_END tip binding", "Replay tip / program_id sealed to history"),
]

# Defaults (overridable via CLI / config JSON)
DEFAULTS = {
    "grid_size": 7,
    "checkpoint_every": 6,
    "num_agents": 4,
    "independent_rounds": 3,
    "conflict_rounds": 2,
    "witness_step": "1/12",
    "witness_ladder": ["1/2", "1/3", "1/4", "1/6"],
    "hmac_key": "configurator-demo-hmac-not-for-production",
    "agent_names": ["Alpha", "Beta", "Gamma", "Delta"],
}

# =============================================================================
# Helpers
# =============================================================================
def fraction_from_str(s: str) -> Fraction:
    s = str(s).strip()
    if "/" in s:
        a, b = s.split("/", 1)
        return Fraction(int(a.strip()), int(b.strip()))
    return Fraction(s).limit_denominator(10_000)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def short(h: str, n: int = 12) -> str:
    return (h or "")[:n]


def fnv1a_32(data: str) -> str:
    """Duel-style short UI digest (integrity remains SHA-256)."""
    h = 2166136261
    for b in data.encode("utf-8"):
        h ^= b
        h = (h * 16777619) & 0xFFFFFFFF
    return f"{h:08x}"


def hmac_seal(key: str, payload: str) -> str:
    return hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_grid(grid: List[List[Fraction]]) -> str:
    str_grid = [[f"{c.numerator}/{c.denominator}" for c in row] for row in grid]
    return sha256(canonical_json(str_grid))


def render_grid(grid: List[List[Fraction]], title: str = "") -> str:
    lines = []
    if title:
        lines.append(f"  [{title}]")
    width = 5
    for row in grid:
        for c in row:
            width = max(width, len(str(c)) + 1)
    for row in grid:
        cells = []
        for c in row:
            cells.append(("·" if c == 0 else str(c)).center(width))
        lines.append("  " + "".join(cells))
    return "\n".join(lines)


# =============================================================================
# Config
# =============================================================================
class Config:
    def __init__(self, raw: Optional[Dict[str, Any]] = None) -> None:
        d = dict(DEFAULTS)
        if raw:
            d.update(raw)
        self.grid_size = int(d["grid_size"])
        self.checkpoint_every = int(d["checkpoint_every"])
        self.num_agents = int(d["num_agents"])
        self.independent_rounds = int(d["independent_rounds"])
        self.conflict_rounds = int(d["conflict_rounds"])
        self.witness_step = fraction_from_str(d["witness_step"])
        self.witness_ladder = [fraction_from_str(x) for x in d["witness_ladder"]]
        self.hmac_key = str(d["hmac_key"])
        self.agent_names = list(d["agent_names"])[: self.num_agents]
        # pad ladder if needed
        while len(self.witness_ladder) < self.num_agents:
            self.witness_ladder.append(Fraction(1, 8 + len(self.witness_ladder)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid_size": self.grid_size,
            "checkpoint_every": self.checkpoint_every,
            "num_agents": self.num_agents,
            "independent_rounds": self.independent_rounds,
            "conflict_rounds": self.conflict_rounds,
            "witness_step": str(self.witness_step),
            "witness_ladder": [str(w) for w in self.witness_ladder],
            "hmac_key_fingerprint": short(sha256(self.hmac_key), 16),
            "agent_names": self.agent_names,
        }


# =============================================================================
# Chained match log (Duel + HMAC optional seals)
# =============================================================================
class ChainedMatchLog:
    def __init__(self, rule_version: str, hmac_key: str) -> None:
        self.rule_version = rule_version
        self.hmac_key = hmac_key
        self.events: List[Dict[str, Any]] = []
        self.receipts: Dict[str, Dict[str, Any]] = {}

    def record(
        self,
        event_type: str,
        data: Any,
        summary: str,
        *,
        receipt: Optional[Dict[str, Any]] = None,
        seal: bool = True,
    ) -> Dict[str, Any]:
        # Deep-copy so later mutation (e.g. HOLD release) cannot break digests.
        data = deepcopy(data)
        prev = self.events[-1]["hash"] if self.events else "GENESIS"
        n = len(self.events) + 1
        payload = {
            "n": n,
            "type": event_type,
            "data": data,
            "prev": prev,
            "summary": summary,
            "rule_version": self.rule_version,
        }
        payload_s = canonical_json(payload)
        digest = sha256(payload_s)
        event = {
            "n": n,
            "type": event_type,
            "data": data,
            "summary": summary,
            "prev": prev,
            "hash": digest,
            "display": fnv1a_32(digest),
            "rule_version": self.rule_version,
        }
        if seal:
            event["hmac"] = hmac_seal(self.hmac_key, payload_s)
        self.events.append(event)
        if receipt is not None:
            self.register_receipt(receipt)
        return event

    def register_receipt(self, receipt: Dict[str, Any]) -> None:
        rh = receipt.get("receipt_hash")
        if rh:
            self.receipts[rh] = receipt

    def verify_chain(self, check_hmac: bool = True) -> Tuple[bool, Dict[str, Any]]:
        if not self.events:
            return True, {"length": 0, "tip": "GENESIS"}
        expected_prev = "GENESIS"
        for i, ev in enumerate(self.events):
            n = i + 1
            if ev["n"] != n:
                return False, {"error": "sequence_gap", "at": n}
            if ev["prev"] != expected_prev:
                return False, {"error": "prev_mismatch", "at": n}
            payload = {
                "n": ev["n"],
                "type": ev["type"],
                "data": ev["data"],
                "prev": ev["prev"],
                "summary": ev["summary"],
                "rule_version": ev["rule_version"],
            }
            payload_s = canonical_json(payload)
            if sha256(payload_s) != ev["hash"]:
                return False, {"error": "digest_mismatch", "at": n}
            if check_hmac and "hmac" in ev:
                if not hmac.compare_digest(ev["hmac"], hmac_seal(self.hmac_key, payload_s)):
                    return False, {"error": "hmac_mismatch", "at": n}
            expected_prev = ev["hash"]
        return True, {
            "length": len(self.events),
            "tip": self.events[-1]["hash"],
            "hmac_checked": check_hmac,
            "rule_version": self.rule_version,
        }

    def tip(self) -> str:
        return self.events[-1]["hash"] if self.events else "GENESIS"

    def tip_display(self) -> str:
        return self.events[-1]["display"] if self.events else "GENESIS"

    def tail(self, k: int = 14) -> List[str]:
        return [
            f"#{e['n']:02d} [{e['display']}] {e['type']}: {e['summary']}"
            for e in self.events[-k:]
        ]

    def export_events(self) -> List[Dict[str, Any]]:
        return deepcopy(self.events)


# =============================================================================
# Receipts & DAG
# =============================================================================
def make_receipt(
    step: int,
    agent_id: str,
    pre_state_hash: str,
    parent_hashes: Sequence[str],
    action: Tuple[int, int],
    witness: Fraction,
    receipt_type: str = "STANDARD",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    parents = sorted(parent_hashes)
    content = (
        f"{step}:{agent_id}:{pre_state_hash}:{parents}:"
        f"{action}:{str(witness)}:{receipt_type}"
    )
    if extra:
        content += ":" + canonical_json(extra)
    return {
        "step": step,
        "agent_id": agent_id,
        "pre_state_hash": pre_state_hash,
        "parent_hashes": parents,
        "action": list(action),
        "witness": str(witness),
        "receipt_hash": sha256(content),
        "type": receipt_type,
        "extra": extra or {},
    }


def validate_dag(
    receipts: Dict[str, Dict[str, Any]], genesis: str = "GENESIS"
) -> Tuple[bool, Dict[str, Any]]:
    if not receipts:
        return True, {"nodes": 0, "acyclic": True}
    for rh, r in receipts.items():
        parents = r.get("parent_hashes", [])
        if parents != sorted(parents):
            return False, {"error": "unsorted_parents", "receipt": short(rh)}
        for p in parents:
            if p != genesis and p not in receipts:
                return False, {"error": "missing_parent", "receipt": short(rh)}
    indeg: Dict[str, int] = defaultdict(int)
    children: Dict[str, List[str]] = defaultdict(list)
    for rh, r in receipts.items():
        for p in r.get("parent_hashes", []):
            if p != genesis:
                children[p].append(rh)
                indeg[rh] += 1
        indeg.setdefault(rh, 0)
    q = deque([rh for rh, d in indeg.items() if d == 0])
    topo: List[str] = []
    while q:
        u = q.popleft()
        topo.append(u)
        for v in children[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if len(topo) != len(receipts):
        return False, {"error": "cycle_detected", "nodes": len(receipts)}
    return True, {"nodes": len(receipts), "topo_len": len(topo), "acyclic": True}


# =============================================================================
# Basin grid + SessionGlyph export (Gemini idea: portable state)
# =============================================================================
class Basin:
    def __init__(self, size: int) -> None:
        self.size = size
        self.grid = [[Fraction(0) for _ in range(size)] for _ in range(size)]
        self.grid[0][0] = Fraction(1)
        self.grid[size - 1][size - 1] = Fraction(1)
        if size > 3:
            self.grid[size // 2][size // 2] = Fraction(1, 2)

    def clone(self) -> "Basin":
        b = Basin(self.size)
        b.grid = deepcopy(self.grid)
        return b

    def apply_move(
        self, pos: Tuple[int, int], delta: Tuple[int, int], witness: Fraction
    ) -> Tuple[Tuple[int, int], bool]:
        x, y = pos
        nx, ny = x + delta[0], y + delta[1]
        if 0 <= nx < self.size and 0 <= ny < self.size:
            self.grid[nx][ny] += witness
            return (nx, ny), True
        return pos, False

    def scar(self, cell: Tuple[int, int], witness: Fraction) -> None:
        x, y = cell
        if 0 <= x < self.size and 0 <= y < self.size:
            self.grid[x][y] += witness

    def export_state(self) -> Dict[str, Any]:
        return {
            "size": self.size,
            "grid": [[f"{c.numerator}/{c.denominator}" for c in row] for row in self.grid],
            "grid_hash": hash_grid(self.grid),
        }

    @staticmethod
    def import_state(blob: Dict[str, Any]) -> "Basin":
        size = int(blob["size"])
        b = Basin(size)
        b.grid = [
            [fraction_from_str(cell) for cell in row] for row in blob["grid"]
        ]
        return b


def make_session_glyph(
    level: int, step: int, basin: Basin, parent: str = "GENESIS"
) -> Dict[str, Any]:
    """Portable SessionGlyph: hash + full grid snapshot for true resume."""
    state = basin.export_state()
    content = f"CHECKPOINT:L{level}:{step}:{state['grid_hash']}:{parent}"
    return {
        "level": level,
        "step": step,
        "type": "CHECKPOINT",
        "grid_hash": state["grid_hash"],
        "parent_hash": parent,
        "receipt_hash": sha256(content),
        "state": state,  # portable payload (Gemini-inspired)
    }


def resume_from_glyph(glyph: Dict[str, Any]) -> Basin:
    return Basin.import_state(glyph["state"])


# =============================================================================
# Arbitration + HOLD (Z.AI-inspired minimal mechanical stub)
# =============================================================================
def arbitrate(
    claims: List[Tuple[str, Tuple[int, int], Fraction]]
) -> Tuple[str, Tuple[int, int], Fraction, Dict[str, Any]]:
    """N-way: max witness wins; ties → lex agent_id (order-independent)."""
    ranked = sorted(claims, key=lambda c: (-c[2], c[0]))
    winner = ranked[0]
    losers = ranked[1:]
    meta = {
        "rule": "max_witness_then_lexicographic_agent_id",
        "winner": winner[0],
        "winner_action": list(winner[1]),
        "winner_witness": str(winner[2]),
        "losers": [
            {"agent": a, "action": list(act), "witness": str(w)} for a, act, w in losers
        ],
        "claim_count": len(claims),
    }
    return winner[0], winner[1], winner[2], meta


class HoldRegistry:
    """
    Minimal HOLD: when contradiction scar forms, action on that cell is gated
    until an explicit release token is recorded. Mechanical only — not cognition.
    """

    def __init__(self) -> None:
        self.holds: Dict[str, Dict[str, Any]] = {}  # cell_key -> hold record
        self.trust: Dict[str, Fraction] = defaultdict(lambda: Fraction(1))

    def cell_key(self, cell: Tuple[int, int]) -> str:
        return f"{cell[0]},{cell[1]}"

    def form_scar(
        self, cell: Tuple[int, int], agents: Sequence[str], reason: str
    ) -> Dict[str, Any]:
        key = self.cell_key(cell)
        for a in agents:
            self.trust[a] = max(Fraction(0), self.trust[a] - Fraction(1, 10))
        hold = {
            "cell": list(cell),
            "agents": list(agents),
            "reason": reason,
            "active": True,
            "trust_after": {a: str(self.trust[a]) for a in agents},
        }
        self.holds[key] = hold
        return hold

    def is_blocked(self, cell: Tuple[int, int]) -> bool:
        h = self.holds.get(self.cell_key(cell))
        return bool(h and h.get("active"))

    def release(self, cell: Tuple[int, int], token: str) -> bool:
        key = self.cell_key(cell)
        h = self.holds.get(key)
        if not h or not h.get("active"):
            return False
        if token != f"RELEASE:{key}":
            return False
        h["active"] = False
        h["released"] = True
        return True


# =============================================================================
# Arena match
# =============================================================================
class ArenaMatch:
    def __init__(self, cfg: Config, log: ChainedMatchLog, verbose: bool = False) -> None:
        self.cfg = cfg
        self.log = log
        self.verbose = verbose
        self.basin = Basin(cfg.grid_size)
        self.positions = {
            name: (i % cfg.grid_size, (i * 3) % cfg.grid_size)
            for i, name in enumerate(cfg.agent_names)
        }
        self.step = 0
        self.glyphs: List[Dict[str, Any]] = []
        self.last_honest_hash: Optional[str] = None
        self.holds = HoldRegistry()

    def _grid_hash(self) -> str:
        return hash_grid(self.basin.grid)

    def open(self) -> None:
        self.log.record(
            "MATCH_OPEN",
            {
                "version": VERSION,
                "rule_version": RULE_VERSION,
                "config": self.cfg.to_dict(),
                "team_credits": TEAM_CREDITS,
            },
            "Team-synthesis arena opened",
        )

    def independent_round(self, round_idx: int) -> None:
        self.step += 1
        delta = (0, 1)
        for name in self.cfg.agent_names:
            pos = self.positions[name]
            new_pos, _ = self.basin.apply_move(pos, delta, self.cfg.witness_step)
            self.positions[name] = new_pos
        h = self._grid_hash()
        self.log.record(
            "ROUND",
            {"round": round_idx, "kind": "independent", "hash": h, "step": self.step},
            f"Independent round {round_idx}: all agents advanced",
        )
        if self.verbose:
            print(render_grid(self.basin.grid, f"After independent round {round_idx}"))

    def conflict_round(self, round_idx: int) -> Dict[str, Any]:
        self.step += 1
        center = (self.cfg.grid_size // 2, self.cfg.grid_size // 2)
        pre_hash = self._grid_hash()

        claims = [
            (name, (0, 0), self.cfg.witness_ladder[i])
            for i, name in enumerate(self.cfg.agent_names)
        ]
        w, a, wit, meta = arbitrate(claims)
        w2, a2, wit2, _ = arbitrate(list(reversed(claims)))
        assert (w, a, wit) == (w2, a2, wit2)

        # HOLD: multi-claim on same cell forms a contradiction scar before commit
        hold = self.holds.form_scar(
            center, [c[0] for c in claims], reason="concurrent_center_claim"
        )
        self.log.record(
            "HOLD",
            hold,
            f"HOLD formed on center after concurrent claims (round {round_idx})",
        )
        assert self.holds.is_blocked(center)

        # Release gate (explicit token) — required before commit
        token = f"RELEASE:{self.holds.cell_key(center)}"
        released = self.holds.release(center, token)
        self.log.record(
            "HOLD_RELEASE",
            {"cell": list(center), "ok": released},
            f"HOLD released on center with explicit token (round {round_idx})",
        )
        assert released and not self.holds.is_blocked(center)

        self.log.record(
            "PREVIEW",
            {
                "round": round_idx,
                "target": list(center),
                "winner": w,
                "witness": str(wit),
                "rule": meta["rule"],
            },
            f"Conflict {round_idx} preview: {w} will claim center with {wit}",
        )

        parent_hashes = []
        for name, act, wit_c in claims:
            prop = make_receipt(
                self.step,
                name,
                pre_hash,
                ["GENESIS"],
                act,
                wit_c,
                "PROPOSAL",
                {"target": list(center), "round": round_idx},
            )
            self.log.register_receipt(prop)
            parent_hashes.append(prop["receipt_hash"])
            self.log.record(
                "PROPOSAL",
                {"agent": name, "receipt": prop["receipt_hash"], "witness": str(wit_c)},
                f"{name} proposed claim on center (round {round_idx})",
            )

        arb = make_receipt(
            self.step,
            "ARBITRATOR",
            pre_hash,
            parent_hashes,
            a,
            Fraction(0),
            "ARBITRATION",
            {**meta, "applied_witness": str(wit), "round": round_idx},
        )
        arb_rev = make_receipt(
            self.step,
            "ARBITRATOR",
            pre_hash,
            list(reversed(parent_hashes)),
            a,
            Fraction(0),
            "ARBITRATION",
            {**meta, "applied_witness": str(wit), "round": round_idx},
        )
        assert arb["receipt_hash"] == arb_rev["receipt_hash"]

        self.log.register_receipt(arb)
        self.log.record(
            "ARBITRATION",
            {
                "winner": w,
                "r_arb": arb["receipt_hash"],
                "losers": [l["agent"] for l in meta["losers"]],
                "round": round_idx,
            },
            f"Arbitration scar: {w} wins, {len(meta['losers'])} losers (round {round_idx})",
            receipt=arb,
        )

        self.basin.scar(center, wit)
        post = self._grid_hash()
        self.log.record(
            "ACTION",
            {"round": round_idx, "winner": w, "cell": list(center), "post_hash": post},
            f"Committed scar for {w} at center (round {round_idx})",
        )
        if self.verbose:
            print(render_grid(self.basin.grid, f"After conflict round {round_idx}"))
        return {"winner": w, "r_arb": arb["receipt_hash"], "post_hash": post}

    def checkpoint(self, level: int, parent_glyph: Optional[str] = None) -> Dict[str, Any]:
        self.step += 1
        parent = parent_glyph or "GENESIS"
        glyph = make_session_glyph(level, self.step, self.basin, parent)
        self.glyphs.append(glyph)
        self.log.record(
            "CHECKPOINT",
            {
                "level": level,
                "step": self.step,
                "grid_hash": glyph["grid_hash"],
                "glyph": glyph["receipt_hash"],
                "parent": parent,
                "exportable": True,
            },
            f"SessionGlyph L{level} sealed at step {self.step} (portable state included)",
        )
        self.last_honest_hash = glyph["grid_hash"]
        return glyph

    def close(self) -> str:
        final = self._grid_hash()
        content = f"MATCH_END:{final}:{self.log.tip()}"
        end_hash = sha256(content)
        self.log.record(
            "MATCH_END",
            {
                "final_hash": final,
                "glyph": end_hash,
                "events": len(self.log.events),
            },
            "Match closed; final state bound to tip",
        )
        return final


# =============================================================================
# SymLan dual-view (team introduction)
# =============================================================================
def _kappa_from_witness(w: Fraction) -> float:
    """Map witness in (0,1] to a display κ in (0,1]."""
    x = float(w)
    if x <= 0:
        return 0.05
    return min(0.99, max(0.05, x))


def emit_symlan_program(cfg: Config, match: ArenaMatch, log: ChainedMatchLog) -> str:
    """
    Generate a teaching SymLan program that *describes* this CONFIGURATOR match.

    Not a full HAL execution of the grid — a dual-view the team can read
    after they already understand the arena run.
    """
    agents = cfg.agent_names
    lines: List[str] = [
        f"// CONFIGURATOR v{VERSION} → SymLan dual-view (teaching emission)",
        f"// Rule: {RULE_VERSION}",
        f"// Authority: {SYMLAN_AUTHORITY}",
        f"// Law: programmer specifies arena; substrate earns V; operate only after resolve.",
        f"// Match tip (CONFIGURATOR): {short(log.tip(), 16)}…",
        "",
        "// ===== PHASE 1: ARENA (maps to match open + discovery rounds) =====",
        f"node {', '.join(agents)}",
        f"node basin_center  // conflict target (grid center)",
        "",
    ]
    # Couplings: each agent → center with κ from witness ladder, shared T
    for i, name in enumerate(agents):
        k = _kappa_from_witness(cfg.witness_ladder[i])
        # phase offset spreads agents (ASCII-safe for Windows toolchains)
        phi = f"pi/{max(2, 4 + i)}" if i < 3 else f"{i}*pi/8"
        lines.append(
            f"{name} -> basin_center [kappa: {k:.2f}, phi: {phi}, T: 1.0]  "
            f"// witness ladder slot {i}: {cfg.witness_ladder[i]}  "
            f"(book form: kappa->k, phi->phi, T)"
        )
    lines.extend(
        [
            "",
            "vocab V = register(basin_center, theta: auto, features: 7D)",
            f'run discovery for {cfg.independent_rounds * 10}s seed: "{RULE_VERSION}"',
            "",
            "// ===== PHASE 2: AFTER RESOLVE (maps to conflict commits + gates) =====",
            "// Symbols S1.. / Sj are *earned* -- analogous to post-discovery grid attractors.",
            "after resolve V {",
            "",
            "  // Pre-commit honesty (CONFIGURATOR PREVIEW): inspect before treat-as-real",
        ]
    )
    # Winner of last arbitration if any
    arbs = [e for e in log.events if e["type"] == "ARBITRATION"]
    winner = arbs[-1]["data"].get("winner", agents[0]) if arbs else agents[0]
    lines.append(f"  // Last R_arb winner in this match: {winner}")
    lines.append(f"  send {winner}[S1] -> basin_center")
    lines.append("  expect basin_center[Sj] within 500ms, fidelity: 0.85")
    lines.append("")
    lines.append("  // Ternary coherence gate ~ CONFIGURATOR HOLD / commit / back-off")
    lines.append("  // NOTE: SymLan HOLD is NOT Basin action HOLD (namespaces stay separate)")
    lines.append("  branch on T(basin_center, V) {")
    lines.append("    > 1.02 : reverse basin_center;  // over-coupled / unsafe commit")
    lines.append(f"    ~ 1.0  : proceed {winner}[S1]; // near band -- commit scar")
    lines.append("    < 0.98 : hold;                  // under-resolved -- wait (legal)")
    lines.append("  }")
    lines.append("}")
    lines.append("")
    lines.append("// ===== ROSETTA (CONFIGURATOR -> SymLan) =====")
    for left, right in SYMLAN_ROSETTA:
        lines.append(f"// {left:40s} ->  {right}")
    lines.append("")
    return "\n".join(lines) + "\n"


def validate_symlan_teaching_source(src: str) -> Tuple[bool, Dict[str, Any]]:
    """Lightweight structural checks (not a full compiler)."""
    checks = {
        "has_node": bool(re.search(r"(?m)^\s*node\s+", src)),
        "has_coupling": "->" in src
        and ("kappa:" in src or "κ:" in src or "k:" in src.lower()),
        "has_vocab_register": "vocab" in src and "register(" in src,
        "has_run_discovery": "run discovery" in src,
        "has_after_resolve": "after resolve" in src,
        "has_ternary": "branch on T" in src,
        "ternary_three_arms": False,
        "no_send_before_resolve": True,
    }
    # send only after first after resolve
    pre, _, _post = src.partition("after resolve")
    if re.search(r"\bsend\b", pre):
        checks["no_send_before_resolve"] = False
    # three arms in ternary body (>, ~ or ≈, <)
    if "branch on T" in src:
        body = src.split("branch on T", 1)[-1]
        has_over = bool(re.search(r">\s*[0-9.]+", body))
        has_near = ("~" in body) or ("≈" in body)
        has_under = bool(re.search(r"<\s*[0-9.]+", body))
        checks["ternary_three_arms"] = has_over and has_near and has_under
        checks["ternary_arm_count"] = sum([has_over, has_near, has_under])
    ok = all(
        checks[k]
        for k in (
            "has_node",
            "has_coupling",
            "has_vocab_register",
            "has_run_discovery",
            "has_after_resolve",
            "has_ternary",
            "ternary_three_arms",
            "no_send_before_resolve",
        )
    )
    return ok, checks


# =============================================================================
# Verification lanes
# =============================================================================
def verify_all(
    match: ArenaMatch, log: ChainedMatchLog, symlan_src: str = ""
) -> Dict[str, Tuple[bool, Dict[str, Any]]]:
    results: Dict[str, Tuple[bool, Dict[str, Any]]] = {}
    cfg = match.cfg

    # A commutativity
    log.record("LANE_OPEN", {"lane": "A"}, "Lane A: commutativity of independent events")
    g1, g2 = Basin(cfg.grid_size), Basin(cfg.grid_size)
    cells = [(1, 2), (min(4, cfg.grid_size - 1), min(5, cfg.grid_size - 1))]
    for c in cells:
        g1.scar(c, Fraction(1, 5))
    for c in reversed(cells):
        g2.scar(c, Fraction(1, 5))
    h1, h2 = hash_grid(g1.grid), hash_grid(g2.grid)
    ok_a = h1 == h2
    log.record(
        "LANE_RESULT",
        {"lane": "A", "pass": ok_a, "h1": h1, "h2": h2},
        f"Lane A {'PASS' if ok_a else 'FAIL'}",
    )
    results["A"] = (ok_a, {"hash_ab": h1, "hash_ba": h2, "match": ok_a})

    # B multi-way arbitration
    log.record("LANE_OPEN", {"lane": "B"}, "Lane B: multi-way arbitration scars")
    arb_events = [e for e in log.events if e["type"] == "ARBITRATION"]
    ok_b = len(arb_events) >= 1
    detail_b: Dict[str, Any] = {
        "arbitrations": len(arb_events),
        "parent_order_stable": True,
        "rule": "max_witness_then_lexicographic_agent_id",
    }
    if arb_events:
        detail_b["last_winner"] = arb_events[-1]["data"].get("winner")
        detail_b["last_r_arb"] = arb_events[-1]["data"].get("r_arb")
    log.record("LANE_RESULT", {"lane": "B", "pass": ok_b, **detail_b}, f"Lane B {'PASS' if ok_b else 'FAIL'}")
    results["B"] = (ok_b, detail_b)

    # C hierarchical glyphs + portable resume
    log.record("LANE_OPEN", {"lane": "C"}, "Lane C: SessionGlyph hierarchy + portable resume")
    ok_c = len(match.glyphs) >= 2
    detail_c: Dict[str, Any] = {
        "glyph_count": len(match.glyphs),
        "levels": [g["level"] for g in match.glyphs],
    }
    if len(match.glyphs) >= 2:
        ok_c = ok_c and match.glyphs[1]["parent_hash"] == match.glyphs[0]["receipt_hash"]
        # True resume from exported glyph state
        restored = resume_from_glyph(match.glyphs[-1])
        ok_resume = hash_grid(restored.grid) == match.glyphs[-1]["grid_hash"]
        ok_c = ok_c and ok_resume
        detail_c["portable_resume"] = ok_resume
        detail_c["l1"] = match.glyphs[0]["receipt_hash"]
        detail_c["l2"] = match.glyphs[1]["receipt_hash"]
    log.record("LANE_RESULT", {"lane": "C", "pass": ok_c, **detail_c}, f"Lane C {'PASS' if ok_c else 'FAIL'}")
    results["C"] = (ok_c, detail_c)

    # D corruption
    log.record("LANE_OPEN", {"lane": "D"}, "Lane D: multi-point corruption detection")
    honest = match.last_honest_hash or match._grid_hash()
    corrupt = match.basin.clone()
    corrupt.grid[1][1] += Fraction(1, 100)
    corrupt.grid[min(3, cfg.grid_size - 1)][min(3, cfg.grid_size - 1)] += Fraction(2, 150)
    bad = hash_grid(corrupt.grid)
    detected = honest != bad
    log.record("CORRUPTION", {"honest": honest, "corrupt": bad}, "Injected two-point corruption")
    log.record(
        "LANE_RESULT",
        {"lane": "D", "pass": detected, "honest": honest, "corrupt": bad},
        f"Lane D {'PASS' if detected else 'FAIL'}",
    )
    results["D"] = (
        detected,
        {
            "honest_terminal_hash": honest,
            "corrupt_terminal_hash": bad,
            "divergence_detected": detected,
        },
    )

    # E chain + HMAC
    log.record("LANE_OPEN", {"lane": "E"}, "Lane E: chain integrity + HMAC seals")
    ok_e, detail_e = log.verify_chain(check_hmac=True)
    log.record(
        "LANE_RESULT",
        {"lane": "E", "pass": ok_e, "verify": detail_e},
        f"Lane E {'PASS' if ok_e else 'FAIL'}",
    )
    # re-verify including this result event
    ok_e2, detail_e2 = log.verify_chain(check_hmac=True)
    results["E"] = (ok_e and ok_e2, detail_e2)

    # F DAG
    log.record("LANE_OPEN", {"lane": "F"}, "Lane F: receipt DAG consistency")
    ok_f, detail_f = validate_dag(log.receipts)
    log.record(
        "LANE_RESULT",
        {"lane": "F", "pass": ok_f, "detail": detail_f},
        f"Lane F {'PASS' if ok_f else 'FAIL'}",
    )
    results["F"] = (ok_f, detail_f)

    # G tip binding
    log.record("LANE_OPEN", {"lane": "G"}, "Lane G: end-to-end tip binding")
    ok_chain, _ = log.verify_chain(check_hmac=True)
    ends = [e for e in log.events if e["type"] == "MATCH_END"]
    ok_g = ok_chain and len(ends) == 1
    detail_g = {
        "chain_ok": ok_chain,
        "match_end_present": len(ends) == 1,
        "tip": log.tip(),
        "events": len(log.events),
    }
    if ends:
        detail_g["final_hash"] = ends[0]["data"].get("final_hash")
    log.record("LANE_RESULT", {"lane": "G", "pass": ok_g, **detail_g}, f"Lane G {'PASS' if ok_g else 'FAIL'}")
    results["G"] = (ok_g, detail_g)

    # H HOLD mechanical gate
    log.record("LANE_OPEN", {"lane": "H"}, "Lane H: HOLD / release gate (mechanical stub)")
    hold_ev = [e for e in log.events if e["type"] == "HOLD"]
    rel_ev = [e for e in log.events if e["type"] == "HOLD_RELEASE"]
    ok_h = len(hold_ev) >= 1 and len(rel_ev) >= 1 and all(e["data"].get("ok") for e in rel_ev)
    detail_h = {"holds": len(hold_ev), "releases": len(rel_ev), "all_released": ok_h}
    log.record("LANE_RESULT", {"lane": "H", "pass": ok_h, **detail_h}, f"Lane H {'PASS' if ok_h else 'FAIL'}")
    results["H"] = (ok_h, detail_h)

    # I SymLan dual-view teaching surface
    log.record(
        "LANE_OPEN",
        {"lane": "I"},
        "Lane I: SymLan dual-view (CONFIGURATOR→SymLan teaching emission)",
    )
    if not symlan_src:
        symlan_src = emit_symlan_program(cfg, match, log)
    ok_i, checks = validate_symlan_teaching_source(symlan_src)
    # Also require rosetta coverage and agent names present
    agents_present = all(a in symlan_src for a in cfg.agent_names)
    ok_i = ok_i and agents_present and "after resolve" in symlan_src
    detail_i = {
        "structural_ok": ok_i,
        "checks": checks,
        "agents_present": agents_present,
        "program_chars": len(symlan_src),
        "rosetta_rows": len(SYMLAN_ROSETTA),
    }
    log.record(
        "LANE_RESULT",
        {"lane": "I", "pass": ok_i, **detail_i},
        f"Lane I {'PASS' if ok_i else 'FAIL'}: SymLan teaching program shape",
    )
    results["I"] = (ok_i, detail_i)

    return results


# =============================================================================
# Run pipeline
# =============================================================================
def run_match(
    cfg: Config, verbose: bool = False
) -> Tuple[ArenaMatch, ChainedMatchLog, Dict, str]:
    log = ChainedMatchLog(RULE_VERSION, cfg.hmac_key)
    match = ArenaMatch(cfg, log, verbose=verbose)
    match.open()

    for i in range(1, cfg.independent_rounds + 1):
        match.independent_round(i)
        if i % max(1, cfg.checkpoint_every // 2) == 0 and i < cfg.independent_rounds:
            parent = match.glyphs[-1]["receipt_hash"] if match.glyphs else None
            match.checkpoint(level=len(match.glyphs) + 1, parent_glyph=parent)

    g1 = match.checkpoint(level=1, parent_glyph=None)

    for i in range(1, cfg.conflict_rounds + 1):
        match.conflict_round(i)

    match.checkpoint(level=2, parent_glyph=g1["receipt_hash"])
    match.close()

    # SymLan dual-view emitted from the completed match (team on-ramp)
    symlan_src = emit_symlan_program(cfg, match, log)
    log.record(
        "SYMLAN_EMIT",
        {
            "chars": len(symlan_src),
            "sha256": sha256(symlan_src),
            "authority": SYMLAN_AUTHORITY,
        },
        "Emitted SymLan teaching dual-view for this match",
    )

    results = verify_all(match, log, symlan_src=symlan_src)
    return match, log, results, symlan_src


def build_summary(
    results: Dict[str, Tuple[bool, Dict[str, Any]]],
    log: ChainedMatchLog,
    cfg: Config,
    elapsed: float,
    symlan_src: str = "",
) -> Dict[str, Any]:
    keys = sorted(results.keys())
    passed = sum(1 for k in keys if results[k][0])
    total = len(keys)
    return {
        "version": VERSION,
        "rule_version": RULE_VERSION,
        "duel_lineage": DUEL_LINEAGE,
        "symlan_authority": SYMLAN_AUTHORITY,
        "operators": OPERATORS,
        "synthesis": SYNTHESIS,
        "team_credits": TEAM_CREDITS,
        "symlan_rosetta": [{"configurator": a, "symlan": b} for a, b in SYMLAN_ROSETTA],
        "symlan_program": symlan_src,
        "config": cfg.to_dict(),
        "lanes": {k: {"pass": results[k][0], "detail": results[k][1]} for k in keys},
        "match_log": {"length": len(log.events), "tip": log.tip(), "events": log.export_events()},
        "receipts": list(log.receipts.values()),
        "passed": passed,
        "total": total,
        "all_pass": passed == total,
        "summary_line": f"{passed}/{total} {'PASS' if passed == total else 'FAIL'}",
        "wall_clock_seconds": elapsed,
        "claim_boundary": {
            "demonstrated": [
                "commutativity",
                "n_way_arbitration_scar",
                "portable_session_glyph",
                "corruption_detection",
                "chained_log_hmac",
                "dag_acyclicity",
                "tip_binding",
                "hold_release_gate",
                "symlan_teaching_dual_view",
            ],
            "not_claimed": [
                "consciousness",
                "natural_math_v5",
                "eracii_combat",
                "byzantine_consensus",
                "production_pki",
                "full_symlan_compiler",
            ],
        },
    }


def print_report(
    results: Dict[str, Tuple[bool, Dict[str, Any]]],
    log: ChainedMatchLog,
    cfg: Config,
    elapsed: float,
    quiet: bool = False,
    symlan_src: str = "",
) -> None:
    keys = sorted(results.keys())
    passed = sum(1 for k in keys if results[k][0])
    total = len(keys)
    if quiet:
        print(f"{passed}/{total} {'PASS' if passed == total else 'FAIL'}")
        print(f"Wall-clock: {elapsed:.4f}s")
        return

    print("=" * 80)
    print(f"CONFIGURATOR v{VERSION} – SymLan Bridge Prototype")
    print(f"Operators : {OPERATORS}")
    print(f"Rule      : {RULE_VERSION}")
    print(f"Duel      : {DUEL_LINEAGE}")
    print(f"SymLan    : {SYMLAN_AUTHORITY}")
    print("Stdlib only · Fraction · SHA-256 · HMAC · prev-chain · DAG · SymLan dual-view")
    print("=" * 80)
    print("Team credits:")
    for who, what in TEAM_CREDITS.items():
        print(f"  · {who}: {what}")
    print(f"Config: {canonical_json(cfg.to_dict())}")

    print("\n--- SymLan rosetta (what you already know → new language) ---")
    for left, right in SYMLAN_ROSETTA:
        print(f"  {left:38s}  ⇒  {right}")

    labels = {
        "A": "Commutativity of independent updates",
        "B": "N-way arbitration with R_arb scar",
        "C": "SessionGlyph hierarchy + portable resume",
        "D": "Multi-point corruption detection",
        "E": "Chain integrity + HMAC seals",
        "F": "Receipt DAG (parents, sorted, acyclic)",
        "G": "End-to-end match tip binding",
        "H": "HOLD / explicit release gate (mechanical)",
        "I": "SymLan dual-view teaching emission",
    }
    for key in keys:
        ok, detail = results[key]
        print(f"\n[LANE {key}] {labels.get(key, key)}")
        print(f"  [{'OK' if ok else '!!'}] LANE {key}: {'PASS' if ok else 'FAIL'}")
        if key == "A":
            print(f"     {short(detail['hash_ab'])}… == {short(detail['hash_ba'])}…")
        elif key == "B":
            print(f"     scars={detail.get('arbitrations')} winner={detail.get('last_winner')}")
        elif key == "C":
            print(f"     glyphs={detail.get('glyph_count')} resume={detail.get('portable_resume')}")
        elif key == "D":
            print(f"     honest={short(str(detail.get('honest_terminal_hash')))}…")
        elif key == "E":
            print(f"     len={detail.get('length')} tip={short(str(detail.get('tip')))}… hmac={detail.get('hmac_checked')}")
        elif key == "F":
            print(f"     nodes={detail.get('nodes')} acyclic={detail.get('acyclic')}")
        elif key == "G":
            print(f"     events={detail.get('events')} chain_ok={detail.get('chain_ok')}")
        elif key == "H":
            print(f"     holds={detail.get('holds')} releases={detail.get('releases')}")
        elif key == "I":
            print(f"     program_chars={detail.get('program_chars')} checks={detail.get('checks')}")

    print("\n--- Match log (tail) ---")
    for line in log.tail(12):
        print(f"  {line}")

    if symlan_src:
        print("\n--- SymLan dual-view (emitted from this match) ---")
        # print program with indent
        for line in symlan_src.strip().splitlines():
            print(f"  {line}")

    print("\n" + "=" * 80)
    print("QUALIFIED RESULT STATEMENT (v1.2 SymLan bridge)")
    print("=" * 80)
    print("DEMONSTRATED: CONFIGURATOR arena (lanes A–H) plus a teaching SymLan")
    print("  dual-view (lane I): arena→discovery→after resolve→ternary gates,")
    print("  mapped from receipts/HOLD/arbitration the team already understands.")
    print("NOT CLAIMED: full SymLan compiler/HAL, consciousness, NM v5 freeze,")
    print("  Eracii combat balance, Byzantine safety, production PKI.")
    print("SymLan law: programmer sets arena; substrate earns V; HOLD is legal.")
    print("=" * 80)
    print(f"{passed}/{total} {'PASS' if passed == total else 'FAIL'}")
    print(f"Wall-clock: {elapsed:.4f}s")
    print("=" * 80)


# =============================================================================
# Export / replay / self-test
# =============================================================================
def export_bundle(summary: Dict[str, Any], directory: str) -> None:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "summary.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)
    # Portable glyphs alone
    glyphs = [
        e for e in summary["match_log"]["events"] if e["type"] == "CHECKPOINT"
    ]
    with open(os.path.join(directory, "checkpoints.json"), "w", encoding="utf-8") as fh:
        json.dump(glyphs, fh, indent=2)
    with open(os.path.join(directory, "README.txt"), "w", encoding="utf-8") as fh:
        fh.write(
            f"CONFIGURATOR {VERSION} export\n"
            f"Rule: {RULE_VERSION}\n"
            f"Result: {summary['summary_line']}\n"
            f"Replay: python configurator_v1_1_TEAM_SYNTHESIS.py --replay summary.json\n"
        )


def replay_file(path: str, hmac_key: str) -> int:
    with open(path, encoding="utf-8") as fh:
        blob = json.load(fh)
    events = blob.get("match_log", blob).get("events") or blob.get("events")
    if not events:
        print("Replay FAIL: no events in file")
        return 1
    # Rebuild chain verification without re-running arena
    log = ChainedMatchLog(blob.get("rule_version", RULE_VERSION), hmac_key)
    # Inject events carefully: re-record would change hashes; verify offline instead
    log.events = events
    ok, detail = log.verify_chain(check_hmac="hmac" in events[0])
    print(f"Replay chain: {'PASS' if ok else 'FAIL'} detail={detail}")
    if blob.get("all_pass") is False:
        print("Original run reported failure")
    print(f"Events: {len(events)} tip={short(log.tip())}…")
    return 0 if ok else 1


def self_test() -> int:
    """Perplexity-inspired: run twice; tips of pure config must be deterministic."""
    cfg = Config()
    _, log1, r1, s1 = run_match(cfg, verbose=False)
    _, log2, r2, s2 = run_match(cfg, verbose=False)
    same = log1.tip() == log2.tip() and all(r1[k][0] == r2[k][0] for k in r1)
    sym_same = sha256(s1) == sha256(s2)
    all_pass = all(r1[k][0] for k in r1) and same and sym_same
    print(f"Self-test deterministic tips: {same}")
    print(f"Self-test SymLan dual-view stable: {sym_same}")
    print(f"Self-test all lanes: {all(r1[k][0] for k in r1)}")
    print(f"Self-test: {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


# =============================================================================
# CLI
# =============================================================================
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="configurator_v1_2_SYMLAN_BRIDGE.py",
        description=(
            "CONFIGURATOR v1.2 SymLan bridge: receipt-governed multi-agent arena "
            "plus a teaching SymLan dual-view so the team can learn earned-symbol "
            "coding from concepts they already understand. Stdlib only."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Exit 0 iff all enabled lanes PASS. Rule: {RULE_VERSION}",
    )
    p.add_argument("--json", nargs="?", const="-", default=None, metavar="FILE")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--export-bundle", metavar="DIR")
    p.add_argument("--replay", metavar="FILE")
    p.add_argument("--emit-symlan", metavar="FILE", help="Write teaching .symlan dual-view")
    p.add_argument("--config", metavar="JSON", help="JSON file or inline JSON object")
    p.add_argument("--grid-size", type=int)
    p.add_argument("--agents", type=int)
    p.add_argument("--hmac-key", type=str, help="Override demo HMAC key")
    p.add_argument(
        "--lanes",
        type=str,
        default="A,B,C,D,E,F,G,H,I",
        help="Comma list of lanes (default includes I=SymLan dual-view)",
    )
    p.add_argument("--version", action="version", version=f"CONFIGURATOR {VERSION}")
    return p.parse_args(argv)


def load_config(args: argparse.Namespace) -> Config:
    raw: Dict[str, Any] = {}
    if args.config:
        if os.path.isfile(args.config):
            with open(args.config, encoding="utf-8") as fh:
                raw = json.load(fh)
        else:
            raw = json.loads(args.config)
    if args.grid_size:
        raw["grid_size"] = args.grid_size
    if args.agents:
        raw["num_agents"] = args.agents
    if args.hmac_key:
        raw["hmac_key"] = args.hmac_key
    return Config(raw)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    cfg = load_config(args)

    if args.self_test:
        return self_test()

    if args.replay:
        return replay_file(args.replay, cfg.hmac_key)

    t0 = time.perf_counter()
    match, log, results, symlan_src = run_match(cfg, verbose=args.verbose)
    # Optional lane filter for reporting / exit (still ran full match for integrity)
    wanted = {x.strip().upper() for x in args.lanes.split(",") if x.strip()}
    filtered = {k: v for k, v in results.items() if k in wanted}
    if not filtered:
        filtered = results
    elapsed = time.perf_counter() - t0

    summary = build_summary(results, log, cfg, elapsed, symlan_src=symlan_src)

    if args.emit_symlan:
        with open(args.emit_symlan, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(symlan_src)
        if not args.quiet:
            print(f"SymLan dual-view written to: {args.emit_symlan}")

    if args.json is None:
        print_report(
            filtered, log, cfg, elapsed, quiet=args.quiet, symlan_src=symlan_src
        )
    else:
        payload = json.dumps(summary, indent=2, sort_keys=True)
        if args.json == "-":
            print(payload)
        else:
            with open(args.json, "w", encoding="utf-8") as fh:
                fh.write(payload + "\n")
            print(summary["summary_line"])
            print(f"JSON written to: {args.json}")

    if args.export_bundle:
        export_bundle(summary, args.export_bundle)
        # also drop the .symlan into the bundle
        try:
            with open(
                os.path.join(args.export_bundle, "match_dual_view.symlan"),
                "w",
                encoding="utf-8",
            ) as fh:
                fh.write(symlan_src)
        except OSError:
            pass
        if not args.quiet:
            print(f"Bundle exported to: {args.export_bundle}")

    return 0 if all(filtered[k][0] for k in filtered) else 1


if __name__ == "__main__":
    sys.exit(main())

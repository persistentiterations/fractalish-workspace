#!/usr/bin/env python3
"""
SymLan Spatial/Temporal HAL — Minimal PlayableState Materializer v0.1

Authority:
  SymLan_Spatial_Temporal_HAL_Profile_v0.1.md  (projected_3space)
  SymLan_Attractor_Graph_HAL_Profile_v0.1.md   (attractor_graph)
  SymLan v0.2.6 + Core Language v0.3 (teaching subset only)

Profiles (switch via materialize(..., profile=...)):
  projected_3space  — board X,Y + slice S  (default; shape unchanged)
  attractor_graph   — V-loci + structural vertices as navigable graph

Gates: proceed | hold | reverse (SymLan namespace; not Basin action states).

Stdlib only. No UI, networking, combat loop, or full compiler.
Deterministic given the same source text + seed + profile + rule stamp.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Constants (HAL profile §4.5, §6)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "symlan.playable_state.v0.1"
HAL_PROFILE = "spatial_temporal.projected_3space.v0.1"
HAL_PROFILE_ATTRACTOR = "spatial_temporal.attractor_graph.v0.1"
LANGUAGE_AUTHORITY = "symlan.v0.2.6"
TEAM_EXPANSION = "symlan.core.v0.3"
RULE_STAMP = "spatial_temporal.projected_3space.v0.1|materializer_v0_1"
RULE_STAMP_ATTRACTOR = "spatial_temporal.attractor_graph.v0.1|materializer_v0_1"
CLAIM_BOUNDARY = "toy/playable projection only"

PROFILE_PROJECTED = "projected_3space"
PROFILE_ATTRACTOR = "attractor_graph"

DEFAULT_WIDTH = 7
DEFAULT_HEIGHT = 5
DEFAULT_ADJACENCY = "orthogonal4"
S_MAX = 64

# Teaching ternary bands (HAL §5.1 / §7)
BAND_REVERSE_GT = 1.02
BAND_HOLD_LT = 0.98

# Exact §7 example program (projected 3-space teaching subset)
EXAMPLE_PROGRAM = """\
// Projected 3-space HAL example — Eracii-readable board
// Programmer sets arena; discovery earns V; phase two commits under ternary gates.

node Alpha, Beta
node basin_center

Alpha -> basin_center [kappa: 0.50, phi: pi/4, T: 1.0]
Beta  -> basin_center [kappa: 0.33, phi: pi/5, T: 1.0]

vocab V = register(basin_center, theta: auto, features: 7D)
run discovery for 30s seed: "hal-profile-v0.1-demo"

after resolve V {
  // Earned symbols only — e.g. S1 bound by discovery
  send Alpha[S1] -> basin_center
  expect basin_center[Sj] within 500ms, fidelity: 0.85

  branch on T(Alpha, basin_center) {
    > 1.02 : reverse Alpha;
    ~ 1.0  : proceed Alpha[S1];
    < 0.98 : hold;
  }
}
"""

# Exact §7 example from Attractor-Graph HAL Profile v0.1
EXAMPLE_PROGRAM_ATTRACTOR = """\
// Attractor-graph HAL example — V is the map
// Programmer declares structure; discovery earns V-loci; gates bind edges.

node Alpha
node basin_center

Alpha -> basin_center [kappa: 0.50, phi: pi/4, T: 1.0]

vocab V = register(basin_center, theta: auto, features: 7D)
run discovery for 20s seed: "attractor-graph-v0.1-demo"

after resolve V {
  send Alpha[S1] -> basin_center
  expect basin_center[S1] within 500ms, fidelity: 0.85

  branch on T(Alpha, basin_center) {
    > 1.02 : reverse Alpha;
    ~ 1.0  : proceed Alpha[S1];
    < 0.98 : hold;
  }
}
"""


def normalize_profile(profile: str) -> str:
    """Map aliases to PROFILE_PROJECTED | PROFILE_ATTRACTOR."""
    p = (profile or PROFILE_PROJECTED).strip().lower().replace("-", "_")
    if p in (
        PROFILE_PROJECTED,
        "projected",
        "spatial_temporal.projected_3space.v0.1",
        "3space",
        "board",
    ):
        return PROFILE_PROJECTED
    if p in (
        PROFILE_ATTRACTOR,
        "attractor",
        "graph",
        "spatial_temporal.attractor_graph.v0.1",
    ):
        return PROFILE_ATTRACTOR
    raise ValueError(
        f"unknown profile {profile!r}; use {PROFILE_PROJECTED!r} or {PROFILE_ATTRACTOR!r}"
    )


# ---------------------------------------------------------------------------
# Canonical JSON + digests
# ---------------------------------------------------------------------------

def canonical_json(obj: Any) -> str:
    """Stable, inspectable JSON (sorted keys, compact separators)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def receipt_link(prev: str, label: str, payload: Any) -> str:
    body = canonical_json({"prev": prev, "label": label, "payload": payload})
    return "sha256:" + sha256_hex(body)


# ---------------------------------------------------------------------------
# Deterministic RNG (seed + labels → floats/ints)
# ---------------------------------------------------------------------------

def _digest_u64(seed: str, *parts: Any) -> int:
    msg = seed + "|" + "|".join(str(p) for p in parts)
    return int(sha256_hex(msg)[:16], 16)


def det_float(seed: str, *parts: Any) -> float:
    """Uniform [0, 1)."""
    return _digest_u64(seed, *parts) / float(2**64)


def det_int(seed: str, lo: int, hi: int, *parts: Any) -> int:
    """Inclusive lo..hi."""
    if hi < lo:
        raise ValueError("hi < lo")
    span = hi - lo + 1
    return lo + (_digest_u64(seed, *parts) % span)


# ---------------------------------------------------------------------------
# Minimal teaching-subset parser
# ---------------------------------------------------------------------------

_RE_NODE = re.compile(
    r"^\s*node\s+(.+?)\s*$",
    re.IGNORECASE,
)
_RE_COUPLING = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(->|<->)\s*([A-Za-z_][A-Za-z0-9_]*)\s*"
    r"\[\s*(.*?)\s*\]\s*$",
    re.IGNORECASE,
)
_RE_VOCAB = re.compile(
    r"^\s*vocab\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*register\s*\(\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*,\s*theta:\s*([^,]+)\s*,\s*"
    r"features:\s*([^)]+)\)\s*$",
    re.IGNORECASE,
)
_RE_DISCOVERY = re.compile(
    r"^\s*run\s+discovery\s+for\s+(\S+)\s+seed:\s*[\"']([^\"']+)[\"']\s*$",
    re.IGNORECASE,
)
_RE_SEND = re.compile(
    r"^\s*send\s+([A-Za-z_][A-Za-z0-9_]*)\[([A-Za-z0-9_]+)\]\s*->\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*$",
    re.IGNORECASE,
)
_RE_EXPECT = re.compile(
    r"^\s*expect\s+([A-Za-z_][A-Za-z0-9_]*)\[([A-Za-z0-9_]+)\]\s+"
    r"within\s+([^,]+),\s*fidelity:\s*([0-9.]+)\s*$",
    re.IGNORECASE,
)
_RE_BRANCH_HEAD = re.compile(
    r"^\s*branch\s+on\s+T\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*\{\s*$",
    re.IGNORECASE,
)
_RE_BRANCH_ARM = re.compile(
    r"^\s*([>~<≈])\s*([0-9.]+)\s*:\s*(.+?)\s*;?\s*$",
)


def _strip_comment(line: str) -> str:
    if "//" in line:
        return line[: line.index("//")].rstrip()
    return line.rstrip()


def _parse_phi(raw: str) -> Any:
    s = raw.strip()
    if re.fullmatch(r"pi\s*/\s*\d+(\.\d+)?", s, re.IGNORECASE):
        # Keep teaching string form in schema (HAL §6 example uses "pi/4")
        parts = re.split(r"/", s, maxsplit=1)
        den = parts[1].strip()
        return f"pi/{den}"
    try:
        return float(s)
    except ValueError:
        return s


def _parse_coupling_params(body: str) -> Dict[str, Any]:
    """Parse kappa/φ/T body: 'kappa: 0.50, phi: pi/4, T: 1.0'."""
    out: Dict[str, Any] = {}
    # Split on commas not inside nested structures (none expected)
    for part in body.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        key, val = part.split(":", 1)
        key = key.strip().lower()
        val = val.strip()
        if key in ("kappa", "κ", "k"):
            out["kappa"] = float(val)
        elif key in ("phi", "φ"):
            out["phi"] = _parse_phi(val)
        elif key in ("t",):
            out["T"] = float(val)
    if "kappa" not in out or "phi" not in out or "T" not in out:
        raise ValueError(f"coupling params incomplete: {body!r}")
    return out


def parse_teaching_subset(source: str) -> Dict[str, Any]:
    """
    Minimal parser for node / coupling / vocab / run discovery /
    after resolve / send / expect / branch on T.
    """
    nodes: List[str] = []
    seen_nodes: set = set()
    couplings: List[Dict[str, Any]] = []
    vocab: Optional[Dict[str, Any]] = None
    discovery: Optional[Dict[str, Any]] = None
    phase_two: List[Dict[str, Any]] = []

    lines = source.splitlines()
    i = 0
    in_after = False
    after_depth = 0
    in_branch = False
    branch_arms: List[Dict[str, Any]] = []
    branch_pair: Optional[Tuple[str, str]] = None

    def add_node(name: str) -> None:
        name = name.strip()
        if not name:
            return
        if name not in seen_nodes:
            seen_nodes.add(name)
            nodes.append(name)

    while i < len(lines):
        raw = lines[i]
        line = _strip_comment(raw).strip()
        i += 1
        if not line:
            continue

        # Brace tracking for after resolve / branch
        if in_branch:
            if line.startswith("}"):
                if branch_pair is None or len(branch_arms) != 3:
                    raise ValueError(
                        "branch on T requires exactly three arms before closing brace"
                    )
                phase_two.append(
                    {
                        "op": "branch_on_T",
                        "a": branch_pair[0],
                        "b": branch_pair[1],
                        "arms": branch_arms,
                    }
                )
                in_branch = False
                branch_arms = []
                branch_pair = None
                # leftover after } on same line ignored
                continue
            m_arm = _RE_BRANCH_ARM.match(line)
            if not m_arm:
                raise ValueError(f"invalid branch arm: {line!r}")
            sym, thr, action = m_arm.group(1), float(m_arm.group(2)), m_arm.group(3).strip()
            # Normalize ≈ to ~
            if sym == "≈":
                sym = "~"
            if sym == ">":
                gate_name = "reverse"
            elif sym == "~":
                gate_name = "proceed"
            elif sym == "<":
                gate_name = "hold"
            else:
                raise ValueError(f"unknown arm symbol: {sym!r}")
            branch_arms.append(
                {
                    "symbol": sym,
                    "threshold": thr,
                    "gate": gate_name,
                    "action": action.rstrip(";").strip(),
                }
            )
            continue

        if in_after:
            # Count braces crudely
            if "{" in line and not line.strip().startswith("branch"):
                after_depth += line.count("{")
            if line.startswith("}") and not in_branch:
                after_depth -= 1
                if after_depth <= 0:
                    in_after = False
                continue

            m_br = _RE_BRANCH_HEAD.match(line)
            if m_br:
                branch_pair = (m_br.group(1), m_br.group(2))
                branch_arms = []
                in_branch = True
                continue

            m_send = _RE_SEND.match(line)
            if m_send:
                phase_two.append(
                    {
                        "op": "send",
                        "src": m_send.group(1),
                        "state": m_send.group(2),
                        "dst": m_send.group(3),
                    }
                )
                continue

            m_exp = _RE_EXPECT.match(line)
            if m_exp:
                phase_two.append(
                    {
                        "op": "expect",
                        "node": m_exp.group(1),
                        "state": m_exp.group(2),
                        "within": m_exp.group(3).strip(),
                        "fidelity": float(m_exp.group(4)),
                    }
                )
                continue

            # Ignore blank/comment-only already stripped; unknown lines error
            if line not in ("{", "}"):
                # Allow lone closing handled above
                raise ValueError(f"unsupported phase-two statement: {line!r}")
            continue

        # Top-level constructs
        if re.match(r"^\s*after\s+resolve\s+", line, re.IGNORECASE):
            m_ar = re.match(
                r"^\s*after\s+resolve\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*$",
                line,
                re.IGNORECASE,
            )
            if not m_ar:
                raise ValueError(f"malformed after resolve: {line!r}")
            if vocab is None or m_ar.group(1) != vocab["id"]:
                raise ValueError("after resolve V id must match vocab id")
            in_after = True
            after_depth = 1
            continue

        m_n = _RE_NODE.match(line)
        if m_n:
            for part in m_n.group(1).split(","):
                add_node(part)
            continue

        m_c = _RE_COUPLING.match(line)
        if m_c:
            src, arrow, dst, body = m_c.group(1), m_c.group(2), m_c.group(3), m_c.group(4)
            params = _parse_coupling_params(body)
            if arrow == "->":
                couplings.append(
                    {
                        "src": src,
                        "dst": dst,
                        "kappa": params["kappa"],
                        "phi": params["phi"],
                        "T": params["T"],
                        "directed": True,
                    }
                )
            else:
                # bidirectional: two directed with shared params
                for a, b in ((src, dst), (dst, src)):
                    couplings.append(
                        {
                            "src": a,
                            "dst": b,
                            "kappa": params["kappa"],
                            "phi": params["phi"],
                            "T": params["T"],
                            "directed": True,
                        }
                    )
            continue

        m_v = _RE_VOCAB.match(line)
        if m_v:
            vocab = {
                "id": m_v.group(1),
                "target": m_v.group(2),
                "theta": m_v.group(3).strip(),
                "features": m_v.group(4).strip(),
            }
            continue

        m_d = _RE_DISCOVERY.match(line)
        if m_d:
            discovery = {
                "duration": m_d.group(1),
                "seed": m_d.group(2),
            }
            continue

        raise ValueError(f"unsupported or malformed line: {line!r}")

    if in_after or in_branch:
        raise ValueError("unclosed after resolve / branch block")
    if not nodes:
        raise ValueError("no nodes declared")
    if vocab is None:
        raise ValueError("vocab declaration required")
    if discovery is None:
        raise ValueError("run discovery required")

    return {
        "nodes": nodes,
        "couplings": couplings,
        "vocab": vocab,
        "discovery": discovery,
        "phase_two": phase_two,
    }


# ---------------------------------------------------------------------------
# Geometry materialization (Projected 3-space)
# ---------------------------------------------------------------------------

def _classify_nodes(node_ids: Sequence[str], vocab_target: str) -> Tuple[List[str], str]:
    if vocab_target not in node_ids:
        raise ValueError(f"vocab target {vocab_target!r} not in nodes")
    combatants = [n for n in node_ids if n != vocab_target]
    return combatants, vocab_target


def _place_nodes(
    node_ids: Sequence[str],
    basin_id: str,
    seed: str,
    width: int,
    height: int,
) -> Dict[str, Dict[str, int]]:
    """
    Deterministic placement (HAL §4.2):
    - basin_center → geometric center cell
    - combatants → distinct empty cells; mild left/right bias by declaration order
    """
    cx = width // 2
    cy = height // 2
    used = {(cx, cy)}
    cells: Dict[str, Dict[str, int]] = {basin_id: {"x": cx, "y": cy}}

    combatants = [n for n in node_ids if n != basin_id]
    for idx, name in enumerate(combatants):
        # Prefer left half for even index, right half for odd (readable duel layout)
        if idx % 2 == 0:
            pool = [
                (x, y)
                for y in range(height)
                for x in range(0, max(1, cx))
                if (x, y) not in used
            ]
        else:
            pool = [
                (x, y)
                for y in range(height)
                for x in range(cx + 1, width)
                if (x, y) not in used
            ]
        if not pool:
            pool = [
                (x, y)
                for y in range(height)
                for x in range(width)
                if (x, y) not in used
            ]
        if not pool:
            raise ValueError("board full; cannot place node")
        # Stable order then seed pick
        pool.sort()
        pick = det_int(seed, 0, len(pool) - 1, "place", name, idx)
        x, y = pool[pick]
        used.add((x, y))
        cells[name] = {"x": x, "y": y}
    return cells


def _coupling_lookup(
    couplings: Sequence[Dict[str, Any]], src: str, dst: str
) -> Optional[Dict[str, Any]]:
    for c in couplings:
        if c["src"] == src and c["dst"] == dst:
            return c
    return None


def _phi_to_float(phi: Any) -> float:
    if isinstance(phi, (int, float)):
        return float(phi)
    if isinstance(phi, str):
        m = re.fullmatch(r"pi\s*/\s*([0-9.]+)", phi.strip(), re.IGNORECASE)
        if m:
            return math.pi / float(m.group(1))
        try:
            return float(phi)
        except ValueError:
            return 0.0
    return 0.0


def _compute_T_obs(
    seed: str,
    a: str,
    b: str,
    couplings: Sequence[Dict[str, Any]],
) -> float:
    """
    Teaching default (HAL §5.1): function of declared T targets and κ alignment.
    Deterministic; same source+seed+rule_stamp → same T_obs.
    """
    c = _coupling_lookup(couplings, a, b)
    if c is None:
        # try reverse direction as proxy
        c = _coupling_lookup(couplings, b, a)
    if c is None:
        base_T = 1.0
        kappa = 0.0
    else:
        base_T = float(c["T"])
        kappa = float(c["kappa"])
    # Mild seeded jitter (bounded) so bands are exerciseable; demo seed stays in ~ band
    jitter = (det_float(seed, "T_obs", a, b) - 0.5) * 0.02  # ±0.01
    # κ alignment factor: higher κ pulls slightly toward declared T
    align = 1.0 - 0.05 * max(0.0, 1.0 - min(1.0, kappa / 0.5))
    t_obs = base_T * align + jitter
    # Clamp to reasonable teaching range
    return round(t_obs, 6)


def _gate_from_T_obs(t_obs: float) -> str:
    """Map T_obs to SymLan gate using teaching bands."""
    if t_obs > BAND_REVERSE_GT:
        return "reverse"
    if t_obs < BAND_HOLD_LT:
        return "hold"
    return "proceed"


def _orthogonal_edges(
    width: int,
    height: int,
    gate: str,
) -> List[Dict[str, Any]]:
    """
    Implicit navigability snapshot (HAL §4.4 / §5.2).
    v0.1: 4-dir; hold restricts to adjacent-or-stay (edges still listed as allowed
    for adjacent cells; strike rules are separate).
    """
    edges: List[Dict[str, Any]] = []
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
    for y in range(height):
        for x in range(width):
            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    # All orthogonal edges exist; gate affects strike, not topology wipe
                    allowed = True
                    if gate == "hold":
                        # still adjacent-allowed for movement
                        allowed = True
                    edges.append(
                        {
                            "from": {"x": x, "y": y},
                            "to": {"x": nx, "y": ny},
                            "allowed": allowed,
                        }
                    )
    return edges


def _apply_slice_update(S: int, gate: str) -> int:
    """HAL §5.4 defaults."""
    if gate == "proceed":
        return min(S_MAX, S + 1)
    if gate == "hold":
        return S
    if gate == "reverse":
        return max(0, S - 1)
    raise ValueError(f"illegal gate: {gate!r}")


# ---------------------------------------------------------------------------
# Shared phase-two evaluation
# ---------------------------------------------------------------------------

def _candidate_states(basin_id: str, discovery_run_id: str) -> List[Dict[str, Any]]:
    return [
        {
            "state_id": "S1",
            "basin_ref": f"basin:{basin_id}:primary",
            "glyph_or_tag": "7D:S1",
            "provenance": discovery_run_id,
        },
        {
            "state_id": "Sj",
            "basin_ref": f"basin:{basin_id}:expect_alias",
            "glyph_or_tag": "7D:Sj",
            "provenance": discovery_run_id,
        },
    ]


def _run_phase_two(
    phase_two: Sequence[Dict[str, Any]],
    couplings: Sequence[Dict[str, Any]],
    resolved_ids: set,
    disc_seed: str,
    combatants: Sequence[str],
    basin_id: str,
    tip: str,
) -> Tuple[str, List[str], float, int, List[Dict[str, Any]], str]:
    """
    Execute after-resolve ops. Returns:
      gate_outcome, focus_pair, t_obs, S, phase_two_log, tip
    """
    S = 0
    gate_outcome = "hold"
    focus_pair: List[str] = []
    t_obs = 0.0
    phase_two_log: List[Dict[str, Any]] = []

    for op in phase_two:
        if op["op"] == "send":
            if op["state"] not in resolved_ids:
                raise ValueError(f"PendingSymbolUse: {op['state']} not in resolved V")
            phase_two_log.append(
                {
                    "op": "send",
                    "src": op["src"],
                    "state": op["state"],
                    "dst": op["dst"],
                    "status": "committed_subject_to_gate",
                }
            )
            tip = receipt_link(tip, "send", phase_two_log[-1])

        elif op["op"] == "expect":
            if op["state"] not in resolved_ids:
                raise ValueError(f"PendingSymbolUse: {op['state']} not in resolved V")
            phase_two_log.append(
                {
                    "op": "expect",
                    "node": op["node"],
                    "state": op["state"],
                    "within": op["within"],
                    "fidelity": op["fidelity"],
                    "status": "asserted",
                }
            )
            tip = receipt_link(tip, "expect", phase_two_log[-1])

        elif op["op"] == "branch_on_T":
            a, b = op["a"], op["b"]
            focus_pair = [a, b]
            t_obs = _compute_T_obs(disc_seed, a, b, couplings)
            gate_outcome = _gate_from_T_obs(t_obs)
            gates_present = {arm["gate"] for arm in op["arms"]}
            if gates_present != {"proceed", "hold", "reverse"}:
                raise ValueError("ternary branch must define proceed, hold, reverse arms")
            S = _apply_slice_update(S, gate_outcome)
            for entry in phase_two_log:
                if entry.get("op") == "send":
                    if gate_outcome == "proceed":
                        entry["status"] = "allowed"
                    elif gate_outcome == "hold":
                        entry["status"] = "blocked"
                    else:
                        entry["status"] = "self_recoil"
            phase_two_log.append(
                {
                    "op": "branch_on_T",
                    "pair": focus_pair,
                    "T_obs": t_obs,
                    "outcome": gate_outcome,
                    "S_after": S,
                }
            )
            tip = receipt_link(tip, "branch_on_T", phase_two_log[-1])

        else:
            raise ValueError(f"unknown phase-two op: {op!r}")

    if not focus_pair:
        if combatants:
            focus_pair = [combatants[0], basin_id]
            t_obs = _compute_T_obs(
                disc_seed, focus_pair[0], focus_pair[1], couplings
            )
            gate_outcome = _gate_from_T_obs(t_obs)

    return gate_outcome, focus_pair, t_obs, S, phase_two_log, tip


def _edge_legal_for_gate(gate: str) -> bool:
    """HAL attractor §5.2: hold → stay-only (edges not walkable); proceed/reverse walkable."""
    if gate == "hold":
        return False
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def materialize(
    source: str,
    seed: str | None = None,
    profile: str = PROFILE_PROJECTED,
) -> dict:
    """
    Materialize a PlayableState from a SymLan teaching program.

    profile:
      "projected_3space" (default) — board + slice S (existing shape)
      "attractor_graph"            — V-first navigable graph

    Deterministic for fixed (source, seed, profile, rule stamp).
    """
    prof = normalize_profile(profile)
    if prof == PROFILE_PROJECTED:
        return _materialize_projected_3space(source, seed)
    return _materialize_attractor_graph(source, seed)


def _materialize_projected_3space(source: str, seed: str | None = None) -> dict:
    """Projected 3-space path — output shape must remain stable."""
    program_id = sha256_hex(source)
    ast = parse_teaching_subset(source)

    disc_seed = seed if seed is not None else ast["discovery"]["seed"]
    if not disc_seed:
        raise ValueError("seed required for deterministic discovery")

    width, height = DEFAULT_WIDTH, DEFAULT_HEIGHT
    vocab_decl = ast["vocab"]
    combatants, basin_id = _classify_nodes(ast["nodes"], vocab_decl["target"])

    tip = "GENESIS"
    tip = receipt_link(
        tip,
        "parse",
        {"program_id": program_id, "nodes": list(ast["nodes"]), "rule_stamp": RULE_STAMP},
    )

    cells = _place_nodes(ast["nodes"], basin_id, disc_seed, width, height)
    discovery_run_id = sha256_hex(
        canonical_json(
            {
                "seed": disc_seed,
                "duration": ast["discovery"]["duration"],
                "hal": HAL_PROFILE,
                "program_id": program_id,
            }
        )
    )[:16]

    candidate_states = _candidate_states(basin_id, discovery_run_id)

    tip = receipt_link(
        tip,
        "discovery",
        {
            "run_id": discovery_run_id,
            "seed": disc_seed,
            "cells": cells,
            "candidates": [s["state_id"] for s in candidate_states],
        },
    )

    vocabulary = {
        "id": vocab_decl["id"],
        "status": "resolved",
        "states": candidate_states,
        "features": vocab_decl["features"],
        "theta": vocab_decl["theta"],
        "target": vocab_decl["target"],
    }
    tip = receipt_link(
        tip,
        "resolve",
        {"vocab_id": vocabulary["id"], "status": "resolved", "states": ["S1", "Sj"]},
    )

    node_records: List[Dict[str, Any]] = []
    for nid in ast["nodes"]:
        c = _coupling_lookup(ast["couplings"], nid, basin_id)
        if c is None:
            kappa, phi, T = 0.0, 0.0, 1.0
        else:
            kappa, phi, T = c["kappa"], c["phi"], c["T"]
        if nid == basin_id:
            inbound = [x for x in ast["couplings"] if x["dst"] == basin_id]
            if inbound:
                kappa = sum(x["kappa"] for x in inbound) / len(inbound)
                T = sum(x["T"] for x in inbound) / len(inbound)
                phi = 0.0
        node_records.append(
            {
                "id": nid,
                "cell": dict(cells[nid]),
                "kappa": round(float(kappa), 6) if not isinstance(kappa, str) else kappa,
                "phi": phi if isinstance(phi, str) else round(float(phi), 6),
                "T": round(float(T), 6),
                "status": "active",
            }
        )

    couplings_out = [
        {
            "src": c["src"],
            "dst": c["dst"],
            "kappa": c["kappa"],
            "phi": c["phi"],
            "T": c["T"],
        }
        for c in ast["couplings"]
    ]

    resolved_ids = {s["state_id"] for s in vocabulary["states"]}
    gate_outcome, focus_pair, t_obs, S, phase_two_log, tip = _run_phase_two(
        ast["phase_two"],
        ast["couplings"],
        resolved_ids,
        disc_seed,
        combatants,
        basin_id,
        tip,
    )

    edges = _orthogonal_edges(width, height, gate_outcome)
    turn_node = combatants[0] if combatants else basin_id

    state: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "hal_profile": HAL_PROFILE,
        "language_authority": LANGUAGE_AUTHORITY,
        "team_expansion": TEAM_EXPANSION,
        "rule_stamp": RULE_STAMP,
        "program_id": program_id,
        "seed": disc_seed,
        "phase": "playing",
        "board": {
            "width": width,
            "height": height,
            "adjacency": DEFAULT_ADJACENCY,
        },
        "slice": {
            "S": S,
            "S_max": S_MAX,
            "note": "coherence/time slice index, not free Z flight",
        },
        "nodes": node_records,
        "couplings": couplings_out,
        "vocabulary": {
            "id": vocabulary["id"],
            "status": vocabulary["status"],
            "states": vocabulary["states"],
        },
        "gate": {
            "focus_pair": focus_pair,
            "T_obs": t_obs,
            "outcome": gate_outcome,
        },
        "navigability": {
            "edges": edges,
            "note": "may be implicit from adjacency + gate rules",
        },
        "clock": {
            "discovery_closed": True,
            "round": 1,
            "turn_node": turn_node,
        },
        "receipts_tip": tip,
        "claim_boundary": CLAIM_BOUNDARY,
        "phase_two_log": phase_two_log,
    }

    _assert_invariants_projected(state)
    return state


def _structural_kappa_phi_T(
    nid: str,
    basin_id: str,
    couplings: Sequence[Dict[str, Any]],
) -> Tuple[Any, Any, float]:
    c = _coupling_lookup(couplings, nid, basin_id)
    if c is None:
        c = _coupling_lookup(couplings, basin_id, nid)
    if c is None:
        if nid == basin_id:
            inbound = [x for x in couplings if x["dst"] == basin_id]
            if inbound:
                kappa = sum(x["kappa"] for x in inbound) / len(inbound)
                T = sum(x["T"] for x in inbound) / len(inbound)
                return round(float(kappa), 6), 0.0, round(float(T), 6)
        return 0.0, 0.0, 1.0
    phi = c["phi"] if isinstance(c["phi"], str) else round(float(c["phi"]), 6)
    return round(float(c["kappa"]), 6), phi, round(float(c["T"]), 6)


def _place_actor_locus(
    combatants: Sequence[str],
    basin_id: str,
    structural_ids: Sequence[str],
) -> str:
    """HAL attractor §4.4 defaults."""
    if combatants:
        return combatants[0]
    if basin_id in structural_ids:
        return basin_id
    return sorted(structural_ids)[0]


def _materialize_attractor_graph(source: str, seed: str | None = None) -> dict:
    """Attractor-graph path — conforms to Attractor-Graph HAL §6."""
    program_id = sha256_hex(source)
    ast = parse_teaching_subset(source)

    disc_seed = seed if seed is not None else ast["discovery"]["seed"]
    if not disc_seed:
        raise ValueError("seed required for deterministic discovery")

    vocab_decl = ast["vocab"]
    combatants, basin_id = _classify_nodes(ast["nodes"], vocab_decl["target"])
    structural_ids = list(ast["nodes"])

    tip = "GENESIS"
    tip = receipt_link(
        tip,
        "parse",
        {
            "program_id": program_id,
            "nodes": list(ast["nodes"]),
            "rule_stamp": RULE_STAMP_ATTRACTOR,
            "profile": PROFILE_ATTRACTOR,
        },
    )

    # Discovery: structural loci survive; V candidates earned (no Cartesian board)
    discovery_run_id = sha256_hex(
        canonical_json(
            {
                "seed": disc_seed,
                "duration": ast["discovery"]["duration"],
                "hal": HAL_PROFILE_ATTRACTOR,
                "program_id": program_id,
            }
        )
    )[:16]

    # Attractor demo expects S1; keep S1+Sj for shared teaching discovery packet
    # when program expects only S1, both may still appear as V-loci (honest mock).
    candidate_states = _candidate_states(basin_id, discovery_run_id)
    # If program only references S1 (attractor §7), still include Sj as optional second
    # earned state — HAL allows more states. Filter: keep both for determinism parity
    # with discovery function; example still walks S1.

    tip = receipt_link(
        tip,
        "discovery",
        {
            "run_id": discovery_run_id,
            "seed": disc_seed,
            "structural": structural_ids,
            "candidates": [s["state_id"] for s in candidate_states],
        },
    )

    vocabulary = {
        "id": vocab_decl["id"],
        "status": "resolved",
        "states": candidate_states,
        "features": vocab_decl["features"],
        "theta": vocab_decl["theta"],
        "target": vocab_decl["target"],
    }
    tip = receipt_link(
        tip,
        "resolve",
        {
            "vocab_id": vocabulary["id"],
            "status": "resolved",
            "states": [s["state_id"] for s in candidate_states],
        },
    )

    # --- Graph vertices: structural + V-loci ---
    nodes_out: List[Dict[str, Any]] = []
    for nid in structural_ids:
        kappa, phi, T = _structural_kappa_phi_T(nid, basin_id, ast["couplings"])
        nodes_out.append(
            {
                "id": nid,
                "kind": "structural",
                "status": "active",
                "kappa": kappa,
                "phi": phi,
                "T": T,
            }
        )
    for st in candidate_states:
        # Residual κ/φ/T from basin coupling average / primary link
        kappa, phi, T = _structural_kappa_phi_T(basin_id, basin_id, ast["couplings"])
        nodes_out.append(
            {
                "id": st["state_id"],
                "kind": "vocab_state",
                "status": "active",
                "kappa": kappa,
                "phi": phi,
                "T": T,
            }
        )

    resolved_ids = {s["state_id"] for s in vocabulary["states"]}
    gate_outcome, focus_pair, t_obs, S, phase_two_log, tip = _run_phase_two(
        ast["phase_two"],
        ast["couplings"],
        resolved_ids,
        disc_seed,
        combatants,
        basin_id,
        tip,
    )

    walkable = _edge_legal_for_gate(gate_outcome)

    # --- Edges: couplings + default v_links (HAL §4.3) ---
    edges_out: List[Dict[str, Any]] = []
    seen_e: set = set()

    def add_edge(
        src: str,
        dst: str,
        kappa: Any,
        phi: Any,
        T: Any,
        origin: str,
    ) -> None:
        key = (src, dst, origin)
        if key in seen_e:
            return
        seen_e.add(key)
        edges_out.append(
            {
                "src": src,
                "dst": dst,
                "kappa": kappa,
                "phi": phi,
                "T": T,
                "origin": origin,
                "legal": walkable,
            }
        )

    for c in ast["couplings"]:
        add_edge(
            c["src"],
            c["dst"],
            c["kappa"],
            c["phi"],
            c["T"],
            "coupling",
        )

    for st in candidate_states:
        sid = st["state_id"]
        kappa, phi, T = _structural_kappa_phi_T(basin_id, basin_id, ast["couplings"])
        add_edge(basin_id, sid, kappa, phi, T, "v_link")
        add_edge(sid, basin_id, kappa, phi, T, "v_link")

    # Optional send_path edges from phase-two send (record path; legality under gate)
    for entry in phase_two_log:
        if entry.get("op") == "send":
            # Actor structural → state, state → dst (effect path, not free teleport)
            add_edge(
                entry["src"],
                entry["state"],
                0.5,
                0.0,
                1.0,
                "send_path",
            )
            add_edge(
                entry["state"],
                entry["dst"],
                0.5,
                0.0,
                1.0,
                "send_path",
            )
            # Re-apply gate legality (add_edge used walkable already)
            for e in edges_out:
                if e["origin"] == "send_path":
                    if gate_outcome == "hold":
                        e["legal"] = False
                    elif gate_outcome == "reverse":
                        e["legal"] = False  # send recoils; path not free progress
                    else:
                        e["legal"] = True

    current_locus = _place_actor_locus(combatants, basin_id, structural_ids)
    actors = []
    for cid in combatants:
        actors.append({"id": cid, "locus": cid if cid in structural_ids else current_locus, "status": "active"})
    if not actors:
        actors.append({"id": "actor", "locus": current_locus, "status": "active"})

    # Optional non-authoritative display layout (circle)
    positions: Dict[str, Dict[str, float]] = {}
    ids_layout = [n["id"] for n in nodes_out]
    n_lay = max(1, len(ids_layout))
    for i, nid in enumerate(ids_layout):
        ang = 2.0 * math.pi * i / n_lay
        positions[nid] = {
            "x": round(math.cos(ang), 6),
            "y": round(math.sin(ang), 6),
        }

    state: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "hal_profile": HAL_PROFILE_ATTRACTOR,
        "language_authority": LANGUAGE_AUTHORITY,
        "team_expansion": TEAM_EXPANSION,
        "rule_stamp": RULE_STAMP_ATTRACTOR,
        "program_id": program_id,
        "seed": disc_seed,
        "phase": "playing",
        "graph": {
            "directed": True,
            "note": "rules surface; layout is display-only",
        },
        "nodes": nodes_out,
        "edges": edges_out,
        "vocabulary": {
            "id": vocabulary["id"],
            "status": vocabulary["status"],
            "states": vocabulary["states"],
        },
        "gate": {
            "focus_pair": focus_pair,
            "T_obs": t_obs,
            "outcome": gate_outcome,
        },
        "current_locus": current_locus,
        "actors": actors,
        "slice": {
            "S": S,
            "S_max": S_MAX,
            "note": "coherence step index, not free Z / not Euclidean axis",
        },
        "clock": {
            "discovery_closed": True,
            "round": 1,
            "turn_actor": actors[0]["id"],
        },
        "display_layout": {
            "optional": True,
            "positions": positions,
            "note": "human drawing only; not the rule surface",
        },
        "receipts_tip": tip,
        "claim_boundary": CLAIM_BOUNDARY,
        "phase_two_log": phase_two_log,
    }

    _assert_invariants_attractor(state)
    return state


def _assert_invariants_projected(state: Dict[str, Any]) -> None:
    vstat = state["vocabulary"]["status"]
    if vstat not in ("resolved", "partial", "pending", "invalidated"):
        raise AssertionError(f"bad vocabulary.status: {vstat}")
    outcome = state["gate"]["outcome"]
    if outcome not in ("proceed", "hold", "reverse"):
        raise AssertionError(f"gate.outcome must be SymLan gate, got {outcome!r}")
    if state["slice"]["S"] < 0:
        raise AssertionError("slice.S must be >= 0")
    cells = [(n["id"], (n["cell"]["x"], n["cell"]["y"])) for n in state["nodes"]]
    positions = [c for _, c in cells]
    if len(positions) != len(set(positions)):
        raise AssertionError("nodes must occupy distinct cells (v0.1 no stacking)")


def _assert_invariants_attractor(state: Dict[str, Any]) -> None:
    """Attractor-Graph HAL §6.1."""
    if state.get("hal_profile") != HAL_PROFILE_ATTRACTOR:
        raise AssertionError("hal_profile must be attractor_graph id")
    vstat = state["vocabulary"]["status"]
    if vstat not in ("resolved", "partial", "pending", "invalidated"):
        raise AssertionError(f"bad vocabulary.status: {vstat}")
    outcome = state["gate"]["outcome"]
    if outcome not in ("proceed", "hold", "reverse"):
        raise AssertionError(f"gate.outcome must be SymLan gate, got {outcome!r}")
    node_ids = {n["id"] for n in state["nodes"]}
    locus = state.get("current_locus")
    if locus is not None and locus not in node_ids:
        raise AssertionError(f"current_locus {locus!r} not in nodes")
    if vstat != "resolved" and vstat != "partial":
        # pending: no V-id as locus
        for n in state["nodes"]:
            if n.get("kind") == "vocab_state" and locus == n["id"]:
                raise AssertionError("V-locus not allowed before resolve")
    for e in state.get("edges") or []:
        if e["src"] not in node_ids or e["dst"] not in node_ids:
            raise AssertionError(f"edge endpoints not in nodes: {e}")
    if state["slice"]["S"] < 0:
        raise AssertionError("slice.S must be >= 0")
    # display_layout must not be required for legality — just present or absent
    if "board" in state:
        raise AssertionError("attractor_graph PlayableState must not require Cartesian board")


# ---------------------------------------------------------------------------
# Self-check + demo runner
# ---------------------------------------------------------------------------

def self_check(state: Dict[str, Any]) -> List[str]:
    """Projected-3-space self-check (existing demo)."""
    failures: List[str] = []
    if state["vocabulary"]["status"] != "resolved":
        failures.append(
            f"vocabulary.status expected 'resolved', got {state['vocabulary']['status']!r}"
        )
    by_id = {n["id"]: n for n in state["nodes"]}
    for required in ("Alpha", "Beta", "basin_center"):
        if required not in by_id:
            failures.append(f"missing node {required!r}")
    if "Alpha" in by_id and "Beta" in by_id and "cell" in by_id["Alpha"]:
        ca = (by_id["Alpha"]["cell"]["x"], by_id["Alpha"]["cell"]["y"])
        cb = (by_id["Beta"]["cell"]["x"], by_id["Beta"]["cell"]["y"])
        if ca == cb:
            failures.append(f"Alpha and Beta must occupy distinct cells; both at {ca}")
    outcome = state["gate"]["outcome"]
    if outcome not in ("proceed", "hold", "reverse"):
        failures.append(f"illegal gate outcome: {outcome!r}")
    if state["hal_profile"] != HAL_PROFILE:
        failures.append("hal_profile mismatch")
    if state.get("board", {}).get("width") != DEFAULT_WIDTH or state.get("board", {}).get(
        "height"
    ) != DEFAULT_HEIGHT:
        failures.append("board size not HAL default 7x5")
    return failures


def self_check_attractor(state: Dict[str, Any]) -> List[str]:
    """Attractor-graph self-check (HAL §6.1 + example norms)."""
    failures: List[str] = []
    if state.get("hal_profile") != HAL_PROFILE_ATTRACTOR:
        failures.append(f"hal_profile expected {HAL_PROFILE_ATTRACTOR!r}")
    if state["vocabulary"]["status"] != "resolved":
        failures.append("vocabulary not resolved")
    kinds = {n["id"]: n.get("kind") for n in state["nodes"]}
    for sid in ("S1", "Sj"):
        if sid not in kinds:
            failures.append(f"missing V-locus {sid!r}")
        elif kinds[sid] != "vocab_state":
            failures.append(f"{sid} kind must be vocab_state")
    for sid in ("Alpha", "basin_center"):
        if sid not in kinds:
            failures.append(f"missing structural {sid!r}")
        elif kinds[sid] != "structural":
            failures.append(f"{sid} kind must be structural")
    origins = {(e["src"], e["dst"], e["origin"]) for e in state.get("edges") or []}
    if ("Alpha", "basin_center", "coupling") not in origins:
        failures.append("missing coupling edge Alpha→basin_center")
    if ("basin_center", "S1", "v_link") not in origins:
        failures.append("missing v_link basin_center→S1")
    if ("S1", "basin_center", "v_link") not in origins:
        failures.append("missing v_link S1→basin_center")
    if state.get("current_locus") not in kinds:
        failures.append("current_locus not a graph vertex")
    if state["gate"]["outcome"] not in ("proceed", "hold", "reverse"):
        failures.append("illegal gate")
    if "board" in state:
        failures.append("unexpected Cartesian board on attractor state")
    try:
        _assert_invariants_attractor(state)
    except AssertionError as e:
        failures.append(str(e))
    return failures


def run_demo() -> int:
    """Materialize projected §7 example; print summary + digests; run self-check."""
    state = materialize(EXAMPLE_PROGRAM, profile=PROFILE_PROJECTED)
    canon = canonical_json(state)
    state_digest = sha256_hex(canon)

    board = state["board"]
    print("=== Materializer v0.1 — projected_3space §7 ===")
    print(f"profile:           {state['hal_profile']}")
    print(f"board size:        {board['width']} x {board['height']} ({board['adjacency']})")
    print("node placements:")
    for n in state["nodes"]:
        c = n["cell"]
        print(
            f"  {n['id']:14} cell=({c['x']},{c['y']})  "
            f"kappa={n['kappa']}  phi={n['phi']}  T={n['T']}  status={n['status']}"
        )
    print(f"vocabulary status: {state['vocabulary']['status']}")
    print(
        f"  states: {', '.join(s['state_id'] for s in state['vocabulary']['states'])}"
    )
    print(
        f"current gate:      {state['gate']['outcome']}  "
        f"(T_obs={state['gate']['T_obs']}, pair={state['gate']['focus_pair']})"
    )
    print(f"slice S:           {state['slice']['S']} (S_max={state['slice']['S_max']})")
    print(f"seed:              {state['seed']}")
    print(f"PlayableState SHA-256 (canonical JSON): {state_digest}")

    fails = self_check(state)
    if fails:
        print("SELF-CHECK FAIL (projected):")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(
        "SELF-CHECK PASS (projected): resolved V; distinct Alpha/Beta; "
        "gate in {proceed, hold, reverse}"
    )
    return 0


def run_demo_attractor() -> int:
    """Materialize attractor-graph HAL §7 example; graph summary + digest."""
    state = materialize(EXAMPLE_PROGRAM_ATTRACTOR, profile=PROFILE_ATTRACTOR)
    canon = canonical_json(state)
    state_digest = sha256_hex(canon)

    print("=== Materializer v0.1 — attractor_graph §7 ===")
    print(f"profile:           {state['hal_profile']}")
    print(f"vocabulary:        {state['vocabulary']['status']}")
    print(
        f"  states: {', '.join(s['state_id'] for s in state['vocabulary']['states'])}"
    )
    print(f"current_locus:     {state['current_locus']}")
    print(
        f"gate:              {state['gate']['outcome']}  "
        f"(T_obs={state['gate']['T_obs']})"
    )
    print(f"slice S:           {state['slice']['S']}")
    print("vertices:")
    for n in state["nodes"]:
        print(
            f"  {n['id']:14} kind={n['kind']:12} "
            f"κ={n['kappa']} φ={n['phi']} T={n['T']}"
        )
    print("edges:")
    for e in state["edges"]:
        print(
            f"  {e['src']:14} → {e['dst']:14}  "
            f"origin={e['origin']:10} legal={e['legal']}"
        )
    print(f"seed:              {state['seed']}")
    print(f"receipts_tip:      {state['receipts_tip']}")
    print(f"PlayableState SHA-256 (canonical JSON): {state_digest}")

    fails = self_check_attractor(state)
    if fails:
        print("SELF-CHECK FAIL (attractor):")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(
        "SELF-CHECK PASS (attractor): V-loci + couplings + v_links; "
        "gate legal; no Cartesian board"
    )
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help"):
        print("Usage: materializer_v0_1.py [--attractor] [--json] [--both]")
        print("  Default: projected_3space §7 example.")
        print("  --attractor  run attractor_graph §7 example")
        print("  --both       run both profiles")
        print("  --json       print canonical JSON after summary")
        return 0

    want_attr = "--attractor" in argv
    want_both = "--both" in argv
    want_json = "--json" in argv

    rc = 0
    if want_both:
        rc = run_demo()
        if rc == 0:
            print()
            rc = run_demo_attractor()
        if want_json and rc == 0:
            print(canonical_json(materialize(EXAMPLE_PROGRAM_ATTRACTOR, profile=PROFILE_ATTRACTOR)))
        return rc

    if want_attr:
        rc = run_demo_attractor()
        if want_json and rc == 0:
            print(
                canonical_json(
                    materialize(EXAMPLE_PROGRAM_ATTRACTOR, profile=PROFILE_ATTRACTOR)
                )
            )
        return rc

    rc = run_demo()
    if want_json and rc == 0:
        print(canonical_json(materialize(EXAMPLE_PROGRAM, profile=PROFILE_PROJECTED)))
    return rc


if __name__ == "__main__":
    sys.exit(main())

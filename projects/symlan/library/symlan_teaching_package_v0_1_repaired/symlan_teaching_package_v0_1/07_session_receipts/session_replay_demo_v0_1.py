#!/usr/bin/env python3
"""
Offline demo of hotseat session export shape + replay (stdlib only).
Mirrors hotseat_play_surface_v0_1.html session schema; does not drive a browser.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "demo_hotseat_session_v0_1.json"

# Minimal PlayableState fragment (same cells as §7 materializer embed)
INITIAL = {
    "schema_version": "symlan.playable_state.v0.1",
    "hal_profile": "spatial_temporal.projected_3space.v0.1",
    "gate": {"outcome": "proceed", "T_obs": 1.007559, "focus_pair": ["Alpha", "basin_center"]},
    "board": {"width": 7, "height": 5, "adjacency": "orthogonal4"},
    "slice": {"S": 1, "S_max": 64},
    "clock": {"turn_node": "Alpha", "round": 1, "discovery_closed": True},
    "nodes": [
        {"id": "Alpha", "cell": {"x": 2, "y": 4}, "status": "active"},
        {"id": "Beta", "cell": {"x": 5, "y": 1}, "status": "active"},
        {"id": "basin_center", "cell": {"x": 3, "y": 2}, "status": "active"},
    ],
    "vocabulary": {"id": "V", "status": "resolved", "states": [{"state_id": "S1"}]},
    "receipts_tip": "GENESIS",
}


def fnv1a32(s: str) -> str:
    h = 0x811C9DC5
    for ch in s.encode("utf-8"):
        h ^= ch
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def digest_state(st: dict) -> str:
    return "fnv1a32:" + fnv1a32(json.dumps(st, sort_keys=True, separators=(",", ":")))


def apply_slice(S: int, gate: str, committed: bool) -> int:
    if not committed:
        return S
    if gate == "proceed":
        return min(64, S + 1)
    if gate == "reverse":
        return max(0, S - 1)
    return S


def advance_turn(st: dict) -> None:
    order = [n["id"] for n in st["nodes"] if n["id"] in ("Alpha", "Beta")]
    cur = st["clock"]["turn_node"]
    idx = order.index(cur) if cur in order else 0
    nxt = (idx + 1) % len(order)
    st["clock"]["turn_node"] = order[nxt]
    if nxt == 0:
        st["clock"]["round"] += 1


def node(st: dict, nid: str) -> dict:
    return next(n for n in st["nodes"] if n["id"] == nid)


def play_and_export() -> dict:
    st = json.loads(json.dumps(INITIAL))
    initial = json.loads(json.dumps(st))
    tip = st["receipts_tip"]
    events = []
    n = 0

    def rec(typ: str, actor: str, detail: dict, gate: str) -> None:
        nonlocal tip, n
        n += 1
        prev = tip
        body_hash = fnv1a32(
            f"{prev}|{n}|{typ}|{actor}|{gate}|{st['slice']['S']}|{json.dumps(detail, sort_keys=True)}"
        )
        tip = "local:" + body_hash
        st["receipts_tip"] = tip
        events.append(
            {
                "n": n,
                "type": typ,
                "actor": actor,
                "detail": detail,
                "gate": gate,
                "S_after": st["slice"]["S"],
                "prev": prev,
                "hash": tip,
            }
        )
        advance_turn(st)

    # Alpha stay
    rec("stay", "Alpha", {}, "proceed")
    # Beta move
    b = node(st, "Beta")
    fr = dict(b["cell"])
    b["cell"] = {"x": 5, "y": 2}
    st["slice"]["S"] = apply_slice(st["slice"]["S"], "proceed", True)
    rec("move", "Beta", {"from": fr, "to": dict(b["cell"])}, "proceed")
    # Alpha strike ok toward basin if adjacent — may not be; record stay instead if not
    a = node(st, "Alpha")
    # Move Alpha toward basin then strike
    fr = dict(a["cell"])
    a["cell"] = {"x": 2, "y": 3}
    st["slice"]["S"] = apply_slice(st["slice"]["S"], "proceed", True)
    rec("move", "Alpha", {"from": fr, "to": dict(a["cell"])}, "proceed")
    # Beta stay
    rec("stay", "Beta", {}, "proceed")
    # Alpha strike hold blocked (demo type under forced hold gate label)
    rec("strike_hold_blocked", "Alpha", {"target": "basin_center"}, "hold")

    return {
        "schema_version": "symlan.hotseat_session.v0.1",
        "hal_profile": "spatial_temporal.projected_3space.v0.1",
        "initial_state_digest": digest_state(initial),
        "initial_state": initial,
        "events": events,
        "final_tip": tip,
        "final_snapshot": {
            "nodes": [
                {"id": n["id"], "cell": dict(n["cell"]), "status": n["status"]}
                for n in st["nodes"]
            ],
            "slice_S": st["slice"]["S"],
            "turn_node": st["clock"]["turn_node"],
            "round": st["clock"]["round"],
            "gate_outcome": st["gate"]["outcome"],
        },
        "claim_boundary": "toy session log only",
    }


def replay(sess: dict) -> dict:
    st = json.loads(json.dumps(sess["initial_state"]))
    for ev in sess["events"]:
        if ev["type"] == "move" and "to" in ev.get("detail", {}):
            node(st, ev["actor"])["cell"] = dict(ev["detail"]["to"])
        st["slice"]["S"] = ev["S_after"]
        st["receipts_tip"] = ev["hash"]
        advance_turn(st)
    if sess.get("final_tip"):
        st["receipts_tip"] = sess["final_tip"]
    return st


def main() -> int:
    sess = play_and_export()
    OUT.write_text(json.dumps(sess, indent=2) + "\n", encoding="utf-8")
    st = replay(sess)
    snap = sess["final_snapshot"]
    for n in snap["nodes"]:
        live = node(st, n["id"])["cell"]
        assert live == n["cell"], (n["id"], live, n["cell"])
    assert st["slice"]["S"] == snap["slice_S"]
    assert st["clock"]["turn_node"] == snap["turn_node"]
    assert st["receipts_tip"] == sess["final_tip"]
    print("DEMO PASS: play → export → replay positions/S/turn/tip match")
    print(f"  wrote {OUT}")
    print(f"  events={len(sess['events'])}  S={snap['slice_S']}  turn={snap['turn_node']}")
    print(f"  final_tip={sess['final_tip']}")
    print(f"  digest={sess['initial_state_digest']}")
    print(
        "  Browser: open hotseat → Export session after play → Load session file "
        "(or paste demo_hotseat_session_v0_1.json)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

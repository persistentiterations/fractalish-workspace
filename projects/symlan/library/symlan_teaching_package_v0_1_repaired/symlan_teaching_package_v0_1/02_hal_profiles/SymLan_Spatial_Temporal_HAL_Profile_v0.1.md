# SymLan Spatial/Temporal HAL Profile v0.1

**Title:** SymLan_Spatial_Temporal_HAL_Profile_v0.1  
**Status:** Draft contract (not a runtime, not a game build)  
**Date:** 2026-07-27  
**Authorities:**  
- SymLan Programming Language **v0.2.6** (teaching / language canonical)  
- SymLan Core Language **v0.3** team expansion (AI package; does not override v0.2.6 where they conflict)  
**Operators:** James Allen Clow / Melissa Ellen Clow  
**Audience:** Language, runtime, and Eracii-style game-space implementers  

**One-line purpose:**  
Define how a SymLan program **earns and constrains a playable arena geometry** without claiming literal 4-space rendering, consciousness, rights, or production readiness.

---

## 1. Purpose and scope

### 1.1 Purpose

This profile is the **missing HAL (Hardware Abstraction Layer) contract** between:

1. A **SymLan source program** (arena → discovery → resolve → phase-two ops), and  
2. A **playable game space** (e.g. future Eracii-style combat, museum arenas, training grounds).

It answers: *When a SymLan program runs under a spatial/temporal game-space backend, what geometry is produced, what may be navigated, and how do κ, φ, T, V, and ternary gates bind that geometry?*

### 1.2 In scope (v0.1)

- Exactly **one** starter geometry (chosen below).  
- Explicit mappings from core SymLan constructs to geometric meaning.  
- Rules for discovery → resolution → navigable space.  
- Effects of `branch on T` on **legal moves**, **visibility**, and **time progression**.  
- A **minimal** `PlayableState` schema (conceptual JSON shape only).  
- One worked SymLan example and the geometry it **must** produce.  
- Non-conflation of SymLan gates with Cognitive Basin action states.  
- Claim boundary and open questions for v0.2.

### 1.3 Out of scope (v0.1)

- Materializer implementation, renderer, networking, or UI.  
- Full SymLan compiler, physical substrate HAL (BZ, VO₂, Hopfield), or Π_A+ execution.  
- Literal 4-spatial-dimension meshes or engines.  
- Consciousness, sentience, rights, personhood, or legal standing.  
- Production matchmaking, anti-cheat, or ranked multiplayer.  
- Freezing Natural Math v5 or Eracii combat balance as part of this profile.

### 1.4 Design law (inherited)

> The programmer specifies the arena. The substrate earns the vocabulary.  
> Symbols are usable only after resolution. HOLD is legal. False closure is not.

Game-space consequence: **navigable structure is not a free level-design asset list.** It is constrained—and partially *earned*—by discovery and resolution under declared κ, φ, T.

---

## 2. Chosen starter geometry (v0.1)

### 2.1 Choice

**Projected 3-space:**  
**two spatial axes (X, Y)** on a finite discrete board, plus **one coherence/time slice axis (S)** derived from SymLan coherence **T** and phase-two gate outcomes—not a third free-flight spatial axis.

### 2.2 One-sentence justification

Projected 3-space keeps Eracii-style combat **human-readable on a 2D board** while making SymLan’s coherence dimension **play-consequential** (visibility, legal moves, and time advance) without claiming literal 4D geometry or unreadable multi-space UX.

### 2.3 Rejected for v0.1 (deferred, not discarded)

| Option | Why not v0.1 |
|--------|----------------|
| Attractor graph as primary geometry | Excellent for pure V-navigation; weaker default for Eracii-style board combat readability. |
| Timeline branches as primary geometry | Strong for HOLD/reverse pedagogy; risks conflating “time travel” with SymLan reverse without a spatial combat base. |

Both remain **v0.2 candidates** as alternate HAL profiles, not as silent replacements of this contract.

### 2.4 Notation

| Symbol | Meaning in this profile |
|--------|-------------------------|
| **X, Y** | Discrete spatial coordinates on a finite board |
| **S** | Coherence/time **slice index** (integer); not a continuous free Z-axis for flight |
| **Cell** | Address `(x, y)` at the current slice `s` |
| **Occupant** | A SymLan `node` bound to a cell (or multi-cell footprint later) |
| **Edge** | Optional navigable adjacency; may be gated by T / HOLD |

**V (vocabulary)** is **not** a fourth spatial axis. V is the set of **earned symbols** that may label basins, tokens, and allowed operations on the projected space after resolution.

---

## 3. Mapping table: SymLan construct → geometric meaning

| SymLan construct | Geometric / temporal meaning in Projected 3-space HAL |
|------------------|--------------------------------------------------------|
| `node A, B, …` | Declares **occupiable agents / units / loci**. Before discovery: handles only (pending placement rules). After bind: each node has a cell `(x,y)` and may carry κ/φ/T local readouts. |
| `node` array form (if used later) | Reserved for multi-cell or multi-instance units; **v0.1 uses singleton nodes only**. |
| `A -> B [κ, φ, T]` | Declares a **directed coupling constraint** between nodes. Geometrically: influences **adjacency cost**, **line-of-effect eligibility**, and **default coherence band** between A and B—not automatic free movement. κ scales interaction strength; φ biases preferred relative placement / timing offset; T sets the coherence target for ternary evaluation between that pair (or pair vs arena). |
| `A <-> B […]` | Bidirectional coupling: same as two directed edges with shared or mirrored parameters (HAL must record directionality explicitly). |
| `vocab V = register(target, θ:, features:)` | Declares **pending vocabulary** to be earned from the arena substrate (sim or physical). Geometrically: V will label **basins / tokens** that can mark cells, edges, or operations after resolve—not pre-authored skill IDs. |
| `features: 7D` | Teaching feature pack (v0.2.6). HAL records which feature pack produced V; geometry materialization may use a subset (e.g. Count, PhaseRel, Transition) for slice or edge rules. |
| `features: PEFP(k:)` / glyph packs | **Out of primary path for v0.1 board combat**; if present, treat as alternate readout of the same basins, not a second space. |
| `run discovery for DURATION [seed:]` | Executes **Phase 1**: substrate/sim settles; observations collected. Geometrically: **initial layout + V candidates** are produced under seed + rule stamp. No phase-two navigation commits until resolve. |
| `after resolve V { … }` | **Hard phase boundary.** Only here may navigable commitments that *use* earned symbols (send/expect/branch that depend on V) execute. Spatial moves that are pure geometry may still be HAL-defined; **symbol-using combat ops require resolve**. |
| `send node[S] -> target` | Transmits an **earned token/state** S toward a target node/channel. Geometrically: a **directed effect along a legal line-of-effect** (adjacency or coupling-allowed path), subject to gate outcome. |
| `expect node[S] within …, fidelity:` | Asserts a **predicted state occupancy / token acceptance** within a time window; failure is evidence, not silent fudge. |
| `inject … into channel` | Host- or bus-bound request (Bolt-On spirit): geometry may show a pending delivery; **does not seize host authority**. |
| `mutate … dim: …` | Alters a token feature; may degrade fidelity of later expects; geometry may show “scar” on the source basin/cell. |
| `branch on T(a, b) { > : …; ≈ : …; < : … }` | Evaluates **coherence relation** for pair `(a,b)` (or HAL-defined proxy). **Must** have three arms. Maps to **proceed / hold / reverse** gates that change legal moves, visibility, and time (see §5). |
| `query V.entropy` / capacity | Meta-readouts of vocabulary; may surface as HUD metrics, not new cells. |
| Receipts / checkpoints (runtime discipline) | Every geometry-changing or symbol-using step should be **receiptable** (CONFIGURATOR/Bolt-On discipline). Profile requires *that* receipts exist; schema details live in runtime docs. |

### 3.1 What κ, φ, T mean on the board (v0.1 defaults)

| Dim | Board-facing default (must be documented by any implementer if overridden) |
|-----|-----------------------------------------------------------------------------|
| **κ** | Interaction *strength*: raises strike/effect magnitude or coupling range cost; does **not** alone grant omniscience. |
| **φ** | Relative *phase / timing bias*: may rotate preferred approach directions or delay windows; v0.1 may treat φ as display + mild adjacency preference only. |
| **T** | *Coherence target / observed coherence proxy* for ternary gates; drives slice S and gate band (proceed/hold/reverse). |
| **V** | *Earned symbol set* after discovery; labels basins/tokens usable in phase two—not a free spatial axis. |

---

## 4. Discovery → resolution → navigable space rules

### 4.1 Lifecycle (mandatory order)

```text
1. Parse & type-check SymLan source
2. Instantiate empty PlayableState (declared nodes, pending V)
3. run discovery  →  produce DiscoveryPacket
4. resolve V      →  bind Vocabulary<resolved>
5. Materialize navigable projection from (layout + V + couplings)
6. after resolve  →  phase-two ops may use earned symbols
7. Receiptize / optional checkpoint
```

Skipping resolve before symbol-using ops is a **PendingSymbolUse** (language error), not a soft warning.

### 4.2 Discovery rules (geometry)

Under this HAL profile, **discovery must determine**:

1. **Initial placement** of each declared `node` onto discrete cells `(x,y)` within declared board bounds (or a documented placement algorithm driven by seed).  
2. **Candidate basins** for vocabulary registration (feature observations).  
3. A **seeded, deterministic** observation stream: same source + seed + rule/HAL version ⇒ same discovery packet (within declared sim precision).

Discovery **must not**:

- Invent nodes not declared in source.  
- Promote programmer-named free strings as V entries without binding to observed basins.  
- Advance match **round time** as if phase-two combat commits had occurred (discovery may use its own duration clock, separate from play rounds).

### 4.3 Resolution rules

Resolution binds `Vocabulary<pending>` → `Vocabulary<resolved>`:

- Each earned state id (e.g. `S1`, `Sj`) maps to a basin record with provenance (run id, feature snapshot, optional glyph).  
- Partial resolution (insufficient states) is allowed only if the language/runtime surfaces **partial** status; HAL must not pretend full V.  
- After resolution, **navigable space is locked** for the epoch: cell graph + V labels become the playable projection until an explicit re-discovery / invalidation epoch (v0.2).

### 4.4 Navigable space rules (post-resolve)

A cell is **navigable** for a node if all hold:

1. Coordinates in board bounds.  
2. Not occupied by another node (v0.1: no stacking), unless HAL defines pass-through (default: no).  
3. Edge to destination is allowed under current **gate state** for the acting node (§5).  
4. If the move is justified by a **V-dependent** ability, that symbol must be resolved and not invalidated.

**Visibility (v0.1 defaults):**

| Condition | Visibility |
|-----------|------------|
| Gate **proceed** | Full board occupancy of opponent units; V HUD visible |
| Gate **hold** | Own unit + adjacent cells only; V HUD visible but dimmed; no symbol-using strikes |
| Gate **reverse** | Full occupancy visible; self-effects emphasized; outbound strike suppressed or reflected per §5 |

These are **profile defaults**. Implementations may refine numbers but must not invert the honesty of HOLD (wait is legal).

### 4.5 Spatial board defaults (v0.1)

| Parameter | Default | Notes |
|-----------|---------|-------|
| Width × height | 7 × 5 | Eracii-Duel-readable; overridable by HAL config, not by silent magic |
| Adjacency | Orthogonal (4-dir) | No diagonals in v0.1 unless coupling explicitly unlocks |
| Max units | = number of declared combatant nodes | |
| Seed | From `run discovery … seed:` if present | Required for competitive determinism |

---

## 5. How ternary gates affect legal moves / visibility / time

### 5.1 Gate evaluation

`branch on T(a, b)` evaluates a **coherence proxy** `T_obs` for pair `(a,b)` (HAL-defined measurement; teaching default: function of declared T targets and current κ alignment).

Mandatory arms and **SymLan gate** outcomes:

| Arm (teaching form) | Gate | Name |
|---------------------|------|------|
| over-coupled (`>` band) | **reverse** | Over-constrained / unsafe commit |
| near target (`≈` / `~` band) | **proceed** | Usable coherence |
| under-coupled (`<` band) | **hold** | Insufficient resolution; wait is legal |

Compiler/profile rule: **three arms required**. Incomplete ternary is invalid SymLan.

### 5.2 Legal moves

| Gate | Movement | Strike / send (symbol-using) |
|------|----------|------------------------------|
| **proceed** | Standard orthogonal step into empty navigable cell | Allowed along legal line-of-effect; magnitude may scale with κ |
| **hold** | Step still allowed **or** restricted to stay/adjacent only (default: **adjacent-only or stay**) | **Blocked** — no commit of damaging/send that pretends resolution |
| **reverse** | Step allowed | Strike/send **reflects** as self-cost or cancel+scar (default: **self-recoil**, no free opponent damage) |

v0.1 default for combat prototypes: **hold blocks strike/send; reverse converts strike to self-recoil; proceed allows normal strike.**

### 5.3 Visibility

As in §4.4. HOLD must not be implemented as “hide the fact that you are waiting”; it may reduce **information range**, not erase the gate’s existence from receipts.

### 5.4 Time

Projected 3-space treats **time** as:

1. **Discovery duration** — wall/sim time for Phase 1 only.  
2. **Play rounds / turns** — discrete combat time after resolve.  
3. **Slice index S** — integer coherence/time slice; advances on successful phase-two **proceed** commits; **does not advance** on **hold**; **may decrement or scar** on **reverse** (v0.1 default: reverse does not rewind board positions; it applies recoil and may decrement S by 1 floor 0).

```text
proceed  →  S := S + 1  (and turn/round clock advances per game rules)
hold     →  S unchanged; turn may still pass or wait (game rule); no false strike
reverse  →  S := max(0, S - 1); apply reverse effects; no free offensive progress
```

**Critical:** **reverse is not general time travel** and **not** Cognitive Basin `RETRACT`. It is a **SymLan gate** with local geometric/temporal cost.

---

## 6. Minimal PlayableState schema (conceptual)

Not an implementation—only the fields a materializer **must** be able to populate from SymLan + this HAL.

```json
{
  "schema_version": "symlan.playable_state.v0.1",
  "hal_profile": "spatial_temporal.projected_3space.v0.1",
  "language_authority": "symlan.v0.2.6",
  "team_expansion": "symlan.core.v0.3",
  "rule_stamp": "string — HAL + game rule version",
  "program_id": "sha256 of SymLan source",
  "seed": "string | null",
  "phase": "declared | discovering | resolved | playing | closed",
  "board": {
    "width": 7,
    "height": 5,
    "adjacency": "orthogonal4"
  },
  "slice": {
    "S": 0,
    "S_max": 64,
    "note": "coherence/time slice index, not free Z flight"
  },
  "nodes": [
    {
      "id": "Alpha",
      "cell": { "x": 0, "y": 2 },
      "kappa": 0.35,
      "phi": 0.0,
      "T": 1.0,
      "status": "active | held | eliminated"
    }
  ],
  "couplings": [
    {
      "src": "Alpha",
      "dst": "basin_center",
      "kappa": 0.5,
      "phi": "pi/4",
      "T": 1.0
    }
  ],
  "vocabulary": {
    "id": "V",
    "status": "pending | resolved | partial | invalidated",
    "states": [
      {
        "state_id": "S1",
        "basin_ref": "string",
        "glyph_or_tag": "optional short id",
        "provenance": "discovery_run_id"
      }
    ]
  },
  "gate": {
    "focus_pair": ["Alpha", "basin_center"],
    "T_obs": 1.0,
    "outcome": "proceed | hold | reverse"
  },
  "navigability": {
    "edges": [
      { "from": { "x": 0, "y": 2 }, "to": { "x": 1, "y": 2 }, "allowed": true }
    ],
    "note": "may be implicit from adjacency + gate rules"
  },
  "clock": {
    "discovery_closed": true,
    "round": 1,
    "turn_node": "Alpha"
  },
  "receipts_tip": "sha256:… or GENESIS",
  "claim_boundary": "toy/playable projection only"
}
```

### 6.1 Invariants on PlayableState

1. If `vocabulary.status != resolved` (and not partial with explicit warnings), phase-two symbol ops are illegal.  
2. `gate.outcome` is always one of `proceed|hold|reverse` when evaluated.  
3. Every mutation of cells, V, gate, or clock should be appendable to a receipt chain (tip updates).  
4. `slice.S` never represents a fourth free spatial dimension.

---

## 7. Example: SymLan program → required geometry

### 7.1 Program (teaching subset, ~20 lines)

```symlan
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
```

*(Book form may use κ/φ/θ/≈; ASCII aliases are allowed for tooling. Semantics identical.)*

### 7.2 Geometry this program **must** produce (normative for v0.1 HAL)

After successful discovery + resolve, any compliant materializer **must** yield a PlayableState such that:

1. **Board** exists with finite discrete **X,Y** (default 7×5 unless config overrides **and** records the override in `rule_stamp`).  
2. **Nodes** `Alpha`, `Beta`, `basin_center` exist as handles; combatants occupy **distinct cells**; `basin_center` occupies a designated center or registered cell.  
3. **Couplings** Alpha→center and Beta→center are recorded with the given κ/φ/T.  
4. **V** is `resolved` (or explicit partial); at least one earned state usable as `S1` (and `Sj` if aliasing is used) with provenance to the discovery seed `hal-profile-v0.1-demo`.  
5. **No** phase-two `send` is considered to have occurred before resolve.  
6. Evaluating `branch on T(Alpha, basin_center)` yields exactly one of proceed/hold/reverse and updates **legal moves / visibility / slice S** per §5.  
7. **Slice S** starts at 0 (or documented initial) and only advances on proceed commits as defined.  
8. A **receipt tip** exists covering discovery, resolution, and any executed phase-two ops.

If any of (1)–(8) fails, the HAL is **non-conformant** to this profile, even if a pretty board is drawn.

---

## 8. Non-conflation rules (mandatory)

| Namespace | States | Allowed role in this HAL |
|-----------|--------|---------------------------|
| **SymLan gate** | PROCEED / HOLD / REVERSE | Legal moves, visibility, slice S, strike/send commit rules |
| **Cognitive Basin action** | EXTEND / HOLD / RETRACT | **Not** used as board gates in v0.1; governance/epistemic stack only |
| **Cognitive Basin epistemic** | SUPPORTED / UNRESOLVED / CONTRADICTED | Evidence about claims, not cell adjacency |
| **Natural Math process** | EXTEND / SENSE / RESTRICT | Substrate/process backend mapping only via **explicit adapter table**, never silent rename |

**Hard rules:**

1. SymLan **HOLD** must not be rewritten as Basin **HOLD** in code paths or UI copy without a visible namespace label.  
2. SymLan **REVERSE** must not be marketed as “undo history” or Basin **RETRACT**.  
3. Natural Math **RESTRICT** is not a drop-in for reverse.  
4. Adapter maps, if any, are versioned and receipted; they are not “the same enum.”

---

## 9. Claim boundary (one page)

| **Is** | **Is not** |
|--------|------------|
| A **HAL profile contract** for generating playable projected geometry from SymLan | A full game, renderer, netcode, or materializer implementation |
| Bound by **SymLan v0.2.6** + **Core v0.3** teaching/expansion authority | A replacement of the v0.2.6 language book |
| **Projected 3-space**: 2 spatial axes + coherence/time **slice S** | Literal **4-spatial-dimension** combat or engine requirement |
| Mapping of nodes, couplings [κ,φ,T], discovery, `after resolve V`, `branch on T` into board geometry and gates | Proof that κ/φ/T are unique physical constants of all substrates |
| Requirement that **V is earned** before symbol-using play | Permission to hardcode free skill names as V |
| Ternary gates affecting **moves, visibility, and time slice** | Binary-only combat with cosmetic “hold” labels |
| Compatible with **receipt / replay** discipline (CONFIGURATOR, Bolt-On) | A finished forensic PKI or production anti-cheat system |
| Suitable on-ramp for **future Eracii-style** arenas | Frozen Eracii Duel v0.15 ruleset or balance document |
| Explicit **non-conflation** of SymLan gates vs Basin/NM states | A merge of all HOLD-like words into one enum |
| Honest **prototype / specification** posture | Claim of consciousness, rights, personhood, or sentience |
| Determinism **when** seed + program + HAL version are fixed | Claim of Byzantine-safe multiplayer by this document alone |
| Open questions deferred to **v0.2** (below) | A closed, final geometry ontology for all games |

---

## 10. Open questions deferred to v0.2

1. **Alternate primary profiles:** attractor-graph navigation and timeline-branch geometry as first-class HAL ids.  
2. **Diagonal / multi-cell footprints** and stacking rules.  
3. **φ-driven** hard directional masks (v0.1 allows mild bias only).  
4. **Re-discovery epochs** and V invalidation mid-match (draft invalidation exists in Core v0.3; board semantics TBD).  
5. **Π_A+ glyph** as default combat token identity vs 7D teaching tags.  
6. **Official numeric bands** for T_obs thresholds beyond teaching defaults (1.02 / 1.0 / 0.98).  
7. **Multi-pair gates** (more than one `branch on T` focus per turn).  
8. **Competitive online authority** (Durable Objects, signed logs)—beyond this contract.  
9. **Partial vocabulary** play: which cells/ops remain available.  
10. **Formal conformance test suite** binding golden PlayableState digests to example programs.

---

## 11. Acceptance gate

This profile is **accepted for materializer/UI work** only when stakeholders agree that:

- Projected 3-space is the correct v0.1 starter geometry;  
- The mapping table and ternary effects are sufficient to implement without invention;  
- Claim boundary is printed or linked in any demo that cites this profile.

**Do not proceed to materializer or UI until this profile is accepted.**

---

*End of SymLan Spatial/Temporal HAL Profile v0.1*

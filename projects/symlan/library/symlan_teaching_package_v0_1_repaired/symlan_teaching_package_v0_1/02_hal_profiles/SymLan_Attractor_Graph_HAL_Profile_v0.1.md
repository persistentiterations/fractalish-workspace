# SymLan Attractor-Graph HAL Profile v0.1

**Title:** SymLan_Attractor_Graph_HAL_Profile_v0.1  
**Profile id (canonical):** `spatial_temporal.attractor_graph.v0.1`  
**Status:** Draft contract (not a runtime, not a game build)  
**Date:** 2026-07-27  
**Authorities:**  
- SymLan Programming Language **v0.2.6** (teaching / language canonical)  
- SymLan Core Language **v0.3** team expansion (does not override v0.2.6 where they conflict)  
- This HAL contract for **geometry only**  

**Related profile (complementary, not replaced):**  
`spatial_temporal.projected_3space.v0.1` — Cartesian board + coherence slice **S**.  

**Audience:** Language, runtime, and graph-navigation implementers  

**One-line purpose:**  
Define how a SymLan program, after discovery and resolve, yields a **navigable attractor graph whose vertices are earned vocabulary (and surviving structural loci)**—without claiming consciousness, literal 4-space, physical substrate fidelity, or production readiness.

---

## 1. Purpose and scope

### 1.1 Purpose

This profile is the **second Geometry HAL** for SymLan playable projections. Where projected 3-space makes **cells** primary and **V** a label set, this profile makes **earned V the walkable space**.

It answers: *When the game surface is an attractor graph, what is a node, what is an edge, when may the actor traverse or send, and how do κ, φ, T, gates, and receipts bind that graph?*

### 1.2 Relationship to projected_3space

| | Projected 3-space | Attractor graph (this profile) |
|--|-------------------|--------------------------------|
| Profile id | `spatial_temporal.projected_3space.v0.1` | `spatial_temporal.attractor_graph.v0.1` |
| Primary space | Discrete board cells `(x,y)` + slice **S** | Graph of **V-states + structural loci** |
| Role of V | Labels / tokens on a board | **Vertices of the navigable space** |
| Human layout | Board *is* the rule surface | Optional drawing of the graph; **rules ignore free X/Y** |
| Status | Accepted starter for Eracii-readable combat | **Complementary** profile for V-first navigation |

Neither supersedes the other. A future materializer chooses **one** profile id per PlayableState. Dual-profile fusion is **out of scope** for v0.1.

### 1.3 In scope (v0.1)

- Exactly **one** geometry: **attractor graph**.  
- Explicit SymLan → graph mapping (teaching subset only).  
- Discovery → resolve → **walkable** graph rules.  
- Ternary gate effects on stay / traverse / send (**proceed / hold / reverse**).  
- Minimal attractor-graph **PlayableState** field list.  
- One short example program + intended graph.  
- Non-conflation and claim boundary.  
- Open questions deferred.

### 1.4 Out of scope (v0.1)

- Materializer code, hotseat UI, session export, networking.  
- Timeline-branch geometry (separate future profile).  
- New SymLan syntax beyond v0.2.6 / Core v0.3 teaching subset.  
- Automatic force-directed or “pretty” layout as a **rules** dependency.  
- Multi-actor combat balance, AI opponents, or production multiplayer.  
- Physical substrate HAL (BZ, VO₂, Hopfield) or Construction A+ / Π_A+ execution.  
- Consciousness, rights, personhood, or sentience claims.

### 1.5 Design law (inherited)

> The programmer specifies the arena. The substrate earns the vocabulary.  
> Symbols are usable only after resolution. HOLD is legal. False closure is not.

Graph consequence: **the walkable vertex set is not a free skill menu.** Vertices that come from V appear only after resolve (or are explicitly labeled structural loci that discovery kept). Mock discovery must stay labeled mock when used in prototypes.

---

## 2. Geometry definition

### 2.1 Choice

**Attractor graph:** a finite **directed** graph \(G = (N, E)\) in which:

1. **Vertices \(N\)** =  
   - all **resolved** vocabulary states in `V` (each `state_id` is a locus), **plus**  
   - programmer-declared **structural loci** (`node` declarations) that **survive discovery** as non-eliminated handles (e.g. `basin_center`, combatant anchors).  
2. **Edges \(E\)** =  
   - couplings that remain **legal after resolve**, **plus**  
   - phase-two **send/expect** paths the current **gate** permits (as directed, possibly ephemeral, effect edges).  
3. **Movement** = **traverse** one legal directed edge, or **stay** on the current vertex.  
4. **No free Cartesian X/Y grid as the rule surface.** A UI may draw nodes in the plane for humans; positions are **display-only** and never authorize moves the graph forbids.

### 2.2 One-sentence justification

Attractor-graph geometry makes **earned symbols the places you stand**—so navigation, send, and HOLD teach vocabulary discipline rather than board tactics alone.

### 2.3 Notation

| Symbol | Meaning in this profile |
|--------|-------------------------|
| **Vertex / locus** | Graph node: a resolved `state_id` or surviving structural `node` id |
| **Edge** | Directed walkable or effect link `src → dst` with legality under gate |
| **Actor locus** | Where the current turn’s actor **stands** (`current_locus`) |
| **Structural locus** | Programmer-declared `node` that discovery did not eliminate |
| **V-locus** | Vertex whose id is a resolved vocabulary `state_id` |
| **S** | Optional coherence **step index** (integer), same spirit as projected-3-space slice—not a spatial axis |

**V is not a label stuck on a board.** After resolve, V **is** (part of) the map.

### 2.4 What is *not* a vertex

- Free programmer strings never bound by discovery.  
- Pending vocabulary entries (`status: pending`).  
- Cosmetic glyph faces without a bound `state_id` or structural id.  
- Basin action names (EXTEND / RETRACT) or Natural Math process names.

---

## 3. Mapping table: SymLan construct → graph element

| SymLan construct | Geometric meaning in Attractor-Graph HAL |
|------------------|------------------------------------------|
| `node A, B, …` | Declares **structural loci** (and/or actor anchors). Pre-discovery: handles only. Post-discovery: remain as vertices if status ≠ eliminated. |
| `A -> B [κ, φ, T]` | Declares a **candidate directed edge** A→B with residual κ/φ/T. After resolve: edge is **materialized** if both ends exist in \(N\) and the coupling was not invalidated. κ = edge weight / send strength bias; φ = timing or preferred-order bias (display + mild priority in v0.1); T = coherence target for gates on that pair. |
| `A <-> B […]` | Two directed edges (or one undirected record expanded to both directions); directionality must be explicit in PlayableState. |
| `vocab V = register(target, θ:, features:)` | Declares **pending V**. Graph has **no V-loci** until resolve. Target is typically a structural basin vertex. |
| `features: 7D` (etc.) | Feature pack that discovery used; recorded on V / provenance—not a second geometry. |
| Pending V | **No walkable V-vertices.** Structural loci may exist as a skeleton graph; symbol-using traverse/send that *requires* a V-id is illegal (**PendingSymbolUse**). |
| Resolved V | Each earned `state_id` becomes a **V-locus** vertex. Optional edges from structural target → each state (or among states) per materializer rules in §4. |
| `run discovery … seed:` | Produces candidate basins / state ids under seed + rule stamp. **Does not** open phase-two walk commits that use unresolved symbols. |
| `after resolve V { … }` | Hard phase boundary: graph becomes **navigable for symbol ops**; send/expect/branch may run. |
| `send X[Si] -> Y` | **Directed effect** along an edge (or ephemeral send-edge) from actor’s locus or X toward Y / Si, subject to gate. |
| `expect Y[Sj] …` | Asserts that locus Y holds or accepts Sj within a window; failure is evidence, not silent success. |
| `branch on T(a, b) { >…; ~…; <… }` | Sets **gate.outcome** ∈ {proceed, hold, reverse}. **Three arms required.** Gates retarget edge legality and send policy (§5). |
| Receipts / tip | Every graph-changing or symbol-using step is receiptable; `receipts_tip` advances. |
| κ / φ / T on a vertex | Residual readouts from couplings involving that locus; do not alone invent new vertices. |

### 3.1 Dimensional defaults (graph-facing)

| Dim | Default meaning on the graph |
|-----|------------------------------|
| **κ** | Edge *strength*: higher κ may keep edge walkable under stress or scale send magnitude; does **not** grant omniscience of the whole graph. |
| **φ** | *Phase / order bias*: may prioritize one outgoing edge in UI or mild scheduler preference; v0.1 does not hard-mask edges by φ alone. |
| **T** | Coherence target for `branch on T`; drives **gate** and optional step index **S**. |
| **V** | After resolve: **vertex set contribution**; before resolve: pending only. |

---

## 4. Lifecycle: discovery → resolve → navigable graph

### 4.1 Mandatory order

```text
1. Parse & type-check SymLan source (teaching subset)
2. Instantiate empty graph skeleton (declared structural nodes, pending V)
3. run discovery  →  DiscoveryPacket (candidate basins / state ids)
4. resolve V      →  bind Vocabulary<resolved>; promote state_ids to vertices
5. Materialize edges from couplings + default V-links (§4.3)
6. after resolve  →  phase-two ops; gate evaluation; actor locus placed
7. Receiptize / optional checkpoint
```

Skipping resolve before symbol-using traverse/send is **PendingSymbolUse**, not a soft warning.

### 4.2 Pending vs resolved

| Phase | Vertices present | Walk / send using V-ids |
|-------|------------------|-------------------------|
| Declared / discovering | Structural loci only (optional) | **Forbidden** for V-dependent ops |
| Resolved / playing | Structural + V-loci | Allowed under **gate** rules |
| Partial V | Only resolved state_ids as vertices; partial status **must** be explicit | Ops on missing ids illegal |
| Invalidated | V-loci frozen or removed per runtime; HAL requires honest status | No pretence of full V |

### 4.3 When edges become walkable

An edge `src → dst` is **walkable** for the actor only if **all** hold:

1. Both `src` and `dst` are in \(N\) (structural or resolved V).  
2. Edge origin is: a surviving **coupling**, a materializer **default V-link** (see below), or a gate-permitted **send path**.  
3. Current **gate** allows traverse for this edge class (§5).  
4. Actor’s `current_locus` is `src` (for movement), or the send rule allows remote effect (send is not free teleport of the actor unless the profile instance says so—**v0.1 default: send does not move the actor**).

**Default V-links (v0.1 teaching):** after resolve, for each earned state `Si` bound to register target `B`:

- Materialize directed edge `B → Si` (basin to earned state), and  
- Materialize directed edge `Si → B` (return),  

unless the program’s couplings already define the only legal skeleton. Couplings between structural nodes always contribute candidate edges when both ends survive.

### 4.4 Actor locus placement (v0.1 default)

- On enter `playing`: place actor at the first combatant structural node if present, else at `vocab` register target, else at any structural locus (deterministic order by id).  
- **Stay:** locus unchanged.  
- **Traverse** `u → v`: locus becomes `v` if edge walkable.  
- V-loci are standable after resolve; standing on `Si` means the actor is “at” that earned symbol for UI and send origin defaults.

### 4.5 Step index S (optional, same spirit as prior HAL)

```text
proceed  →  S := S + 1  on successful traverse or allowed send commit
hold     →  S unchanged; stay legal; symbol-using send blocked
reverse  →  S := max(0, S - 1); send recoils; traverse still allowed by default
```

**Reverse is not time travel** and not Basin `RETRACT`.

---

## 5. Ternary gate effects on the graph

### 5.1 Gate evaluation

Same teaching bands as projected-3-space HAL §5.1:

| Arm | Gate | Meaning |
|-----|------|---------|
| over-coupled (`>`) | **reverse** | Unsafe commit |
| near target (`~` / `≈`) | **proceed** | Usable coherence |
| under-coupled (`<`) | **hold** | Wait is legal |

`gate.outcome` ∈ {`proceed`, `hold`, `reverse`}. Incomplete ternary is invalid SymLan.

### 5.2 Stay / traverse / send

| Gate | Stay | Traverse walkable edge | Send / symbol-using effect |
|------|------|------------------------|---------------------------|
| **proceed** | Allowed | Allowed along edges with `legal: true` under proceed | **Allowed** along gate-legal send edges; may scale with κ |
| **hold** | Allowed (**preferred**) | Allowed only to **stay** or along edges marked `hold_ok` (v0.1 default: **stay only**, or traverse only if edge is a pure structural self-loop—default **stay-only**) | **Blocked** — no pretend resolution |
| **reverse** | Allowed | Allowed (same skeleton as proceed unless edge scarred) | **Self-recoil**: no free progress on target; scar optional on source edge/locus; S may decrement |

v0.1 combat-prototype spirit (aligned with projected-3-space):

> **hold blocks send; reverse converts send to self-recoil; proceed allows normal send.**  
> **hold** does not erase the gate from receipts or UI.

### 5.3 Visibility (graph)

| Gate | Visibility default |
|------|--------------------|
| **proceed** | Full vertex set + edge skeleton; V HUD clear |
| **hold** | Current locus + outgoing neighbors only; V HUD dimmed; send blocked |
| **reverse** | Full graph visible; self-effects emphasized; outbound send suppressed/reflected |

### 5.4 Edge legality field

PlayableState edges carry at least:

```text
legal_proceed | legal_hold | legal_reverse   (or a single "legal" recomputed from gate)
```

v0.1 materializers may store one `legal: bool` recomputed whenever `gate.outcome` changes.

---

## 6. Minimal PlayableState shape (attractor graph)

Conceptual only—fields a future materializer **must** populate.  
`schema_version` may share the playable envelope; **profile id distinguishes geometry**.

```json
{
  "schema_version": "symlan.playable_state.v0.1",
  "hal_profile": "spatial_temporal.attractor_graph.v0.1",
  "language_authority": "symlan.v0.2.6",
  "team_expansion": "symlan.core.v0.3",
  "rule_stamp": "string — HAL + materializer version",
  "program_id": "sha256 of SymLan source",
  "seed": "string | null",
  "phase": "declared | discovering | resolved | playing | closed",

  "graph": {
    "directed": true,
    "note": "rules surface; layout is display-only"
  },

  "nodes": [
    {
      "id": "S1",
      "kind": "vocab_state | structural",
      "status": "active | held | eliminated",
      "kappa": 0.5,
      "phi": "pi/4",
      "T": 1.0
    }
  ],

  "edges": [
    {
      "src": "basin_center",
      "dst": "S1",
      "kappa": 0.5,
      "phi": "pi/4",
      "T": 1.0,
      "origin": "coupling | v_link | send_path",
      "legal": true
    }
  ],

  "vocabulary": {
    "id": "V",
    "status": "pending | resolved | partial | invalidated",
    "states": [
      {
        "state_id": "S1",
        "basin_ref": "basin:basin_center:primary",
        "glyph_or_tag": "optional",
        "provenance": "discovery_run_id"
      }
    ]
  },

  "gate": {
    "focus_pair": ["Alpha", "basin_center"],
    "T_obs": 1.0,
    "outcome": "proceed | hold | reverse"
  },

  "current_locus": "S1",
  "actors": [
    { "id": "Alpha", "locus": "basin_center", "status": "active" }
  ],

  "slice": {
    "S": 0,
    "S_max": 64,
    "note": "coherence step index, not free Z / not Euclidean axis"
  },

  "clock": {
    "discovery_closed": true,
    "round": 1,
    "turn_actor": "Alpha"
  },

  "display_layout": {
    "optional": true,
    "positions": { "S1": { "x": 0.0, "y": 0.0 } },
    "note": "human drawing only; not the rule surface"
  },

  "receipts_tip": "sha256:… or GENESIS or local:…",
  "claim_boundary": "toy/playable projection of earned symbols only"
}
```

### 6.1 Invariants

1. If `vocabulary.status` is not `resolved` (or honest `partial`), no V-id may be `current_locus` and no V-dependent send may commit.  
2. `gate.outcome` ∈ {`proceed`, `hold`, `reverse`} when evaluated.  
3. `current_locus` ∈ node ids (or null only before placement).  
4. Every edge `src`/`dst` references existing node ids.  
5. `hal_profile` **must** be `spatial_temporal.attractor_graph.v0.1` for this geometry.  
6. `display_layout` never overrides `edges[].legal` or gate policy.  
7. Mutations of locus, edges, gate, V, or clock are receipt-appendable.

---

## 7. Example: teaching program → small walkable graph

### 7.1 Program (teaching subset)

```symlan
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
```

### 7.2 Intended post-resolve graph (normative sketch)

After successful discovery + resolve, a conformant materializer **must** produce a graph such that:

1. **Vertices** include at least: `Alpha`, `basin_center`, and one earned V-locus `S1` (more states allowed if discovery returns them).  
2. **Edges** include at least: `Alpha → basin_center` (from coupling), plus default **v_links** `basin_center → S1` and `S1 → basin_center` (unless rule_stamp documents a stricter skeleton).  
3. **V.status** is `resolved` (or explicit partial); `S1` has provenance to seed `attractor-graph-v0.1-demo`.  
4. **current_locus** for Alpha starts on `Alpha` or `basin_center` (deterministic; must be recorded).  
5. **gate.outcome** is exactly one of proceed/hold/reverse after the branch; edge `legal` flags follow §5.  
6. **No** send is treated as committed before resolve.  
7. **receipts_tip** covers discovery, resolve, and any phase-two ops.

**ASCII (illustrative layout only):**

```text
        [Alpha]
           |
           | coupling (κ,φ,T)
           v
     [basin_center] <----> [S1]
           ^     v_link      |
           |_________________|
```

Under **hold**: actor may **stay**; send Alpha[S1] blocked.  
Under **proceed**: traverse basin_center→S1 allowed; send allowed.  
Under **reverse**: traverse allowed; send self-recoils.

If any of (1)–(7) fails, the HAL instance is **non-conformant**, even if a pretty force-directed picture is drawn.

---

## 8. Non-conflation rules (mandatory)

| Namespace | States | Role in this HAL |
|-----------|--------|------------------|
| **SymLan gate** | proceed / hold / reverse | Edge legality, stay/traverse/send, step S |
| **Cognitive Basin action** | EXTEND / HOLD / RETRACT | **Not** graph gates |
| **Cognitive Basin epistemic** | SUPPORTED / UNRESOLVED / CONTRADICTED | Evidence about claims, not edge walkability |
| **Natural Math process** | EXTEND / SENSE / RESTRICT | Substrate adapters only via **explicit** versioned tables |

**Hard rules:**

1. Do not silently rename SymLan HOLD to Basin HOLD in code or UI.  
2. REVERSE is not “undo history” and not RETRACT.  
3. Standing on a V-locus is not “knowing” the substrate without receipts/provenance.  
4. Display coordinates are not a second rules geometry.

---

## 9. Claim boundary (one page)

| **Is** | **Is not** |
|--------|------------|
| A **HAL profile contract** for attractor-graph playable projection | A materializer, hotseat, or full runtime |
| Profile id **`spatial_temporal.attractor_graph.v0.1`** | A silent replacement of projected_3space |
| **Complementary** to `spatial_temporal.projected_3space.v0.1` | A merge of board + graph into one required engine |
| Geometry where **earned V states are navigable vertices** | Permission to hardcode free skill names as vertices |
| Couplings + gate-legal send paths as **edges** | Proof that κ/φ/T are universal physical constants |
| Ternary gates binding **stay / traverse / send** | Binary-only navigation with cosmetic “hold” |
| Optional **display_layout** for humans | Euclidean free-flight 3D/4D rule space |
| Compatible with **receipt / replay** discipline | Production PKI, anti-cheat, or ranked multiplayer |
| Bound by **SymLan v0.2.6** teaching subset + this contract | A new SymLan syntax release |
| Honest **toy / playable projection of earned symbols** | Consciousness, rights, personhood, or sentience |
| Deterministic **when** source + seed + rule_stamp fixed | Byzantine-safe online authority |
| Open questions listed below | Final ontology for all future games |

---

## 10. Open questions deferred (v0.1 out of scope)

1. **Materializer + hotseat** for this profile (do not implement until this contract is accepted).  
2. **Timeline-branch** geometry as a third HAL id.  
3. **Layout algorithms** (force-directed, hierarchical) as anything more than display_layout.  
4. **Multi-actor** simultaneous loci, blocking, and combat resolution on shared vertices.  
5. **Partial V** edge policies (which v_links appear when only some states resolve).  
6. **φ-hard masks** and κ-threshold edge culling.  
7. **Re-discovery / V invalidation** mid-session (vertex removal vs scar).  
8. **Sensor grounding** and physical substrate HAL binding.  
9. **Conjugate Lattice cylinders** and other research geometries.  
10. **Cross-profile** export (graph ↔ board) and dual-view identity rules.  
11. **Official T bands** beyond teaching 1.02 / 1.0 / 0.98.  
12. **Shared receipt envelope** with toy runtime, projected-3-space materializer, CONFIGURATOR, Bolt-On.  
13. **Formal conformance suite** (golden graph digests for the example program).  
14. Construction **A+ / Π_A+** glyphs as default vertex faces.

---

## 11. Acceptance gate

This profile is **accepted for future materializer/UI work** only when stakeholders agree that:

1. Attractor graph is the correct **V-first** complementary geometry;  
2. Projected 3-space remains the **board-first** complementary profile (not discarded);  
3. Mapping table + gate effects are implementable **without inventing syntax**;  
4. Claim boundary is linked from any demo that cites this profile.

**Do not implement attractor-graph materializer or UI until this profile is accepted.**

---

*End of SymLan Attractor-Graph HAL Profile v0.1*

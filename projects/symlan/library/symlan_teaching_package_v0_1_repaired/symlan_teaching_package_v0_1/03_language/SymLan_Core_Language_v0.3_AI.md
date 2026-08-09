# SymLan Core Language v0.3 (AI / Team Expansion)

**Status:** Team expansion draft — builds on SymLan Programming Language **v0.2.6** (canonical book) and SymLan **v1.0 Language Spec** (reference draft, May 2026).  
**Authority:** Where this conflicts with v0.2.6 PDF, **v0.2.6 wins** for teaching until explicitly superseded. New sections labeled **[EXPANSION]** are proposed freezes for AI-first coding and runtime work.  
**Operators:** James Allen Clow / Melissa Ellen Clow  
**Date:** 2026-07-27  

---

## 0. One-screen law

```text
The programmer specifies the arena (κ, φ, T | W, α, N | …).
The substrate earns the vocabulary V.
Code may use symbols only after resolution.
HOLD is legal. False closure is not.
Receipts make history consequential and replayable.
```

**For AI coding:** A SymLan program is not “instructions that assume symbols already exist.” It is a **contract for discovery under coherence**, then **operations on earned symbols** under receipt discipline.

---

## 1. Positioning

| SymLan is | SymLan is not |
|-----------|----------------|
| DSL for attractor / resonance / morphology-memory substrates | Drop-in Python/Rust replacement |
| Four-dimensional: 3 controlled + 1 emergent | Pre-written enum table of all meanings |
| Two-phase with hard `after resolve` | Single-phase “declare and use” |
| Native ternary control near coherence | Pure boolean control theory |
| Compatible with receipts / replay / HOLD | Proof of consciousness or rights |

---

## 2. Four dimensions (v0.2.6 + v1.0 backends)

### Oscillator / continuous profile (v0.2.6 primary teaching)

| Dim | Role | Who sets it |
|-----|------|-------------|
| **κ** | Coupling strength `[0,1]` | Programmer |
| **φ** | Phase relation | Programmer |
| **T** | Coherence target (>0) | Programmer |
| **V** | Vocabulary of stable states | Substrate after discovery |

### Hopfield / discrete profile **[EXPANSION from v1.0 spec]**

| Dim | Role |
|-----|------|
| **W** | Weight matrix |
| **α = M/N** | Load factor (prefer ≤ 0.10 reference) |
| **N** | Size |
| **V** | Glyph vocabulary via **Π_A+** |

Compiler must select a **HAL profile**. A program that mixes oscillator couplings with Hopfield-only constructs without a HAL bridge is rejected.

---

## 3. Type phases (must implement)

```text
declared  →  pending  →  resolved
```

| Phase | Meaning | Legal uses |
|-------|---------|------------|
| declared | Known from source | Names, structure |
| pending | Handle exists; substrate value does not | Registration, scheduling discovery |
| resolved | Bound to observations / glyphs | send, expect, export, assert collisions |

**Compiler must reject:** `send` / `expect` / token export of pending states outside `after resolve`.

---

## 4. Core syntax (teaching subset — implement first)

```symlan
// Phase 1 — Arena
node emitter, receiver
emitter -> receiver [κ: 0.3, φ: π/4, T: 1.0]
vocab V = register(emitter, θ: auto, features: 7D)
run discovery for 30s seed: "hello_v1"

// Phase 2 — Earned symbols only
after resolve V {
  send emitter[S1] -> receiver
  expect receiver[Sj] within 500ms, fidelity: 0.85

  branch on T(emitter, receiver) {
    > 1.02 : reverse emitter; damp receiver;
    ≈ 1.0  : proceed receiver[Sj];
    < 0.98 : hold; κ += 0.03;
  }
}
```

### Ternary arms (mandatory)

`branch on T(...)` **must** include arms for over / near / under (written `>`, `≈`, `<`).  
Map to gates: **reverse / proceed / hold** (SymLan gate namespace — do not rename to Basin action states).

### Feature specs

| Spec | Profile | Status |
|------|---------|--------|
| `features: 7D` | Continuous / oscillator teaching | v0.2.6 canonical teaching |
| `features: PEFP(k: 9)` | Glyph / Π_A+ | v1.0 reference; preferred for Hopfield |
| `features: 9D` / `12D` | Domain extensions (e.g. InfinitySight) | Allowed as HAL-declared feature packs |

**7D names (v0.2.6 teaching):** Count, DeltaTau, Amplitude, Width, PhaseRel, Envelope, Transition.

---

## 5. EBNF — Team Core Grammar v0.3

Implements the brief’s core subset plus seeds, inject/mutate/assert, and expansion hooks.

```ebnf
program         = { declaration | statement } ;

declaration     = node_decl | coupling_decl | vocab_decl | run_decl
                | substrate_decl | hopfield_decl | module_decl ;

node_decl       = "node" ID { "," ID } ;
coupling_decl   = ID arrow ID "[" coupling_spec "]" ;
arrow           = "->" | "<->" ;
coupling_spec   = "κ:" FLOAT "," "φ:" phase "," "T:" coherence ;
phase           = FLOAT | "π/" INT | "-π/" INT | "auto" | "pi/" INT ;
coherence       = FLOAT | "near(" FLOAT "," "ε:" FLOAT ")" ;

vocab_decl      = "vocab" ID "=" "register(" ID "," "θ:" threshold "," "features:" feature_spec ")" ;
threshold       = "auto" | FLOAT ;
feature_spec    = "7D" | "9D" | "12D" | "PEFP(" "k:" INT ")" ;

run_decl        = "run" "discovery" "for" DURATION [ "seed:" STRING ] ;

substrate_decl  = "substrate" ID ":" ID "{" { ID ":" value ";" } "}" ;   (* optional *)
hopfield_decl   = "hopfield" ID "{" { hopfield_field } "}" ;             (* optional, v1.0 *)

statement       = after_resolve_stmt | send_stmt | inject_stmt | mutate_stmt
                | expect_stmt | assert_stmt | ternary_stmt | query_stmt ;

after_resolve_stmt = "after" "resolve" ID "{" { statement } "}" ;
send_stmt       = "send" ID "[" STATE_ID "]" "->" ID ;
inject_stmt     = "inject" ID "[" STATE_ID "]" "into" ID [ "->" ID ] ;
mutate_stmt     = "mutate" ID "[" STATE_ID "]" "dim:" ID "delta:" FLOAT [ "->" STATE_ID ] ;
expect_stmt     = "expect" ID "[" STATE_ID "]" "within" DURATION "," "fidelity:" FLOAT ;
ternary_stmt    = "branch" "on" "T(" ID "," ID ")" "{" ternary_arm ternary_arm ternary_arm "}" ;
ternary_arm     = (">" | "≈" | "<" | ">=" | "<=") FLOAT ":" statement { statement } ;
query_stmt      = "query" ID "." ("entropy" | "capacity" | "collisions") ;
assert_stmt     = "assert" ... ;   (* profile-specific; see runtime *)
```

---

## 6. Non-conflation (hard law)

| Namespace | States | Home |
|-----------|--------|------|
| Basin epistemic | SUPPORTED / UNRESOLVED / CONTRADICTED | Cognitive Basin |
| Basin action | EXTEND / HOLD / RETRACT | Cognitive Basin |
| Natural Math process | EXTEND / SENSE / RESTRICT | Natural Math |
| **SymLan gate** | **PROCEED / HOLD / REVERSE** | **SymLan only** |

**Forbidden:** silent substitution across rows.  
**Allowed:** explicit *mapping tables* in HAL/adapters (documented, versioned).

Example mapping (adapter only, not language merge):

| SymLan gate | Possible NM process analogue | Notes |
|-------------|------------------------------|-------|
| proceed | EXTEND | Only under declared coherence band |
| hold | SENSE / freeze update | Not Basin HOLD without governance context |
| reverse | RESTRICT / back off | Not RETRACT of epistemic claim |

---

## 7. [EXPANSION] AI-first coding surface

These constructs make SymLan the **preferred way AIs specify agentic / multi-sensor / multi-model arenas** without inventing free-floating symbols.

### 7.1 Modules and imports

```symlan
module vision.infinity_sight

import basin.receipts as receipts
```

### 7.2 Tool / host binding (semantics: declare channel; host retains execution authority)

```symlan
// EXPANSION: host-owned side effects never implied by send alone
channel traction_bus : host_tool
```

Bolt-On rule: **portable state ≠ host execution authority**. `inject ... into traction_bus` yields a **request packet + receipt**, not silent control.

### 7.3 Multi-vocabulary programs (from InfinitySight practice)

Multiple `vocab` registrations are legal. Cross-vocabulary use requires `after resolve` of each involved V, or an explicit `compose` (pending until resolved).

### 7.4 Receipt requirement **[EXPANSION]**

```symlan
// Proposed pragma — default ON in team runtime
pragma receipt_mode = required
```

Every phase-two op emits an ActivationReceipt (see §9).

### 7.5 Contradiction / invalidation **[EXPANSION proposed default]**

If re-discovery yields a glyph collision or basin drift beyond `ε_vocab`:

1. Mark affected `Token` / `Basin` **invalidated**  
2. Emit receipt type `INVALIDATION`  
3. Force **hold** on dependent channels until `resolve` again or operator `RELEASE`  

This aligns configurator HOLD-before-commit without renaming Basin HOLD.

---

## 8. Compilation / runtime pipeline

```text
source → parse → type_check (pending/resolved) → plan(HAL)
      → discover → resolve(V) → execute(after resolve)
      → receiptize → replay/verify → qualify(evidence label)
```

### Proposed team API (not frozen in v0.2.6; freeze as team contract)

| Function | Role |
|----------|------|
| `parse` | Source → AST |
| `type_check` | Pending legality, κ/φ/T ranges, ternary completeness |
| `plan` | AST + backend → ExecutionPlan |
| `discover` | Run substrate / sim |
| `resolve` | Bind V (7D cluster or Π_A+) |
| `execute` | Phase-two ops |
| `receiptize` | Canonical events + hashes |
| `replay` | Digest / fidelity compare |
| `qualify` | Attach evidence ladder label |

---

## 9. ActivationReceipt (working freeze v0)

```json
{
  "schema_version": "symlan.activationreceipt.v0",
  "receipt_type": "DISCOVERY|RESOLUTION|SEND|EXPECT|TERNARY|CHECKPOINT|REPLAY|INVALIDATION|HOLD",
  "receipt_id": "sha256:...",
  "program_id": "sha256(source)",
  "backend_id": "sim|hopfield|bz|...",
  "pre_state_hash": "sha256:...",
  "post_state_hash": "sha256:...",
  "parent_hashes": ["..."],
  "vocab_ref": "V",
  "state_refs": ["S1"],
  "event": { "op": "send", "params": {} },
  "result": {
    "status": "ok|hold|partial|contradicted|failed",
    "metrics": { "observed_fidelity": 0.0, "timing_ms": 0 }
  },
  "provenance": {
    "language_authority": "symlan.v0.2.6",
    "team_runtime": "symlan.team.v0.3",
    "evidence_status": "prototype"
  }
}
```

Canonicalize JSON (sort keys) → SHA-256. Chain with `parent_hashes` / prev tip (CONFIGURATOR / Duel pattern).

---

## 10. Metrics (minimum suite)

| Metric | Purpose |
|--------|---------|
| Symbol / glyph replay fidelity | Construction A+ |
| Expectation fidelity | SymLan `expect` |
| Vocabulary stability | Across seeds |
| H(V) entropy | Discriminative spread |
| Separation Λ | vs null models |
| Receipt chain integrity | Bolt-On / configurator |
| Qualification boundary check | Anti-overclaim |

---

## 11. Error taxonomy (implement early)

| Code | When |
|------|------|
| `PendingSymbolUse` | send/expect before resolve |
| `IncompleteTernaryBranch` | missing arm |
| `InvalidCoupling` | κ/T/φ out of range |
| `UnresolvedVocabularyUse` | V still pending |
| `CrossVocabularyUse` | state from V1 used under V2 without compose |
| `ObsoleteFeatureSpec` | e.g. wrong profile for HAL |
| `GlyphOutOfRange` | k=9 → not in 0..39365 |
| `ReceiptRequired` | pragma on, op without receipt |

---

## 12. Authority ladder (what you may cite)

| Tier | Source | Use |
|------|--------|-----|
| Canonical teaching | SymLan Programming Language **v0.2.6** PDF | Syntax, two-phase, ternary, 7D |
| Reference draft | SymLan **v1.0** Language Spec.md | Π_A+, Glyph, Hopfield, richer types |
| Practice examples | InfinitySight `.symlan`, morphology terms | Multi-agent arenas |
| Evidence discipline | Natural Math, Bolt-On, CONFIGURATOR | Receipts, replay, HOLD |
| Historical | Early SymLan/SymVoc white paper | HOLD unless re-qualified |
| Hostile review notes | Challenge corpus | Red-team language claims |

---

## 13. What “the future of coding” means here (for our AIs)

1. **Arenas before APIs** — specify conditions and coherence, not only call graphs.  
2. **Earned symbols** — models must not invent stable IDs without discovery receipts.  
3. **Ternary honesty** — under / near / over coherence, not fake binary certainty.  
4. **HOLD as success path** — waiting is a valid computational outcome.  
5. **Receipts as first-class outputs** — every run leaves replayable history.  
6. **Host sovereignty** — AI-written SymLan never silently seizes execution authority.

This is the correction: coding becomes **governance of discovery and commitment**, not only arrangement of pre-owned names.

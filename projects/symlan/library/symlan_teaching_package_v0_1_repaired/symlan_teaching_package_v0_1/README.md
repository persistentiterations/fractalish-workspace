# SymLan Teaching Package v0.1
## Eracii Convergence Arena — Code + Contracts for Team Review & Learning

**Purpose of this package**  
Give the team everything needed to:

1. Review the design path (what we are building and why)
2. Run the existing playable loops
3. Read and write small SymLan programs
4. See how a SymLan program becomes a navigable space
5. Prepare for multi-profile convergence on an attractor graph

**Claim boundary**  
Toy / playable projection only. Not consciousness, not production multiplayer, not literal 4-space, not a full compiler. SymLan gates are proceed / hold / reverse (not Basin action states).

---

## Package map

| Folder | Contents | Role |
|--------|----------|------|
| `01_design/` | Convergence Arena Design Brief v0.1 | Team review: geometry, dossiers, convergence, build sequence |
| `02_hal_profiles/` | Projected 3-space + Attractor-graph HAL contracts | Geometry authority — read before changing rules |
| `03_language/` | SymLan v0.2.6 PDF, Core v0.3, bridge notes, example `.symlan` | Language authority + first reading samples |
| `04_runtime/` | materializer, run_arena, configurator bridge, governed persistence | Runnable generators |
| `05_play_surfaces/` | Hotseat HTML + last PlayableState companions | Offline board play |
| `06_examples/` | Teaching programs (board + attractor) | Write / modify / re-materialize |
| `07_session_receipts/` | Session schema demo + replay script | Receipt discipline |

---

## Quick start (local)

Requires Python 3.10+ (stdlib only for materializer / arena loop).

```bash
cd 04_runtime

# Board geometry (default)
python materializer_v0_1.py
python run_arena_v0_1.py --no-open

# Attractor-graph geometry
python materializer_v0_1.py --attractor
python run_arena_v0_1.py --profile attractor_graph --no-open
```

Then open `05_play_surfaces/hotseat_play_surface_v0_1.html` in a browser  
(file:// works; or `python -m http.server 8765` from the package root).

Board hotseat: stay / move / strike under the gate, export session JSON.  
Attractor-graph: inspect the JSON (graph hotseat UI not yet built — next artifact).

---

## How this teaches SymLan

### Reading order for a new team member

1. **Design brief** (`01_design/`) — why attractor graph, dossiers, convergence  
2. **Projected 3-space HAL** (`02_hal_profiles/`) — first geometry, gates, PlayableState  
3. **Attractor-graph HAL** (`02_hal_profiles/`) — V as places, couplings as paths  
4. **Example programs** (`06_examples/`) — smallest programs that materialize  
5. **materializer_v0_1.py** — how discovery → resolve → graph/board happens  
6. **Hotseat + session receipts** — play, export, replay  
7. **SymLan v0.2.6 PDF + Core v0.3** — formal language when ready  

### What a learner should be able to do after this package

- Write a 15-line teaching-subset SymLan program (nodes, couplings, vocab, discovery, after resolve, branch on T)
- Materialize it under both profiles
- Explain pending vs resolved
- Explain why HOLD is legal
- Read a PlayableState JSON and point at gate, loci, edges (or cells)
- Export and reload a session receipt

---

## Progress covered by this package

| Milestone | Status in package |
|-----------|-------------------|
| Projected 3-space HAL contract | Yes |
| Attractor-graph HAL contract | Yes |
| Materializer (both profiles) | Yes |
| Arena loop (materialize → hotseat companions) | Yes |
| Board hotseat (gates + session export/replay) | Yes |
| Session receipt schema + offline replay proof | Yes |
| Convergence Arena design (multi-dossier, shared graph) | Yes (brief) |
| Graph hotseat UI | **Not yet** — next build |
| Live eracii.com shell-out | **Not yet** — after local proof |
| Full multi-profile convergence condition | **Design only** — open questions in brief |

---

## SymLan teaching subset (what the materializer accepts)

```text
node A, B, …
A -> B [kappa: …, phi: …, T: …]
vocab V = register(target, theta: auto, features: 7D)
run discovery for Ns seed: "…"
after resolve V {
  send X[Si] -> Y
  expect Y[Sj] within …, fidelity: …
  branch on T(a, b) {
    > … : reverse …;
    ~ … : proceed …;
    < … : hold;
  }
}
```

Pending symbols cannot be used for commit before resolve. Incomplete ternary is invalid.

---

## Suggested team review checklist

- [ ] Design brief open questions answered (convergence condition, team size, surface name)
- [ ] Both HAL profiles accepted as complementary (not competing)
- [ ] materializer demos run cleanly on a team machine
- [ ] At least one person other than the authors writes a new `.symlan` and materializes it
- [ ] Claim boundary remains linked from any demo shown outside the team

---

## Next engineering artifact (when brief is accepted)

**Graph hotseat v0.1** — offline surface that loads attractor-graph PlayableState and supports stay / traverse / send under the gate, framed so a second actor locus fits without redesign.

---

*SymLan Teaching Package v0.1 — Eracii × SymLan Convergence path*  
*Not production. Not consciousness. HOLD is legal.*

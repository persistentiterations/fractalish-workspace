# Natural Math and Specificity Governance
## A Local Rule Architecture for Discovery, Measurement, and Controlled AI Intake

**Version:** 1.0 (master reference document)
**Date:** 2026-07-10
**Document type:** Consolidated working paper — replaces the need to search separate files for definitions, status, or claims.

---

## How to read this document

Every section is one of two kinds. There is no in-between and no mixing within a section.

| Marker | Meaning | Can it be changed? |
|---|---|---|
| 🔒 **FROZEN** | Finished, tested, locked. This is the ground truth. | No — only typo/formatting corrections. A behavior change requires a new version number. |
| 🧪 **EXPLORATORY** | Working idea, early result, prototype, or proposal. Not yet proven. | Yes — this is where active work happens. |

If a sentence is not clearly under one of these two labels, treat it as **EXPLORATORY** until proven otherwise. Nothing in this document is allowed to be ambiguous about its own status.

Every technical term is defined exactly once, in Section 2 (the Glossary). After that, the same word always means the same thing everywhere in this document, including the appendices. If a source file used a different word for the same idea, that mapping is recorded in Section 2 as well, so nothing is lost — it is just standardized.

---

# PART I — WHAT THIS PROJECT IS, IN PLAIN LANGUAGE

## 1. Executive summary

This project has five layers. Each layer does one job and hands off to the next one. No layer does another layer's job.

1. **🔒 The rulebook (Natural Math).** A set of simple, exact rules for how a small grid-based "creature" (called a node) is allowed to move, sense its surroundings, spend energy, and split into new nodes. Every rule uses whole numbers only — no fractions, no guessing, no hidden math. Anyone, or any machine, can run these rules by hand and get the same result every time.

2. **🔒 The test (the Maze).** A fixed 20×20 grid maze used to check whether nodes following the rulebook can actually do something useful: find a target, remember how they got there, and let other nodes retrace the route without getting lost or corrupting it. This is called the **Stage 10 maze test**.

3. **🔒 The scorecard (the Specificity Engine).** A separate, independent tool that takes a finished maze result and grades it against a written checklist ("did the node find the target? did it get home? was the trail clean?"). It produces a score and a plain-language risk label. It does not run the maze and does not change the rulebook — it only measures what already happened.

4. **🧪 The demonstration (the HTML prototypes).** Interactive, visual mock-ups that show what the scorecard and the maze *could* look like in a live system. These are sketches for understanding and communication, not proof of anything new.

5. **🧪 The applied idea (Guardian).** A proposed use of the same scorecard idea, but applied to a different problem: deciding whether a piece of AI-related data or code should be let into a company's systems at all, before it ever runs. This is a product concept built *on top of* the architecture above, not a new frozen result.

**The one-sentence version:** a fixed set of exact, whole-number rules (layer 1) was tested in a maze (layer 2) and the result was graded by an independent scorer (layer 3); a set of visual demos (layer 4) illustrate how that scoring idea could be shown to a person; and one proposed business use of the scoring idea is an AI intake checkpoint called Guardian (layer 5).

## 2. Glossary — every term, defined once

Use this table as the single source of truth for word meanings in this document. Where an older source file used a different word for the same concept, it is listed under "older name" — that word should no longer be used going forward.

| Term used in this document | Plain-language meaning | Older name(s) seen in source files (retired) |
|---|---|---|
| **Node** | One simulated point on the grid. Has a position, energy, and a small set of exact yes/no properties. | — |
| **Rulebook** | The frozen set of exact rules that says how a node is allowed to move, sense, spend energy, and split. | "Natural Math," "the base," "the frozen integer base" |
| **Scout** | A node whose job is to explore the maze without being told the route in advance. | — |
| **Route record** | The trail a scout leaves behind after successfully reaching the target and returning to base. Only a *completed round trip* freezes a route record. | "learned trail," "reinforced graph," "the path" |
| **Explored mark** | A trace left by a scout while exploring, including wrong turns and dead ends. Explored marks are historical evidence, not a proven route. | "wrong turns," "scream marks" (partial overlap only) |
| **Auditor** | A separate check (not a moving node) that tests whether the route record can actually be read and followed from base to target and back. | "audit reader," "greedy audit" |
| **Follower** | A node that uses a completed route record to travel, but is not allowed to change it. | "non-scout" |
| **Setup check** | A check done before or outside of a run to confirm the maze itself is valid (e.g., that a path physically exists). This is not something any node does — it is bookkeeping done by the test harness. | "global reachability check" |
| **Maze test / Stage 10** | The specific, frozen 20×20 maze experiment used to generate evidence about scout, route record, auditor, and follower behavior. | "the maze," "Stage 10" |
| **Target checklist** | A written, numbered list of the exact conditions a result must meet to "count" as a success, used by the scorer. | "SpecificityTarget" |
| **Checklist item** | One line on the target checklist — one yes/no or numeric condition. | "TargetFeature" |
| **Match score** | The fraction (0 to 1) of the target checklist that a given result satisfies, after applying each item's importance weight. 1.0 means every item was fully satisfied. | "GSR" (Governance-Satisfying Ratio) |
| **Gap score** | 1 minus the match score. How far the result is from fully meeting the checklist. | "NGR" (Non-Governance Ratio) |
| **Scorer** | The independent tool that reads a finished result, compares it to a target checklist, and produces a match score, a gap score, and a risk label. It never re-runs the original test and never changes the rulebook. | "Specificity Engine" |
| **Result slip** | A permanent, tamper-evident record of one scoring event: what was measured, against which checklist, with what score, and what caveats. Once created, a result slip is never edited — a re-score creates a brand-new slip. | "MeasurementReceipt," "receipt" |
| **Risk label** | One of five words describing how far a result sits from its target checklist: On Target, Caution, Limited, Serious, or Failed. This label is about the *result's structural risk*, nothing else. | "Structural Debt" (OPERATIONAL / CAUTION / CONSTRAINED / CRITICAL / EXCEEDED) |
| **Evidence status** | What the available evidence currently shows about a claim: Backed, Unclear, or Contradicted. This is a separate question from the risk label and from the decision. | "Cognitive Basin epistemic state" (SUPPORTED / UNRESOLVED / CONTRADICTED) |
| **Decision** | What action is taken as a result of the evidence and the risk label: Proceed, Pause, or Reverse. This is a separate question from evidence status and from risk label. | "Cognitive Basin action state" (EXTEND / HOLD / RETRACT) |
| **Process state** | How the rulebook itself is currently moving under its own constraints: Extend (grow/act), Sense (check surroundings), or Restrict (pull back/limit). This describes rulebook mechanics only — it is not a decision and not a risk label. | "Natural Math process state" |
| **Ledger** | The permanent, ordered, tamper-evident log of every result slip, risk label, and decision, linked together so that any change to an old entry can be detected. | "SpecificityLedger" |
| **Replay** | The act of re-checking the entire ledger from the beginning to confirm nothing was altered, skipped, or reordered. | — |
| **Intake checkpoint** | A rule-based gate that inspects an incoming item (a file, a piece of code, a data artifact) *before* it is allowed to reach a live system, and produces one of three outcomes: Let In, Hold, or Reject. | "Guardian," "manifest-first intake" |
| **Manifest** | The declared, upfront description of an incoming item that the intake checkpoint reads before deciding whether to let it in. | — |

**Standing rule for this glossary:** if a future document introduces a new synonym for any row above, it must be added to the "older name" column and the standardized term must still be the one used in new writing.

## 3. What is established, what is shown, and what is only proposed

To prevent overclaiming, every statement in this project falls into exactly one of these three buckets. This replaces every looser phrase like "proven," "validated," or "working" used in earlier files.

### 3.1 Established (🔒 frozen, backed by a passing test)

- The rulebook can be written entirely in whole numbers, exact yes/no rules, and one-cell-at-a-time movement, with no decimals, no hidden fields, and no behavior that isn't explicitly written down.
- Under the specific conditions of the Stage 10 maze test, a scout following the rulebook was able to: explore without being given the route, find the target, leave a usable route record, have that route record read correctly by the auditor in both directions, and let a follower reuse the route without corrupting it.
- A target checklist can independently score a finished maze result and produce a reproducible, tamper-evident result slip.
- Match score, evidence status, decision, and process state can be tracked as four separate, non-overlapping labels for the same event.

### 3.2 Shown, but not yet broadly proven (🧪 exploratory, illustrated but untested at scale)

- The visual intake-checkpoint idea (Guardian), including its "check the manifest before anything runs" flow.
- Using this same checklist-and-scorer pattern to gate AI-related data or code intake in a real organization.
- The look and feel of a live maze-plus-scorecard display.
- Any specific enterprise security guarantee.

### 3.3 Not claimed anywhere in this project

- That the rulebook is proven correct for all possible situations, only for the tested maze conditions.
- That results from one domain (the maze) automatically transfer to a different domain (enterprise security, general AI safety, etc.).
- That the system is production-ready, autonomous, or intelligent in any general sense.
- That any specific numeric threshold, weight, or cutoff used in the scorer has been validated outside of this one maze test.

---

# PART II — 🔒 THE FROZEN RULEBOOK (Natural Math)

## 4. What the rulebook governs

The rulebook defines a small simulated world made of grid cells. A **node** is a living point on that grid. Each simulation step, every living node:

1. Spends energy just to stay alive.
2. Senses its immediate neighbors — nothing farther away.
3. Tries to move exactly one grid cell.
4. May split into two new nodes if a specific pressure condition is met.
5. May form a bond with a neighboring node if bonding is switched on for that run.

## 5. The hard boundary — what is allowed and what is not

This boundary is the single most important frozen rule in the whole project. Nothing described anywhere else in this document is allowed to violate it without being explicitly labeled a new, separate, exploratory version.

**Allowed inside the frozen rulebook:**
- Whole-number (integer) positions, energy, pressure, and counters.
- Finite lists and sets (a node's neighbors, its bonds).
- Exact yes/no ("if/else") decision rules.
- Movement of exactly one grid cell per step.
- Randomness that is a simple, discrete coin-flip or fixed-range draw — never a probability curve.

**Not allowed inside the frozen rulebook:**
- Decimal or floating-point numbers stored anywhere.
- Hidden or smoothed-out fields the node can "feel" without an explicit rule.
- Planning that looks beyond the node's immediate neighbors.
- Any behavior — however small — that isn't written down as an explicit rule with a matching test.

**Standing rule:** if a behavior appears in a demo, a screenshot, or a piece of code, but is not written in the rulebook and backed by a passing test, it is not part of the frozen base. It is, at most, an exploratory idea (see Appendix F).

## 6. Node record — the exact fields a node has

| Field | What it stores |
|---|---|
| id | A whole number that uniquely identifies the node. |
| position | Whole-number x, y, z grid coordinates. |
| direction | Which of six directions the node is facing, or "not facing anywhere." |
| alive | Yes or no. |
| energy | A whole number. Zero or below means the node cannot act and dies. |
| pressure | A whole number tracking how "blocked" or "crowded" the node has recently been. |
| type | One of: seed, tip, branch, inert, wall. |
| parent id | The id of the node that created it, or "none." |
| bonds | A finite list of other node ids it is currently connected to. |
| signal type | A whole-number label, defaulting to zero, reserved for future use. |

## 7. Movement, sensing, energy, and splitting — the exact rules

- **Movement:** exactly one grid cell in exactly one of six directions per step (left, right, forward, back, up, down), or no movement at all ("stop"). A node never moves more than one cell in a single step.
- **Sensing:** a node may only check facts about its immediate neighbors — whether they're alive, their energy, whether they're bonded, and their type. It cannot see or react to anything farther away.
- **Energy:** every action (moving, sensing, splitting) costs a fixed, whole-number amount of energy. A node whose energy drops to zero or below dies and becomes inert. Energy can only be replenished by an explicitly written rule (for example, contact with a resource cell).
- **Splitting:** a node may split into two new nodes only when energy is high enough, pressure has crossed a specific whole-number threshold, and at least two neighboring cells are empty. The original node becomes inert; the two new nodes divide the remaining energy exactly, using whole-number division with no remainder lost.
- **Bonding:** two neighboring living nodes may bond if both are switched on for it. Bonded nodes can share energy, using exact whole-number division, so no fractional energy is ever created.
- **Randomness:** used only for breaking ties (e.g., choosing left vs. right when both are equally valid) and is always a simple, fixed-range draw — never a smoothed probability.

## 8. How a step actually runs, in order

Every simulation step follows the same fixed order, every time, with no step allowed to "see into the future":

1. Check that every stored value is still a valid whole number or allowed label.
2. Kill any node whose energy has run out.
3. Freeze which cells are occupied for this step.
4. Let every living node decide its action, one at a time, in a fixed order.
5. Apply deaths from this step.
6. Apply the energy cost of sensing or holding still.
7. Line up all movement and splitting requests.
8. Resolve cases where two nodes want the same cell.
9. Apply the energy cost of any movement that actually succeeded.
10. Carry out any splits that were approved.
11. Update pressure values.
12. Apply bonding, if it's switched on.
13. Apply any resource pickup, if it's switched on.
14. Do a final sanity check that nothing broke the rules.

## 9. What counts as "part of the rulebook" — the validation rule

A behavior only becomes part of the frozen rulebook once **all** of the following are true:

1. It is written out as an explicit rule in this document (not just implied by example code).
2. There is an exact test with a known input and a known, expected output.
3. If the rule involves randomness, the test states the random seed and the exact order random numbers are drawn in.
4. The document says whether the rule is "closed" (nothing created or destroyed, like energy staying constant) or "open" (something is allowed to be created, like energy from an outside resource).
5. The rule has passed its test against the current frozen rulebook.
6. Any behavior added later gets a new version number — it never silently merges into this frozen version.

## 10. Earlier experimental version — kept for history only

An earlier version tried to describe every node property using only single bits (-1, 0, or +1) instead of general whole numbers. That version ran into an unresolved problem: a single unit of energy could not be split between two children without inventing a new rule on the spot. Because of this open problem, that version is **not** treated as an equal, finished alternative to the frozen rulebook above. It is kept only as a historical exploratory record — see Appendix F.

---

# PART III — 🔒 THE MAZE TEST (Stage 10)

## 11. What the maze test is for

The maze is not a theory — it is a **bounded, repeatable test** of whether nodes following the rulebook can actually do something useful. Specifically, it checks whether a scout can:

- Explore a 20×20 maze with no route given in advance.
- Encounter and recover from dead ends and wrong turns.
- Find a target cell.
- Build a usable route record connecting the target back to base.
- Have that route record actually read correctly, in both directions, by an independent auditor.
- Let a follower reuse the route without changing it.

## 12. The four roles, kept strictly separate

| Role | What it does | What it must never do |
|---|---|---|
| **Scout** | Explores the maze and writes down what it finds. | Does not know the answer in advance. |
| **Route record** | The specific part of what a scout wrote down that a completed round trip has proven works. | Is not the same as every mark a scout ever made — wrong turns don't count. |
| **Auditor** | A separate check that tests whether the route record can actually be followed from base to target and back. | Is not a moving node — it's a test, not an agent. |
| **Follower** | Uses the frozen route record to travel. | Never modifies or adds to the route record. |
| **Setup check** | Confirms, before the test even starts, that a valid path physically exists in this maze layout. | Is not something any node does during the run — it is external bookkeeping only. |

This last distinction matters: it is completely acceptable for the test harness to check maze validity ahead of time using an outside, "see the whole maze" method. That does **not** mean the scout itself is allowed to see the whole maze. The scout only ever senses its immediate surroundings, per Section 7.

## 13. The result, stated narrowly and precisely

> Under the fixed conditions of the Stage 10 maze test, a scout following the frozen rulebook was able to find a target, build a connected and usable route record, have that record read correctly by an independent auditor going out and coming back, and let a follower retrace the route without corrupting it.

This is a specific, bounded result. It is **not** the same as saying the rulebook is proven correct in general, or that the same result would hold in a different maze, a different domain, or at a larger scale.

## 14. Known limits of this result — stated plainly, not buried in a footnote

- Only 330 of 450 planned test rows were actually run; the remaining 120 were never executed.
- One known timing quirk (some exploration marks got re-triggered after a successful run, called the "success-edge re-trigger issue" going forward — replacing the earlier name "ScreamOnSuccessEdges") affected 12 of the 330 rows (about 3.6%), adding two extra marks each. It did not cause any of those runs to fail, but it is an open, unresolved wrinkle, not a solved one.
- Passing this diagnostic test is not the same as a full, exhaustive proof — it shows the behavior works under the tested conditions, not under all possible conditions.
- The auditor's "does it find the way" check is a reading test, not a proof that the route is the shortest or most efficient one possible.
- The measured route length reflects whatever the scout actually reinforced, not necessarily the shortest path that could exist.
- All of this evidence is specific to this maze's shape and size — it says nothing, by itself, about mazes of a different shape or a completely different kind of problem.

## 15. Actual measured outcome, for the record

Out of 330 measured test rows:

- **317 rows (96.1%)** fully met the checklist — On Target.
- **12 rows (3.6%)** met the checklist with one documented, bounded caveat (the success-edge re-trigger issue above) — Caution.
- **1 row (0.3%)** failed because the scout never found the target at all in that specific trial (fixture "F3_close_corner," seed 2, R=5) — Limited, specifically a discovery failure, not an auditor failure.

No row fell into the two more serious risk labels (Serious or Failed).

---

# PART IV — 🔒 THE SCORER (Specificity Engine)

## 16. What the scorer does and does not do

The scorer is a completely separate tool from the rulebook and the maze. It takes a finished maze result and grades it against a written checklist. **It never re-runs the maze, and it never changes the rulebook.** Its only job is measurement and record-keeping.

## 17. How a target checklist works

A target checklist is a numbered list of conditions. Each condition (checklist item) specifies:

- What piece of the result it looks at.
- What kind of comparison it performs — exact match, a numeric value within a tolerance, overlap between two sets, or how well two sequences line up.
- How important that item is, expressed as a positive weight.

The **match score** is the weighted fraction of checklist items that were satisfied (a number from 0 to 1). The **gap score** is simply 1 minus the match score. A match score of 1.0 means every checklist item was fully satisfied; anything less quantifies exactly how far short the result fell, and on which items.

## 18. The result slip — a permanent, tamper-evident record

Every time the scorer grades something, it produces one **result slip**. A result slip is created once and is never edited afterward — if you want to re-score something differently, you write a brand-new checklist and get a brand-new slip. Each slip records:

- Which checklist and version was used.
- Which specific result was measured, and when.
- The score on every individual checklist item.
- The overall match score and gap score.
- Any caveats found during scoring.
- A cryptographic fingerprint of the whole slip, so that any later tampering — even changing a single character — is detectable.

## 19. Risk labels

The scorer assigns one of five risk labels based on how far a result sits from its checklist, and what kind of gap caused it:

| Risk label | Meaning | What normally happens next |
|---|---|---|
| **On Target** | Every checklist item was satisfied. No caveats. | Safe to build on. |
| **Caution** | One or more small, documented caveats exist, but the result still functionally works. | Pause and review, but don't discard. |
| **Limited** | The result works for its core purpose, but one or more checklist items were not satisfied. | Pause; do not build further on this result until it's resolved. |
| **Serious** | A checklist item that should have passed is failing. | Reverse; investigate before doing anything else with this result. |
| **Failed** | A core assumption behind the checklist was broken entirely (for example, a follower corrupted a route it should never have touched). | Reverse and rebuild; do not use this result at all. |

## 20. Four separate questions — never merge these

This is the second most important frozen rule in the whole project, after Section 5. Four different questions get four different, independent answers. Mixing them together loses information and creates false confidence or false alarm.

| Question | Possible answers | Belongs to |
|---|---|---|
| How far is this result from its checklist, structurally? | On Target / Caution / Limited / Serious / Failed | Risk label |
| What does the evidence currently show? | Backed / Unclear / Contradicted | Evidence status |
| What are we going to do about it? | Proceed / Pause / Reverse | Decision |
| How is the rulebook itself currently moving? | Extend / Sense / Restrict | Process state |

For example: a result can have evidence that is **Backed** (the evidence is solid) while the decision is still **Pause** (because of one Caution-level caveat that needs review first). Or evidence can be **Unclear** while the decision is still **Proceed**, because the open question is judged low-risk and bounded. Collapsing these four questions into one label would make it impossible to reason about evidence, decisions, and mechanics independently — so this document never does that, anywhere.

## 21. Result slip integrity and the ledger

Every result slip, once created, is appended to a permanent, ordered **ledger**. Each entry is linked to the one before it using a cryptographic chain, so that the entire history can be **replayed**: re-checked from the very first entry to confirm nothing was changed, removed, reordered, or forged. Replay independently re-checks the math on every slip, re-checks every risk-label decision, and re-checks every link in the chain. If anything fails, replay says exactly where and why.

## 22. Status of the scorer itself

The scorer is a finished, working piece of software. What is **not yet proven** is whether its specific weights, thresholds, and risk-label cutoffs are the *correct* ones outside of the one maze checklist they were built and tested on. Applying the same scorer to a brand-new domain requires writing a brand-new target checklist for that domain — the scoring machinery carries over, but the specific numbers do not.

---

# PART V — 🧪 WHAT THE VISUAL DEMOS ADDED

The interactive HTML prototypes did not create new frozen results. What they *did* do is clarify, visually, several design ideas that are worth carrying forward as exploratory findings.

## 23. Check the manifest before anything runs

The strongest idea to come out of the demos is a simple sequencing rule: **the checkpoint has to happen before the thing being checked is allowed to act, not after.**

The intended sequence is:

1. An item arrives.
2. Its manifest (its self-declared description) is checked first.
3. The correct target checklist and policy for this item are identified.
4. A Let In / Hold / Reject decision is made.
5. Only items marked "Let In" ever reach the live system.
6. A result slip records the decision.
7. Only after all of that does the item actually get to run or take effect.

This is a stronger and more useful idea than simply showing a maze — it shows *where* a checkpoint belongs in a pipeline: before the action starts, not after the outcome is already known.

## 24. Three genuinely different reasons something might be blocked

The demos made clear that "blocked" is not one single condition — it can mean three different things, and mixing them together hides useful information:

- **Hold** — the manifest is missing or incomplete. Nothing runs yet. The item can be reviewed, fixed, and resubmitted.
- **Reject** — the manifest is contradicted, tampered with, or explicitly disallowed. Nothing runs. The result slip records exactly why.
- **Let In** — the manifest checks out. The item is allowed to proceed, and normal operation (in the maze's case, the scout beginning to explore) begins.

**Caution for future UI work:** any visual display of these three states may use colors, icons, or friendly labels, but it must never redefine what Hold, Reject, and Let In formally mean.

## 25. Exploration marks are not the same as a proven route

The visual maze made an easy-to-miss point obvious: if every mark a scout ever makes is shown the same way, a viewer will wrongly assume every explored cell is part of the "real" path. Going forward:

- Exploration marks (including wrong turns and dead ends) should stay visible, but visually distinct, as historical evidence.
- Only a completed, successful round trip should freeze a route record.
- Followers should only ever be shown following the frozen route record — never raw exploration marks.
- Followers must not be able to add to or reinforce the route record.

## 26. A result display needs to show its reasoning, not just a color

A single colored status light is not enough information. Any display of a result should show, at minimum: what item was checked, its manifest status, which checklist and policy version were used, the individual checklist scores, the match and gap scores, the risk label, the evidence status, the decision, the process state, any caveats, a unique slip identifier, and whether anything was actually allowed to execute.

## 27. Four layers need to stay visually separate

Earlier prototype screens sometimes compressed everything onto one view, which made it look like a single mechanism instead of four cooperating ones. Going forward, any visual or written explanation should keep these four layers clearly labeled and separated:

1. Intake checkpoint (Let In / Hold / Reject)
2. What the node/agent is actually doing (rulebook mechanics)
3. Measurement and scoring (checklist, match score, risk label)
4. The permanent record (result slip and ledger)

---

# PART VI — 🧪 THE APPLIED IDEA (Guardian)

## 28. What Guardian is

Guardian is a **proposed application**, not a new frozen result. It takes the same idea used for grading a maze result — "compare something to a declared checklist and produce a scored, recorded decision" — and applies it to a different problem: deciding whether an incoming AI-related file, dataset, or piece of code should be allowed into a company's systems at all.

Guardian's proposed job:

- Receive an incoming item.
- Read its manifest (self-declared description) and metadata.
- Apply a written, deterministic intake policy.
- Produce a recorded Let In / Hold / Reject decision.
- Keep disallowed material away from the model, its retrieval store, its memory, and any downstream tools, before any of those ever see it.

## 29. How Guardian relates to the frozen parts of this project — stated exactly once, so it never needs restating

> Guardian does not prove anything about the rulebook, and the rulebook does not, by itself, prove anything about Guardian's claims for enterprise use. Guardian is a proposed application built on top of the shared pattern used throughout this project: explicit local rules, a declared checklist, deterministic scoring, four separated decision questions (Section 20), tamper-evident result slips, and change only through an explicit, versioned extension.

Any enterprise, security, or compliance claim about Guardian is, by the classification in Section 3, **shown but not yet broadly proven** — it belongs in the exploratory bucket until it has its own dedicated tests, the same way the rulebook only became frozen after passing its own tests.

---

# APPENDICES

Every appendix carries its own status banner. Appendices are reference material and reproducibility support — the numbered Parts above are the authoritative summary. If an appendix ever appears to disagree with a Part above, the Part above wins, and the appendix should be corrected to match.

## Appendix A — 🔒 FROZEN NORMATIVE SOURCE: the rulebook

The full rule source lives in `Natural_Math_v5_-_Frozen_Integer_Base_and_Validation_Record.md` (identical content also exists as `Natural_Math_v5_-_Status_Frozen_Int.txt`). Both are frozen at the same version. See the Artifact Register (Appendix I) for exact fingerprints.

Key restated boundary, from the source: a conforming implementation must use integer state, integer counters, finite lists, exact if/else rules, discrete random draws, one-cell movement, and explicit local state only — and must not use decimal/floating-point stored values, hidden continuous fields, unstated smoothing, non-local planning, outside intuition, or any behavior not written in the document.

## Appendix B — 🔒 FROZEN DIAGNOSTIC EVIDENCE: Stage 10 maze test summary

- **Rows measured:** 330 of 450 planned.
- **Mean match score:** 0.9936.
- **On Target:** 317 rows (96.1%).
- **Caution:** 12 rows (3.6%) — all carrying the success-edge re-trigger caveat (2 extra marks each; did not cause failure).
- **Limited:** 1 row (0.3%) — fixture F3_close_corner, seed 2, R=5; discovery failure (scout never found the target), not an auditor failure.
- **Evidence status:** Backed on 329 rows (99.7%); Unclear on 1 row (0.3%).
- **Decision:** Proceed on 317 rows (96.1%); Pause on 13 rows (3.9%).

Sample result slip (one row, reformatted from the raw ledger for readability):

```
Checklist:        NaturalMath_Stage10_MazeBoundary, version v6.18-S10
Case:             F1_close_original, seed=0, R=5
Match score:      1.0000        Gap score: 0.0000
Risk label:       On Target
Evidence status:  Backed         Decision: Proceed
Checklist items:  all 8 satisfied (discovery, route reaches target,
                   auditor out-trip, auditor return-trip, follower
                   recall above threshold, no follower contamination,
                   no re-trigger marks, auditor finished within budget)
Caveats:          none
```

The complete raw ledger (330 result slips) is the companion file `stage10_specificity_receipts.jsonl`. It is not reproduced in full here — this appendix is the summary; the JSONL file is the reproducibility package.

## Appendix C — 🔒 IMPLEMENTED, DOMAIN VALIDATION INCOMPLETE: the scorer's technical contract

The scorer's current version (internally "v0.3") is fully implemented and self-consistent: checklist schema, the four comparison types (exact, numeric-with-tolerance, set-overlap, sequence-similarity), match/gap score math, risk-label policy, result-slip schema, and ledger replay rules. What is *not* yet independently validated is whether its specific weights, thresholds, and risk-label cutoffs generalize correctly outside the one maze checklist they were tested against — each new domain needs its own checklist and its own validation pass.

## Appendix D — 🧪 VISUAL PROOF OF CONCEPT, NON-NORMATIVE: HTML prototype findings

Four interactive HTML files exist as design sketches:

| File | What it demonstrates |
|---|---|
| `guardian_audit_receipt_demo.html` | What a compliance-style result slip could look like, including a JSON export view. |
| `guardian_enterprise_intake_gateway_v01.html` | A mocked-up enterprise "AI intake firewall" flow with sample compliance scenarios. |
| `guardian_intake_gateway_prototype.html` | An early, more literal version connecting an intake checkpoint directly to a maze unlock. |
| `natural_math_governance_maze_lab_field_mode.html` | A live-feeling maze field paired with a governance/result-slip side panel. |

Findings from these prototypes are recorded, by category, in Part V above (Sections 23–27). Each finding there is labeled as observed-in-demo, not as a validated result — none of these files constitute a test with a pass/fail oracle.

## Appendix E — 🧪 APPLICATION PROTOTYPE, NOT PRODUCTION VALIDATED: Guardian architecture

Guardian's proposed flow: item arrives → manifest and metadata inspected → deterministic intake policy applied → Let In / Hold / Reject decision recorded as a result slip → only "Let In" items reach the model, retrieval store, memory, or downstream tools. See Part VI for the full description and its explicit non-transfer statement (Section 29).

## Appendix F — 🧪 UNFROZEN MECHANISMS AND OPEN QUESTIONS

Anything in this appendix is an idea, not a result. Each entry uses the same five-field template so status is never ambiguous.

**Template:** Proposal · Reason it might help · Current evidence · Risk if adopted without testing · What test would settle it.

1. **Earlier bit-only version of the rulebook** (all fields limited to -1/0/+1). *Reason:* simplicity. *Evidence:* an early draft exists. *Risk:* it cannot currently split one energy unit between two children without an unwritten new rule. *Test needed:* a written, explicit splitting rule for single-bit energy, then a matching test — until then it stays historical only, per Section 10.
2. **Resource "beacon" signaling between nodes.** *Reason:* could speed up discovery. *Evidence:* none run. *Risk:* could silently become non-local sensing, violating Section 5. *Test needed:* explicit range-limited rule plus a maze re-run.
3. **Route pruning / shortening after discovery.** *Reason:* current route length reflects exploration, not necessarily the shortest path (Section 14). *Evidence:* none. *Risk:* could quietly require non-local planning. *Test needed:* explicit local pruning rule and a length-comparison test.
4. **Capped negative reinforcement for bad paths.** *Reason:* could discourage reuse of dead ends. *Evidence:* none. *Risk:* uncapped versions could runaway-accumulate. *Test needed:* explicit cap value and an accumulation test.
5. **Fix for the success-edge re-trigger issue (Section 14).** *Reason:* it's the one open caveat in an otherwise clean result set. *Evidence:* affects 12 of 330 rows, bounded, non-fatal. *Risk:* low as-is, but unresolved. *Test needed:* a timing-order fix plus re-run of the affected fixtures.
6. **Validation of the remaining 120 unrun maze rows.** *Reason:* completeness. *Evidence:* none yet — simply not run. *Risk:* none known, just untested. *Test needed:* run them under the same frozen rulebook and scorer.
7. **Multiple simultaneous scouts.** *Reason:* more realistic exploration. *Evidence:* none. *Risk:* new contention/race rules would be needed. *Test needed:* explicit multi-scout step-order rule and dedicated maze fixtures.
8. **Cross-domain checklists** (using the scorer outside the maze — including for Guardian). *Reason:* this is the whole point of Guardian. *Evidence:* demo-level only (Appendix D). *Risk:* weights/thresholds may not transfer; treating demo confidence as validated confidence would be overclaiming. *Test needed:* a written target checklist for the new domain plus its own oracle-backed test suite, exactly as Stage 10 has now.
9. **Physical robot or dynamic-obstacle versions.** *Reason:* real-world applicability. *Evidence:* none. *Risk:* introduces continuous sensors, which conflicts with Section 5 unless explicitly re-scoped as a new version. *Test needed:* a new, separately labeled version of the rulebook for physical/continuous input.

## Appendix G — 🧪 REJECTED APPROACHES AND NEGATIVE RESULTS

Recorded so this project doesn't quietly re-attempt something already ruled out.

- An earlier, broader "cell marking" approach was too broad to give a clean signal and was replaced by the current edge-based marking.
- An earlier version of edge marking did not correctly resolve maze boundaries and was replaced.
- Uncapped positive marking was rejected because it risks runaway accumulation with no natural limit.
- A purely "follow the strongest signal" auditor strategy was rejected as a general rule, because it can favor the loudest signal over the actually-correct route.
- Visually clean demo output was explicitly rejected as a stand-in for a real oracle-backed test — a demo looking convincing is not evidence.
- A route that successfully reaches the target was rejected as "sufficient success" on its own — the round trip and the follower test are both required.

## Appendix H — Terminology crosswalk (for translating older files)

This restates the Section 2 glossary as a quick lookup so anyone reading an older source file can translate it on sight.

| If an older file says... | This document calls it... |
|---|---|
| "The AI learned the maze" | "The scout built a tested route record" |
| "Memory" | "Persistent local state" or "the frozen route record" |
| "Knows" | "The evidence shows" (evidence status) |
| "Thinks" / "decides" (about the rulebook) | "Applies a transition rule" |
| "Decides" (about governance) | "Produces a decision" (Proceed/Pause/Reverse) |
| "Proves Natural Math" | "Supplies evidence under the tested maze conditions" |
| "Perfect path" / "shortest path" | "Route record" (call it "shortest" only if formally measured) |
| "Bad path" | "Unsuccessful exploration branch" |
| "Global signal" | Only ever use with its exact range and storage location stated |
| "Safe" | "Policy-compliant against the declared checklist" |
| "Frozen" | "Version-locked; changes only via documented corrections or a new version number" |
| "Validated" | Always name which specific test(s) it passed |
| "Demonstrated" | "Shown in a prototype, not yet backed by a passing test" |
| GSR / NGR | Match score / Gap score |
| MeasurementReceipt | Result slip |
| Structural Debt (OPERATIONAL/CAUTION/CONSTRAINED/CRITICAL/EXCEEDED) | Risk label (On Target/Caution/Limited/Serious/Failed) |
| Cognitive Basin epistemic state (SUPPORTED/UNRESOLVED/CONTRADICTED) | Evidence status (Backed/Unclear/Contradicted) |
| Cognitive Basin action state (EXTEND/HOLD/RETRACT) | Decision (Proceed/Pause/Reverse) |
| Natural Math process state (EXTEND/SENSE/RESTRICT) | Process state (Extend/Sense/Restrict) |
| SpecificityTarget / TargetFeature | Target checklist / Checklist item |
| Specificity Engine | Scorer |
| SpecificityLedger | Ledger |

**Note on the process-state name collision:** "Extend" appears in both the rulebook's process state and in the governance decision. These are two different scales answering two different questions (Section 20) and are never the same value by coincidence — always state which one you mean by pairing it with its category ("process state: Extend" vs. "decision: Proceed" — note the decision layer uses Proceed/Pause/Reverse specifically so it is never visually confused with the process-state layer's Extend/Sense/Restrict).

## Appendix I — Artifact register

| File | Status | SHA-256 |
|---|---|---|
| `Natural_Math_v5_-_Frozen_Integer_Base_and_Validation_Record.md` | 🔒 Frozen rulebook (normative) | `06a4b40615d664ab2d69a983810e679cc55683a180268c92359e8eeebc66270a` |
| `Natural_Math_v5_-_Status_Frozen_Int.txt` | 🔒 Frozen rulebook (identical content, alternate file) | `e5ab47d41b82f6af573866be637bf3b0054d96c7f45a613ec6cae2124ad84c7b` |
| `__Natural_Math_v6___Integer_Turing.txt` | 🧪 Exploratory reformulation, not the normative source | `2c73c21cee464cd202c9c61f0be52cc6268c91ce8610ecd82220665012504b54` |
| `__Natural_Math_v6___Binary_Turing_C.txt` | 🧪 Exploratory, historical only (unresolved splitting problem — Appendix F.1) | `f99ee57c8f7fe4eb65689247fe4326492e1fd0f00d3d6c2f2318b80ffcc9eaa0` |
| `stage10_specificity_reference.txt` | 🔒 Frozen bridge documentation (v0.1, superseded in terminology by this document, but result numbers still authoritative) | `a928a14f6bcd4a668a964b35b7647dccb4dc095fa5b386d8fba9122ece8aa3c8` |
| `stage10_to_specificity_poc.py` | 🔒 Frozen scoring script that produced the Stage 10 result slips | `ce088c3e076e4c6687189f9146a58a918729b2751e0704e72bb2f9ceb284d45f` |
| `stage10_specificity_receipts.jsonl` | 🔒 Frozen raw ledger (330 result slips) | `85b2a65c666026e5e094d8297f0c8e3c7cde00b2c5bf8844c71b0ecbd295173b` |
| `specificity_engine_v0_3.md` | 🔒 Scorer technical contract (implemented; cross-domain validation incomplete — Appendix C) | `7234d09aece57f79b38b9af50c8fb96b6d298d9c05e0da4b94f52bf92a7a123d` |
| `guardian_audit_receipt_demo.html` | 🧪 Visual prototype | `1ba36e0914c19015a413e76245f14b593d7009e590a87fe2ceffc4d1750ec682` |
| `guardian_enterprise_intake_gateway_v01.html` | 🧪 Visual prototype | `14385e4711d10277aec37b00fb75cdc06f1c8b1f98a6e52a4ac63d56acbc48ea` |
| `guardian_intake_gateway_prototype.html` | 🧪 Visual prototype | `db25ff50e55b5233652c010c7954e01fadb0346b409de5e4da088201ff9dcb76` |
| `natural_math_governance_maze_lab_field_mode.html` | 🧪 Visual prototype | `e78b7e2350d3d193d363559e15b57dbb25349d05de9e60869473ab4fe417807f` |

Two pairs of files in the original upload set were byte-for-byte duplicates (an "_EXPORT" copy alongside the original) and are treated as one artifact each above: `stage10_specificity_reference.txt` / `stage10_specificity_reference_EXPORT.txt`, and `stage10_to_specificity_poc.py` / `stage10_to_specificity_poc_EXPORT.txt`. `stage10_specificity_receipts_EXPORT.txt` is likewise identical to `stage10_specificity_receipts.jsonl`.

---

## The one rule that governs edits to this document going forward

Every new sentence added to this paper must be written with one of the two banners from the top of this document in mind — 🔒 **FROZEN** (only if it's backed by a passing, written test) or 🧪 **EXPLORATORY** (everything else, including anything that "looks like it's working" in a demo). If it's not obvious which one applies, it defaults to 🧪 **EXPLORATORY** until proven otherwise. This is what keeps unfinished ideas from quietly becoming treated as settled fact.

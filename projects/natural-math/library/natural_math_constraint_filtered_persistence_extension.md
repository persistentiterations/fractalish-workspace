# Natural Math Experimental Extension: Constraint-Filtered Persistence and Relay Keepers

**Status:** Experimental; not part of the frozen Natural Math base.

## Proposed mechanism

Natural Math studies how finite local actors convert locally sensed differences into persistent structure through constrained action, consequence, and feedback.

The maze implementation tests this loop:

1. **Difference:** adjacent passages differ in local signal, prior use, and known risk.
2. **Local sensing:** the scout reads only adjacent passages, local marks, movement reserve, and keeper state.
3. **Constraint:** walls, dead-end records, tried branches, and safe-return requirements remove actions before scoring.
4. **Selection:** the remaining safe branch is ranked by an imperfect local beacon.
5. **Persistence:** tried branches, dead ends, keepers, relay anchors, and completed routes remain.
6. **Feedback:** these records change later available actions.

## Functional persistence rule

A persistent record counts as functional only when later actors can encounter it locally and it changes their available actions or improves a measurable outcome.

- Failed branches are **restrictive memory** and are removed from the choice set.
- A keeper's untried safe branch is **obligatory memory** and must be attempted before retreat.
- A weak beacon is **advisory information** and ranks only the branches that remain after constraints.

## Relay keeper rule

Keeper-only exploration must return to the original base. This creates a hard reach limit: distant regions cannot be explored safely when the round-trip distance exceeds the sortie budget.

A relay keeper is a stationary, connected decision point that can hold supplies or support another scout. A later sortie may begin from that keeper with a replenished local budget, provided the known keeper chain remains connected to base.

The relay does not reveal the maze, resource route, or future branches. It changes the safe reference point for return.

## Preliminary Python evidence

A deterministic Python harness compared three policies on the same 300 generated caves:

| Policy | Completed | Completion rate | Mean completed-case movement | Mean route / global shortest |
|---|---:|---:|---:|---:|
| Blind deterministic explorer | 300/300 | 100.0% | 224.4 | 1.273 |
| Persistence, return to original base | 40/300 | 13.3% | 464.9 | 1.041 |
| Persistence with relay keepers | 259/300 | 86.3% | 507.1 | 1.121 |

The blind explorer had a much larger total allowance and no survival requirement. Its 100% completion rate is therefore not a direct safety-equivalent victory. The original-base persistence policy was safe but too conservative. Relay keepers recovered much of the lost reach, but did not yet match the blind explorer's completion rate and required more movement.

Across the relay-policy runs:

- 2,233 keeper-driven branch switches occurred.
- 119 safe branch opportunities were blocked by reserve limits.
- No failed branch was re-entered after being classified as failed.
- Completion by grid size was 47/50 for 15×15, 135/150 for 21×21, and 77/100 for 31×31.

These results support continued testing, not promotion into the frozen base.

## Promotion criteria

The extension should be considered for a new Natural Math version only if it:

1. Reproduces with an independent implementation.
2. Maintains zero repeated entries into restricted failed branches.
3. Preserves a connected return chain in every completed or safely aborted sortie.
4. Improves completion over the original-base persistence control across every maze size.
5. Reaches at least 95% completion on a frozen bank of 1,000 generated caves.
6. Reports total logistics cost separately from active scout movement.
7. Demonstrates that keeper records change later choices rather than merely being displayed.
8. Keeps audit and follower route integrity at 100% whenever a route is promoted.

## Required next tests

- Increase generated testing to at least 1,000 frozen cases.
- Sweep sortie budget, reserve, maximum sorties, and keeper placement policy.
- Compare junction-only relays with distance-based relay placement.
- Charge explicit supply and personnel costs for each relay.
- Remove or add local beacon noise to measure dependence on sensing quality.
- Test changing environments and invalidate stale restrictive memory.
- Test two simultaneous scouts sharing keeper state.

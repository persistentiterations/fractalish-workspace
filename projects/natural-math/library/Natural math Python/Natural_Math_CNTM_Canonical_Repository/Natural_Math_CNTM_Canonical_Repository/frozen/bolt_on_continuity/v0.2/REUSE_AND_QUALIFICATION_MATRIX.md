# Reuse and Qualification Matrix — Bolt-On Continuity for Docker v0.2 Stage 0

## Rule

Frozen v0.1 is a proven engine baseline, not a blanket approval for the v0.2 product. Every reused component must be named, bounded, equivalence-tested, and qualified inside the new lifecycle.

## Reuse candidates

| v0.1 capability | Initial v0.2 disposition | Required proof before use |
|---|---|---|
| Canonical serialization | Reuse unchanged candidate | Frozen-source or byte-for-byte behavior equivalence |
| Evidence normalization | Reuse unchanged candidate | Same accepted inputs, canonical outputs, and rejection behavior |
| Append-only receipt creation | Reuse unchanged candidate | Receipt schema, chain, and digest equivalence |
| Incident digest binding | Reuse unchanged candidate | Identical canonical digest fixtures |
| Deterministic replay | Reuse unchanged candidate | Live and replay terminal state/hash equivalence |
| `NO_ACTION` / `HOLD` / `RELEASE` representation | Reuse unchanged candidate | No new action values or aliases |
| Action-request schema and digest | Reuse unchanged candidate | Exact schema and canonical digest equivalence |
| Gateway independent validation | Reuse unchanged candidate | All v0.1 adversarial rejects remain rejects |
| Native dry-run planning | Reuse unchanged candidate | Exact full-ID command plan remains unchanged |
| Pause/unpause executor | Reuse unchanged candidate | Command ceiling and argument equality tests |
| Duplicate request protection | Reuse unchanged candidate | Restart and replay tests preserve rejection behavior |
| Failed `RELEASE` recovery | Reuse unchanged candidate | v0.1 recovery fixtures and new lifecycle recovery tests |
| Frozen verification tools | Reference only | Must never be altered by v0.2 |

No reuse candidate is approved merely because its source is copied. The preferred implementation must import or vendor an explicitly reviewed source boundary while retaining proof of equivalence to the frozen baseline.

## New v0.2 capabilities requiring independent qualification

| Capability | Required qualification themes |
|---|---|
| Prerequisite checker | Supported Docker/platform detection; unsupported environment rejection; no mutation |
| Guided installation | Clean install; repeat install; interrupted install; reversible changes |
| Container discovery | Eligible container listing; no authority from names; deterministic display ordering |
| Explicit enrollment | Full 64-character ID confirmation; wrong-ID rejection; replacement detection |
| Configuration writer | Canonical output; digest stability; safe defaults; no secrets |
| Configuration validator | Missing, extra, malformed, tampered, stale, and unsupported values fail closed |
| Observation-only default | Gateway disabled; projected actions cannot execute |
| CLI lifecycle | Start, status, stop, restart, and error reporting |
| Operator-readable explanation | Deterministic reason mapping; no claim that recommendation equals execution |
| Incident listing | Stable ordering; pagination/bounds if needed; corrupted records disclosed |
| Offline replay command | No Docker dependency; exact result and chain verification |
| Incident export | Complete bounded package; deterministic manifest; secrets excluded; digest verification |
| Approval and denial UI | Exact request binding; expiry; denial receipt; no implicit approval |
| Gateway enable/disable | Explicit operator action; persistent state; fail-closed restart behavior |
| Restart recovery | No duplicate action; no lost accepted decision; uncertainty rejects |
| Subject replacement | Same-name replacement detected; new enrollment required |
| Missing/stopped container | Clear report; no broadened action; deterministic receipts |
| Receipt-store failure | Corruption, disk-full, permissions, partial write, and recovery behavior |
| Retention/deletion choice | Explicit operator selection; bounded deletion receipt; no silent destruction |
| Uninstall | Product removal without container stop, mutation, or loss of independent operation |
| Clean-environment usability | A non-author operator completes the documented workflow |

## Qualification layers

Every implementation stage must preserve four separate forms of evidence:

1. **Structural verification** — files, schemas, boundaries, and prohibited imports or command surfaces.
2. **Deterministic fixture tests** — exact canonical outputs, receipts, digests, and replay results.
3. **Adversarial tests** — malformed, stale, duplicated, conflicting, tampered, ambiguous, and unsupported cases.
4. **Live disposable-container qualification** — only for stages that require Docker interaction, using explicitly disposable subjects.

## Frozen regression requirement

Before and after each v0.2 stage:

```powershell
python .\tools\verify_all_frozen.py
git diff -- .\frozen
```

Required result:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

The frozen diff must be empty.

## No silent inheritance

The following v0.1 facts do not automatically qualify v0.2:

- successful v0.1 installation instructions;
- usability by a new operator;
- clean-machine packaging;
- configuration migration;
- approval user experience;
- report readability;
- Windows and Linux product lifecycle;
- long-running service behavior;
- production operation;
- customer value or market demand.

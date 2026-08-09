# Bolt-On Demonstrator v0.3 — Stage 1

## Portable Adapter Contract

Stage 1 defines the host-neutral boundary that later adapters must obey. It does
not attach to a second live host and it executes no host action.

### Contract properties

- frozen v0.1 and v0.2 are read-only prerequisites;
- the frozen v0.2 release manifest is independently verified before and after qualification;
- adapters expose identity, event normalization, and action projection only;
- the adapter interface has no execute, apply, dispatch, or mutation method;
- the portable action vocabulary remains exactly `HOLD` and `RELEASE`;
- adapter capabilities are explicit and fail closed when out of scope;
- host-specific events become immutable canonical events;
- semantically equivalent events have an adapter-neutral semantic digest;
- adapter-bound event digests remain distinct across hosts;
- projections are bound to the adapter, request, subject, source event, and expected state;
- every valid Stage 1 projection must report `executed=False`;
- hidden execution claims are rejected;
- missing adapters fail closed;
- exact hash-chained receipts are independently replayed;
- receipt reordering and tampering are detected;
- all integer fields reject booleans and floating-point values;
- no file writing and no non-standard-library dependency.

The two included fixture adapters deliberately consume different raw event
shapes and produce different host-operation projections. They are contract
fixtures, not the Stage 2 independent host.

### Files

```text
portability/portable_adapter_contract.py
tests/test_portable_adapter_contract.py
README.md
README_STAGE_1.md
```

### Run Stage 1 qualification

From the canonical repository root:

```powershell
python .\development\bolt_on_demonstrator_v0_3\portability\portable_adapter_contract.py
```

Expected final line:

```text
STAGE 1 PORTABLE ADAPTER CONTRACT QUALIFICATION: PASS
```

### Run Stage 1 tests

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_3\tests `
  -p "test_*.py" `
  -v
```

Expected ending:

```text
Ran 34 tests

OK
```

### Verify all prior frozen releases

```powershell
python .\tools\verify_all_frozen.py
```

Expected final line:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

### Claim boundary

A Stage 1 pass proves that a finite, deterministic, fail-closed adapter contract
can preserve the v0.2 action and receipt boundaries while translating two
different fixture event shapes. It does not yet prove attachment to a second
independent host, cross-host replay equivalence, live substitution, production
security, or external-system safety.

Stage 2 should introduce a second independent deterministic host whose source,
data model, event model, and ordinary execution path are materially different
from the v0.1 job host.

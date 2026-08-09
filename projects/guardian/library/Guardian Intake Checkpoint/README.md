# Guardian Code Intake Checkpoint — Working Demo

This folder contains a local proof-of-concept for a manifest-first Python intake gate.

Guardian does **not** execute scanned code. It performs static checks, creates a result slip,
and appends the slip to a hash-chained JSONL ledger.

## Files

- `guardian.py` — runnable command-line tool
- `guardian_policy.json` — default policy
- `samples/clean.py` — expected result: LET IN, exit code 0
- `samples/hold_file_write.py` — expected result: HOLD, exit code 2
- `samples/reject_unsafe.py` — expected result: REJECT, exit code 3
- `samples/missing_manifest.py` — expected result: HOLD, exit code 2

## Run

From this folder:

```bash
python guardian.py --ledger guardian_ledger.jsonl scan samples/clean.py
python guardian.py --ledger guardian_ledger.jsonl scan samples/hold_file_write.py
python guardian.py --ledger guardian_ledger.jsonl scan samples/reject_unsafe.py
python guardian.py --ledger guardian_ledger.jsonl scan samples/missing_manifest.py
python guardian.py --ledger guardian_ledger.jsonl ledger
python guardian.py --ledger guardian_ledger.jsonl replay
```

## Optional HMAC protection

A plain hash chain detects accidental edits and simple tampering, but a person who can rewrite the
whole ledger can recompute an unsigned chain. Use an HMAC key to make recomputation harder:

Linux/macOS:

```bash
export GUARDIAN_HMAC_KEY="replace-with-a-long-random-secret"
python guardian.py --ledger signed_ledger.jsonl scan samples/clean.py
python guardian.py --ledger signed_ledger.jsonl replay
```

Windows PowerShell:

```powershell
$env:GUARDIAN_HMAC_KEY="replace-with-a-long-random-secret"
python guardian.py --ledger signed_ledger.jsonl scan samples/clean.py
python guardian.py --ledger signed_ledger.jsonl replay
```

The same key must be present during scan and replay.

## Important boundary

This is a working model, not a complete security product. Static analysis can miss obfuscated,
dynamic, native, generated, or indirect behavior. A production design should add quarantine,
archive inspection, signed policy distribution, stronger append-only storage, and a separate
sandboxed launcher that verifies an admission slip immediately before execution.

# Guardian 0.5 Quick Start

## 1. Validate the policy

```bash
python guardian.py validate-policy guardian_policy.json
```

## 2. Signed scan

Linux/macOS:

```bash
export GUARDIAN_HMAC_KEY="replace-with-a-long-random-secret"
python guardian.py --ledger guardian_ledger.jsonl scan samples/clean.py --explain
```

Windows PowerShell:

```powershell
$env:GUARDIAN_HMAC_KEY="replace-with-a-long-random-secret"
python guardian.py --ledger guardian_ledger.jsonl scan samples/clean.py --explain
```

## 3. Explicit local developer mode

```bash
python guardian.py --unsigned-dev --ledger dev_ledger.jsonl scan samples/clean.py
```

Unsigned developer mode is deliberately visible and is not intended for
production-adjacent use.

## 4. Verify the ledger

```bash
python guardian.py --ledger guardian_ledger.jsonl replay
```

Provide the same HMAC key to authenticate signed entries.

## Outcomes and exit codes

- `0`: LET IN
- `2`: HOLD
- `3`: REJECT
- `4`: scan or usage error
- `5`: policy error
- `6`: ledger error

# Bolt-On Demonstrator v0.2 — Stage 1

## Bounded Authority Contract and Dry-Run Gate

v0.1 proved that the bolt-on could observe, recommend, remember, replay, and
detach without changing the host. v0.2 begins the controlled path toward
bounded intervention.

Stage 1 does **not** execute interventions. It defines and qualifies the
contract that a later active gate must obey.

## Contract properties

- deny by default when no grant is present;
- one grant is bound to one governance-session digest;
- exact action scope: `ALLOW`, `HOLD`, and/or `DENY`;
- exact integer action budget;
- exact integer validity window;
- tampered grants fail closed;
- out-of-scope actions fail closed;
- expired and not-yet-valid grants fail closed;
- `UNKNOWN` always becomes `ABSTAIN`;
- duplicate or misnumbered requests are rejected;
- every request and outcome receives a hash-chained receipt;
- receipt replay and tamper detection are deterministic;
- executed actions remain exactly zero.

The grant SHA-256 hash is an integrity binding for this prototype. It is not a
production digital signature or identity-authentication mechanism.

## Files

```text
authority/bounded_authority_contract.py
tests/test_bounded_authority_contract.py
README_STAGE_1.md
STAGE_1_VERIFICATION.txt
```

## Install

From the canonical repository PowerShell window:

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\Bolt_On_Demonstrator_v0_2_Stage_1.zip" `
  -DestinationPath ".\development\bolt_on_demonstrator_v0_2" `
  -Force
```

## Run Stage 1

```powershell
python .\development\bolt_on_demonstrator_v0_2\authority\bounded_authority_contract.py
```

Expected final line:

```text
STAGE 1 BOUNDED AUTHORITY QUALIFICATION: PASS
```

Fixed authority results:

```text
Host digest:
04d2438f1dbff0b0ddfe5e5eb6382f6623fbe1d18e92078bde8b8dc95bba1c8e

Governance digest:
71e72e0608272f485c6872ec7efb31f467f9bdc0d603373a95f443722b4a5075

Grant hash:
b080217ae79c6f5f88c585fb8e7546c211b148cc3acc78654ec56e27e230557f

Authority digest:
8bfb57659ceb61e090c4042b0d08102c83cba48072905f702a1169753ddeb675
```

The displayed frozen-v0.1 tree digest covers the complete installed release
folder. Treat it as an integrity value that must remain stable before and after
the run; the fixed contract digest above does not depend on local release
metadata.

## Run the 23 Stage 1 tests

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_2\tests `
  -p "test_*.py" `
  -v
```

Expected ending:

```text
Ran 23 tests

OK
```

## Verify all frozen releases

```powershell
python .\tools\verify_all_frozen.py
```

Expected final line:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

## Save Stage 1

```powershell
git add .\development\bolt_on_demonstrator_v0_2
git commit -m "Add v0.2 Stage 1 bounded authority contract"
git push origin main
git status
```

Expected final Git status:

```text
nothing to commit, working tree clean
```

## Claim boundary

A passing Stage 1 proves that authority can be represented as a finite,
session-bound, scope-bound, time-bound, budget-bound, replayable contract that
fails closed. It does not prove active host control, production-grade identity,
cryptographic signatures, distributed authority, or safe intervention in an
external production system.

Stage 2 will introduce the first disposable mediated-host fixture. It will
permit only a narrowly authorized `HOLD` action and will compare the mediated
result against both the original host and the dry-run prediction.

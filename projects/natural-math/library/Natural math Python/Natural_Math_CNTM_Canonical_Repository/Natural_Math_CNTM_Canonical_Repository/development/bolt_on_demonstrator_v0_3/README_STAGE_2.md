# Bolt-On Demonstrator v0.3 — Stage 2

## Second Independent Host

Stage 2 attaches the Stage 1 portable adapter contract to a materially different
host implementation without modifying that host and without giving the adapter
execution authority.

The second host is a deterministic, versioned finite-state workflow engine. It
is structurally different from the earlier arithmetic job host:

- commands address task records rather than arithmetic jobs;
- host state is a set of versioned finite-state records;
- operations are `REGISTER`, `START`, `CHECKPOINT`, `PAUSE`, `RESUME`,
  `COMPLETE`, and `CANCEL`;
- every command uses an exact integer expected revision;
- every accepted or rejected command produces an immutable host-native event;
- the host has its own canonical run text and SHA-256 digest;
- the host imports no Natural Math, CNTM, governance, adapter, or bolt-on code;
- the host can run and qualify by itself.

The Stage 2 adapter observes the immutable workflow event ledger and maps:

- portable `HOLD` to host-native `PAUSE`;
- portable `RELEASE` to host-native `RESUME`.

These mappings are projections only. Stage 2 executes no host action.

## Files added

```text
hosts/workflow_state_host.py
portability/second_independent_host.py
tests/test_second_independent_host.py
README_STAGE_2.md
```

No Stage 1 file and no frozen release is modified.

## Stage 2 qualification properties

A passing Stage 2 requires all of the following:

- the frozen v0.2 release verifies before and after qualification;
- the exact qualified Stage 1 contract source remains bound and unchanged;
- the second host runs without importing the bolt-on;
- the host data model and lifecycle are materially different from the first host;
- direct host execution is deterministic;
- the host input command tuple is unchanged;
- the host output is identical before and after adapter observation;
- the adapter emits deterministic canonical events and projections;
- `HOLD` and `RELEASE` project to the correct host-native operations;
- every projected action reports `executed=False`;
- attachment receipts replay independently;
- receipt tampering is detected;
- all bound source files remain unchanged;
- executed actions remain exactly zero.

## Install Stage 2

From the canonical repository PowerShell window:

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\Bolt_On_Demonstrator_v0_3_Stage_2.zip" `
  -DestinationPath "." `
  -Force
```

## Run the independent host by itself

```powershell
python .\development\bolt_on_demonstrator_v0_3\hosts\workflow_state_host.py
```

Expected final line:

```text
SECOND INDEPENDENT HOST SELF-QUALIFICATION: PASS
```

## Run the Stage 2 attachment qualification

```powershell
python .\development\bolt_on_demonstrator_v0_3\portability\second_independent_host.py
```

Expected final line:

```text
STAGE 2 SECOND INDEPENDENT HOST QUALIFICATION: PASS
```

## Run the complete v0.3 test suite

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_3\tests `
  -p "test_*.py" `
  -v
```

Expected ending:

```text
Ran 76 tests

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

## Review before saving

```powershell
git status --short
```

Expected new Stage 2 paths:

```text
?? development/bolt_on_demonstrator_v0_3/README_STAGE_2.md
?? development/bolt_on_demonstrator_v0_3/hosts/
?? development/bolt_on_demonstrator_v0_3/portability/second_independent_host.py
?? development/bolt_on_demonstrator_v0_3/tests/test_second_independent_host.py
```

Do not commit until the complete host qualification, Stage 2 qualification,
76-test result, frozen verification, and repository status have been reviewed.

## Claim boundary

A passing Stage 2 proves that the portable contract can observe and project the
same bounded `HOLD`/`RELEASE` vocabulary against a second, materially different
host without changing the host or acquiring execution authority. It does not yet
prove equivalent-event replay between both live hosts, active host substitution,
production adapter safety, or safe control of an external production system.

Stage 3 will qualify equivalent-event cross-host replay.

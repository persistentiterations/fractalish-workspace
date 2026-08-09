# Stage 0 Verification and Advancement Gates

Stage 0 is complete only when the user has run and pasted evidence for every
required gate.

## Gate A — Correct repository state

```powershell
git branch --show-current
git status --short
git log -1 --oneline
```

Required:

- branch is `main`;
- working tree was clean before extraction;
- repository includes frozen v0.4 commit
  `0d6de321ccac75bf8d634663396a0a4279b72261`.

Verify ancestry:

```powershell
git merge-base --is-ancestor 0d6de321ccac75bf8d634663396a0a4279b72261 HEAD
if ($LASTEXITCODE -ne 0) { throw "Frozen v0.4 commit is not an ancestor of HEAD" }
```

## Gate B — Frozen releases verify before installation

```powershell
python .\tools\verify_all_frozen.py
```

Required final line:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

## Gate C — Install Stage 0 package

From the repository root:

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\Bolt_On_Continuity_for_Docker_v0_1_Stage_0.zip" `
  -DestinationPath "." `
  -Force
```

The archive creates only:

```text
products/bolt_on_continuity_v0_1
```

## Gate D — No operational product code

```powershell
Get-ChildItem `
  .\products\bolt_on_continuity_v0_1 `
  -Recurse `
  -File |
  Select-Object -ExpandProperty FullName
```

Required interpretation:

- only Markdown, JSON Schema, JSON configuration example, test, and verification files exist;
- no observer implementation;
- no Docker client;
- no gateway implementation;
- no pause or unpause execution;
- no listener or service installer.

## Gate E — Direct Stage 0 verification

```powershell
python .\products\bolt_on_continuity_v0_1\tools\verify_stage_0.py
```

Required ending:

```text
STAGE 0 PRODUCT CONTRACT VERIFICATION: PASS
```

## Gate F — Stage 0 tests

```powershell
python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_1\tests `
  -p "test_*.py" `
  -v
```

Required ending:

```text
Ran 12 tests

OK
```

## Gate G — Frozen releases verify after installation

```powershell
python .\tools\verify_all_frozen.py
```

Required final line:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

## Gate H — Frozen-tree diff is empty

```powershell
git diff -- .\frozen
git status --short
```

Required:

- `git diff -- .\frozen` prints nothing;
- status lists only new files beneath
  `products/bolt_on_continuity_v0_1`;
- no frozen, development demonstrator, or existing tool file is modified.

## Gate I — Schema validity and canonical examples

Covered by the Stage 0 verifier and unit tests:

- all schemas parse;
- schema identifiers are unique;
- action enumeration is exactly `HOLD`, `RELEASE`;
- request target requires immutable container ID;
- forbidden command fields are rejected by schema;
- additional properties are disabled for authority-bearing records;
- canonical JSON examples are stable;
- product configuration defaults to action projection disabled.

## Advancement rule

Do not begin Stage 1 and do not commit until Gates A–I pass and the outputs have
been reviewed.

Stage 1 may add only a read-only Docker observation adapter, its fixtures, tests,
and documentation. Stage 1 must not add action projection or a write-capable
Docker connection.

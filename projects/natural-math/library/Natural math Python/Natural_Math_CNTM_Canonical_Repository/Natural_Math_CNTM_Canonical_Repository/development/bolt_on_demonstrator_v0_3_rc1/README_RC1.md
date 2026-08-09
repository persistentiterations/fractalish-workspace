# Bolt-On Demonstrator v0.3 — Stage 6 / RC1

## Portability Qualification and Release-Candidate Approval

Stage 6 qualifies the completed v0.3 development tree for a later, separate
freeze procedure. It does **not** create `frozen/bolt_on/v0.3`, modify an existing
frozen release, or extend the aggregate frozen verifier.

The required source baseline is:

```text
0e92ecaca48c4c5bf85bab658a4e693aae3d36f6
Add v0.3 Stage 5 adversarial adapter qualification
```

## Qualification procedure

The RC1 procedure performs two complete passes over:

1. Stage 1 portable adapter contract;
2. independent workflow-host self-qualification;
3. Stage 2 second-host attachment;
4. Stage 3 equivalent-event cross-host replay;
5. independent queue-host self-qualification;
6. Stage 4 live host substitution;
7. Stage 5 adversarial adapter qualification;
8. the complete exact-count v0.3 test suite;
9. the aggregate frozen-release verifier.

It requires:

- exactly 256 v0.3 tests;
- identical normalized evidence on both passes;
- both host families qualified;
- exactly one qualified live substitution;
- portable actions limited to `HOLD` and `RELEASE`;
- exactly two host-owned actions on the valid baseline;
- all 48 Stage 5 attacks safely rejected;
- zero attack-time host actions;
- zero bolt-on executed actions;
- no execution method on the portable adapter interface or adapter classes;
- all execution-authority constants fixed at `NONE`;
- frozen v0.2 manifest integrity;
- no development-tree or frozen-tree changes during qualification.

Console timing is normalized out of the second-pass comparison. Substantive
output, counts, receipts, replay digests, and other evidence remain bound.

## Generated approval record

A successful run creates:

```text
development/bolt_on_demonstrator_v0_3/RC1_QUALIFICATION.json
```

The record is canonical JSON with its own SHA-256 digest. It records the Stage 5
source commit, complete development manifest, complete frozen-tree manifest,
portable command evidence, exact test count, portability results, adversarial
results, structural authority scan, and approval for the separate freeze
procedure.

The expected v0.3 development manifest before the RC record is added is:

```text
48cf74381b3ab47be7cffb652da91c6a62a7532f2256c92619fe2ff750664b0b
```

## Install

From the canonical repository PowerShell window:

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\Bolt_On_Demonstrator_v0_3_Stage_6_RC1.zip" `
  -DestinationPath "." `
  -Force
```

The archive adds only the separate RC1 qualification package. The approval
record is created only after the direct qualification passes.

## Run the 46 RC1 package tests

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_3_rc1\tests `
  -p "test_*.py" `
  -v
```

Required ending:

```text
Ran 46 tests

OK
```

## Run RC1 qualification

```powershell
python .\development\bolt_on_demonstrator_v0_3_rc1\release_candidate\qualify_v0_3_rc1.py
```

Required final line:

```text
BOLT-ON DEMONSTRATOR v0.3 RC1 QUALIFICATION: PASS
```

Required fixed fields include:

```text
Release candidate: v0.3-RC1
Source commit: 0e92ecaca48c4c5bf85bab658a4e693aae3d36f6
Expected tests: 256
Observed tests: 256
Development manifest: 48cf74381b3ab47be7cffb652da91c6a62a7532f2256c92619fe2ff750664b0b
Frozen v0.2 manifest: e020199f5327866bfcbe34877466ea06558eb6650c578ce841c37b4c9abd159c
Second pass exact: True
Host families qualified: 2
Attacks rejected: 48
Prohibited action hits: 0
Approved for freeze procedure: True
```

The frozen-tree manifest and RC1 record digest are produced by the canonical
repository run and must be retained exactly.

## Review before saving

After qualification:

```powershell
python .\tools\verify_all_frozen.py
git status --short
```

Expected new paths:

```text
?? development/bolt_on_demonstrator_v0_3/RC1_QUALIFICATION.json
?? development/bolt_on_demonstrator_v0_3_rc1/
```

Do not create or modify `frozen/bolt_on/v0.3` during Stage 6.

## Save RC1

After reviewing the direct qualification, package tests, frozen verification,
approval record, and repository status:

```powershell
git add `
  .\development\bolt_on_demonstrator_v0_3\RC1_QUALIFICATION.json `
  .\development\bolt_on_demonstrator_v0_3_rc1

git commit -m "Add v0.3 RC1 portability qualification"
git push origin main
git status
```

Required final status:

```text
nothing to commit, working tree clean
```

## Claim boundary

A passing v0.3 RC1 qualifies the demonstrated portability architecture across
the two included host families and the enumerated substitution and adversarial
campaigns. It proves deterministic qualification evidence, exact replay, bounded
host-owned execution, and preservation of prior frozen releases within this
finite demonstrator.

It does not prove arbitrary-host compatibility, production network security,
production identity authentication, distributed consensus, resistance to every
possible attack, or safe deployment in an uncontrolled production environment.
The final v0.3 freeze must remain a separate explicit procedure and commit.

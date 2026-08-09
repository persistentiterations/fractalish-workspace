# Stage 2 Verification Gates

Start from clean commit:

```text
f830672 Add Docker continuity product v0.1 Stage 1 read-only observer
```

Run before extraction:

```powershell
python .\tools\verify_all_frozen.py
```

Extract the ZIP, then run:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_2.py

python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_1\tests `
  -p "test_stage_2_*.py" `
  -v
```

Required endings:

```text
STAGE 2 DETERMINISTIC INCIDENT LEDGER: PASS
```

```text
Ran 40 tests

OK
```

Re-run Stage 1 and Stage 0 verification and tests, then frozen verification.

Finally:

```powershell
git diff -- .\frozen
git status --short --untracked-files=all
```

The frozen diff must be empty and all changes must remain under the product tree.
Do not commit until every gate is confirmed.

# Stage 3 Verification Gates

Start from clean commit:

```text
a46405b Add Docker continuity product v0.1 Stage 2 incident ledger
```

Verify frozen releases, extract the Stage 3 ZIP, then run:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_3.py

python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_1\tests `
  -p "test_stage_3_*.py" `
  -v
```

Required endings:

```text
STAGE 3 BOUNDED ACTION PROJECTION: PASS
```

```text
Ran 44 tests

OK
```

Re-run Stage 2, Stage 1, and Stage 0 qualification and tests. Then verify all
frozen releases again.

Finally:

```powershell
git diff -- .\frozen
git status --short --untracked-files=all
```

The frozen diff must be empty and all changes must remain under the product tree.

Do not commit until every gate is confirmed.

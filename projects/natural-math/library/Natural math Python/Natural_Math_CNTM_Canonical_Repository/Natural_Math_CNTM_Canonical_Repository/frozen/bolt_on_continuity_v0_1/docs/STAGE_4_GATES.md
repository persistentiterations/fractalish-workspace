# Stage 4 Verification Gates

Start from clean commit:

```text
0c7900d Add Docker continuity product v0.1 Stage 3 bounded projection
```

Verify frozen releases, extract the Stage 4 ZIP, then run:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_4.py

python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_1\tests `
  -p "test_stage_4_*.py" `
  -v
```

Required endings:

```text
STAGE 4 HOST-OWNED GATEWAY DECISION CONTRACT: PASS
```

```text
Ran 48 tests

OK
```

Re-run Stage 3, Stage 2, Stage 1, and Stage 0 qualification and tests. Then
verify all frozen releases again.

Finally:

```powershell
git diff -- .\frozen
git status --short --untracked-files=all
```

The frozen diff must be empty and all changes must remain under the product tree.

Do not commit until every gate is confirmed.

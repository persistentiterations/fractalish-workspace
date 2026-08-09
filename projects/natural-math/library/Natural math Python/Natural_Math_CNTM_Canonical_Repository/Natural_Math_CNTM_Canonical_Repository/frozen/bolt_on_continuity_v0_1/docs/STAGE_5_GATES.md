# Stage 5 Verification Gates

Start from clean commit:

```text
c4f3e8f Add Docker continuity product v0.1 Stage 4 gateway contract
```

Verify frozen releases, extract the Stage 5 ZIP, then run:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_5.py

python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_1\tests `
  -p "test_stage_5_*.py" `
  -v
```

Required endings:

```text
STAGE 5 DRY-RUN NATIVE ACTION ADAPTER: PASS
```

```text
Ran 52 tests

OK
```

Re-run Stage 4 through Stage 0 qualification and tests, then verify all frozen
releases again.

Finally:

```powershell
git diff -- .\frozen
git status --short --untracked-files=all
```

The frozen diff must be empty and all changes must remain under the product tree.

Do not commit until every gate is confirmed.

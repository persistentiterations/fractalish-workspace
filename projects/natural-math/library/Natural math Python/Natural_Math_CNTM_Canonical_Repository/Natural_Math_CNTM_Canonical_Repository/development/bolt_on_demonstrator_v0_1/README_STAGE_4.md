# Bolt-On Demonstrator v0.1 — Stage 4

## Purpose

Stage 4 adds a finite CNTM shadow-memory layer beside the unchanged host,
observer, and Natural Math shadow-governance layers.

It stores exact evidence across runs while retaining no authority to change the
host. The memory rejects duplicate sessions and capacity overflow atomically,
preserves contradictory evidence, leaves UNKNOWN unresolved, and detects record
damage through deterministic replay.

## Added files

```text
memory/cntm_shadow_memory.py
tests/test_cntm_shadow_memory.py
README_STAGE_4.md
STAGE_4_VERIFICATION.txt
```

## Run Stage 4

From the canonical repository root:

```powershell
python .\developmentolt_on_demonstrator_v0_1\memory\cntm_shadow_memory.py
```

Expected final line:

```text
STAGE 4 SHADOW QUALIFICATION: PASS
```

## Run the complete Stage 1–4 suite

```powershell
python -m unittest discover `
  -s .\developmentolt_on_demonstrator_v0_1	ests `
  -p "test_*.py" `
  -v
```

Expected ending:

```text
Ran 55 tests
OK
```

## Verify frozen releases

```powershell
python .	oolserify_frozen.py
```

Expected:

```text
FROZEN VERIFICATION PASSED: 11 files
```

## Commit Stage 4

```powershell
git add .\developmentolt_on_demonstrator_v0_1
git commit -m "Add Stage 4 CNTM bounded shadow memory"
git status
```

## Fixed Stage 4 baseline

```text
Memory records: 10
Memory sessions: 1
Memory digest: 581b40271800046fe28519c290193b3c7209b697ee92ba1c7418a1116c70e2a7
CNTM v3.0F source hash: b65f5b88054b3a897d0ce0f577daf803c5f2f296349d7614be547e5d3e72287d
```

## Claim boundary

Stage 4 proves finite, deterministic, tamper-evident evidence preservation in
shadow mode. It does not yet prove active intervention, long-term autonomous
memory, morphology-specific advantage, or production persistence.

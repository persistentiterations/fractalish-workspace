# Final Freeze Checklist

Before freezing:

```powershell
git status --short
git log -1 --oneline
python .\tools\verify_all_frozen.py
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_10_release_candidate.py
```

The working tree should contain only the uncommitted Stage 11 files.

Run the one-shot freeze command with the operator's name and an explicit
integer approval epoch supplied in the run instructions.

After freezing:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\verify_frozen_bolt_on_continuity_v0_1.py
git status --short --untracked-files=all
git diff -- .\frozen
```

Review the new frozen snapshot carefully before committing. Existing frozen
release paths must show no modifications; all additions must be under:

```text
frozen/bolt_on_continuity_v0_1
```

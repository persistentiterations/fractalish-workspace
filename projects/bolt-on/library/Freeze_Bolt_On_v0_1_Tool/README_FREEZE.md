# Freeze Bolt-On Demonstrator v0.1

The Stage 5 project is already saved in Git. This package creates the protected
release copy and its verification manifest.

## 1. Extract this helper package

From the canonical repository PowerShell window:

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\Freeze_Bolt_On_v0_1.zip" `
  -DestinationPath ".\release_tools\bolt_on_v0_1" `
  -Force
```

## 2. Run the freeze script

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\release_tools\bolt_on_v0_1\freeze_bolt_on_v0_1.ps1
```

The script will:

- require a clean Git working tree;
- rerun all 76 tests;
- rerun Stage 5 qualification;
- verify the existing 11 frozen files;
- copy v0.1 into `frozen\bolt_on\v0.1`;
- create `RELEASE_RECORD.txt`;
- create a SHA-256 release manifest;
- mark the release files read-only;
- install separate and combined verification tools;
- create `development\bolt_on_demonstrator_v0_2`;
- verify all frozen releases.

The final message should say:

```text
BOLT-ON DEMONSTRATOR v0.1 FREEZE CREATED SUCCESSFULLY
```

## 3. Commit the frozen release

```powershell
git add `
  .\frozen\bolt_on\v0.1 `
  .\tools\verify_bolt_on_v0_1.py `
  .\tools\verify_all_frozen.py `
  .\development\bolt_on_demonstrator_v0_2

git commit -m "Freeze Bolt-On Demonstrator v0.1"
```

## 4. Create the release tag

```powershell
git tag -a bolt-on-demonstrator-v0.1 `
  -m "Qualified shadow-only Bolt-On Demonstrator v0.1"
```

## 5. Verify and inspect

```powershell
python .\tools\verify_all_frozen.py
git status
git tag --list
```

Expected status:

```text
nothing to commit, working tree clean
```

The tag list should include:

```text
bolt-on-demonstrator-v0.1
```

## 6. Push the saved release to GitHub

```powershell
git push origin main
git push origin bolt-on-demonstrator-v0.1
```

After these commands, v0.1 is preserved in three ways:

1. the original Git history;
2. a read-only frozen release with exact hashes;
3. the tagged GitHub release point.

The new `development\bolt_on_demonstrator_v0_2` folder remains writable for the
next stage.

# Bolt-On Demonstrator v0.2 — Release Candidate 1

RC1 is the formal pre-freeze qualification for the completed v0.2 active-control demonstrator. It does not create or modify a frozen release.

It requires the Stage 2–5 qualification scripts, exactly 150 existing v0.2 tests, all frozen-release verifiers, an unchanged development manifest, an unchanged frozen tree, no prohibited executable action vocabulary beyond HOLD and RELEASE, and an exact second pass.

The RC1 harness has 22 separate unit tests outside the qualified product test directory, so it does not change the required 150-test baseline.

Run RC1 unit tests:

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_2_rc1\tests `
  -p "test_*.py" `
  -v
```

Run canonical RC1 qualification from the repository root:

```powershell
python .\development\bolt_on_demonstrator_v0_2_rc1\release_candidate\qualify_v0_2_rc1.py --repo .
```

Expected final lines:

```text
V0.2 RC1 QUALIFICATION: PASS
APPROVED FOR SEPARATE FREEZE PROCEDURE: YES
```

The generated approval record is written to `development/bolt_on_demonstrator_v0_2/RC1_QUALIFICATION.json` and is bound to the current Git commit and source manifests.


## RC1 harness correction 2

The second-pass comparison excludes console-output hashes because unittest output contains elapsed wall-clock time. It compares stable qualification evidence: command identity, required pass marker, exact 150-test count, and unchanged development and frozen manifests. Console hashes remain recorded as diagnostic evidence but are not used as a determinism oracle.

# Common-mode evidence constructed-fixture baseline v0.2

Status: accepted constructed-fixture baseline; not a real-evidence validation.

The trial asks whether apparently independent witnesses actually share one
supplied upstream cause. Two independent valid roots are required to establish a claim.
Repeated copies never become independent merely because relay IDs, sensor IDs,
agent IDs, or paths differ.

Run:

```bash
python3 common_mode_evidence.py
```

Tests:

```bash
python3 -m unittest discover -s tests -v
```

Read `CLAIM_BOUNDARY.md` before citing the result. The experiment evaluates
constructed labels; it does not infer causal roots from real-world evidence.

The preserved acceptance record is in `BASELINE_v0.2.md`. Verify baseline
files with `sha256sum -c SHA256SUMS_v0.2.txt`.

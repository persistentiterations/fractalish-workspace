# Guardian v0.6 — Packaging and Visual Demonstration

Guardian is a manifest-first static intake checkpoint for Python source files.
It scans a file without executing it, applies a validated policy, returns
`LET IN`, `HOLD`, or `REJECT`, and records a policy-bound result slip in a
locked, tamper-evident ledger.

This package preserves the frozen Guardian 0.5 trust engine and adds:

- standard Python package layout;
- `pip` installation;
- `guardian` command-line entry point;
- `python -m guardian_intake` support;
- PyInstaller build specification;
- self-contained browser demonstration;
- evaluation branding and visible limitations.

## Install for development

```bash
python -m pip install .
guardian version
guardian validate-policy docs/guardian_policy.json
```

A scan that writes a receipt requires an HMAC key or explicit local developer
mode:

```bash
guardian --unsigned-dev --ledger demo-ledger.jsonl scan path/to/file.py --explain
```

## Visual demonstration

Open:

```text
demo/guardian_visual_demo.html
```

The HTML demonstration uses built-in sample artifacts. It visualizes the intake
sequence but does not replace the packaged Guardian scanner.

## Security limitation

Guardian may miss harmful, unsafe, or newly developed content. It helps identify
risks based on checks performed at the time of scanning, but results are
informational only and do not guarantee safety. A pass does not mean the content
is completely safe.

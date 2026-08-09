# Guardian Stage 02 — Analyzer Correctness Hardening

Version: 0.4.0

This stage uses one file buffer for hashing, decoding, manifest parsing, AST
analysis, and secret scanning.

Added coverage:
- os/subprocess import aliases and from-import aliases
- `from os import system`
- simple assignment of dangerous callables
- constant-string `getattr`
- constant-string `__import__`
- constant-string `importlib.import_module`
- common os exec/spawn calls
- Path write methods
- selected os and shutil mutations
- broader network modules
- additional common secret formats
- suspicious-obfuscation HOLD indicators

Decision mapping:
- known process execution, network access, or secret: REJECT
- direct file mutation: HOLD
- suspicious obfuscation indicator: HOLD

Limit:
This remains lightweight static analysis. It does not claim complete data-flow,
control-flow, malware, de-obfuscation, dependency, or runtime analysis.

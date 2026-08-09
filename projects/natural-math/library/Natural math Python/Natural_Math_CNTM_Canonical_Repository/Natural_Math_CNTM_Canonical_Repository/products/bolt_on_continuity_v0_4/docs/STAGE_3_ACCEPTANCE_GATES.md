# Bolt-On Continuity v0.4 — Stage 3 Acceptance Gates

- G3.1: The qualified Stage 2 head, qualification record, verifier manifest, and six-file Stage 2 authority set remain unchanged.
- G3.2: The live Stage 2 prerequisite probe must be eligible before any Stage 3 discovery or enrollment command proceeds.
- G3.3: Only the fixed all-container discovery vector and fixed-projection exact-ID inspection vector are executable.
- G3.4: Every subprocess uses a direct argument list, `shell=False`, a five-second timeout, `capture_output=True`, `text=True`, and `check=False`.
- G3.5: Discovery accepts only unique lowercase 64-character hexadecimal IDs and deterministic bounded metadata.
- G3.6: Truncated, uppercase, duplicate, malformed, oversized, ambiguous, and unsupported-state discovery evidence fails closed.
- G3.7: Selection and confirmation must contain the same exact currently discovered full ID.
- G3.8: Inspection must return the same exact ID, consistent name and image metadata, a supported state, and Linux platform evidence.
- G3.9: Discovery and enrollment receipts are canonical, deterministic, timestamp-free, and contain no executable path, stderr, environment mapping, logs, events, or unprojected inspection data.
- G3.10: No persistent state is written and no Docker mutation vector exists.
- G3.11: Only prerequisite probing, local daemon contact, container enumeration, one-container inspection, and in-memory enrollment construction are enabled.
- G3.12: All Stage 0 through Stage 3 tests pass, two Stage 3 verifier runs match, all frozen verifiers pass, `frozen/` remains unchanged, and the working tree is clean.

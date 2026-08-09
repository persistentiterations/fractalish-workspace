# Stage 01 — Strict Manifest

Scope: manifest intake only.

Frozen rules:
- One exact Python comment-block format.
- Exactly one begin/end pair in first 80 lines.
- Required fields: name, version, purpose, dependencies.
- Duplicate, unknown, malformed, empty, uncommented, or ambiguous fields reject.
- Missing manifest holds.
- No guessing or repair during scan.

# Stage 01 — Strict Manifest

Scope: manifest intake only.

Frozen rules:
- One exact Python comment-block format.
- Exactly one begin/end pair in first 80 lines.
- Required fields: name, version, purpose, dependencies.
- Duplicate, unknown, malformed, empty, uncommented, or ambiguous fields reject.
- Missing manifest holds.
- No guessing or repair during scan.

Dependency grammar clarification (v0.3.1):
- `dependencies: none`, `dependencies: stdlib`, and `dependencies: standard library`
  are reserved standalone declarations.
- Reserved declarations may not be mixed with package names.
- Valid package lists use comma-separated package identifiers, for example:
  `dependencies: requests, numpy`.
- Mixed forms such as `dependencies: none, requests` or
  `dependencies: stdlib, pandas` are rejected.
- Blank commented lines remain rejected in the frozen strict Stage 01 format.
- Unknown fields remain rejected; a future extension namespace is deferred.

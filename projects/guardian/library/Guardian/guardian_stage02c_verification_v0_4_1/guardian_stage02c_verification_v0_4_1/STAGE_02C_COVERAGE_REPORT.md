# Guardian Stage 02C — Verification Coverage Report

Engine version tested: 0.4.1  
Stage type: verification freeze; analyzer code was not expanded in this stage.

## Corpus totals

- Original Stage 02B corpus: 36 cases, retained.
- New Stage 02C executable cases: 65
- New adversarial cases: 46
- New benign false-positive controls: 19
- Explicitly untested/out-of-scope hypotheses: 8

## Runtime classification

- Reviewer hypotheses disproven by matching the required outcome: 46
- Confirmed bypasses or false positives: 19
  - Confirmed adversarial misses/under-classifications: 14
  - Confirmed benign false positives: 5
- Idempotence mismatches: 0

## What Guardian 0.4.1 has runtime evidence for

Guardian has corpus evidence for direct and selected indirect forms of:

- manifest validation and dependency declaration grammar;
- direct and aliased `os`, `subprocess`, `eval`, `exec`, and `compile` use;
- selected subscript, container, class attribute, named-expression, function-return,
  and higher-order callable indirection;
- constant and selected computed dynamic imports;
- selected native loaders including `ctypes`, `cffi`, and `zipimport`;
- selected network-capable module imports;
- selected direct filesystem mutation APIs;
- common hardcoded-secret patterns;
- wildcard imports and selected unresolved dynamic behavior as HOLD evidence.

A case appearing in the corpus proves only that exact pattern and its close structural
equivalents were handled under version 0.4.1. It does not prove complete coverage of
the Python language feature involved.

## What Guardian intentionally does not claim

Guardian does not claim:

- complete control-flow, data-flow, points-to, taint, or interprocedural analysis;
- accurate modeling of `global`, `nonlocal`, closures, descriptors, metaclasses,
  monkey-patching, or arbitrary factory return values;
- repository-wide or dependency-source analysis;
- runtime sandboxing or behavioral malware analysis;
- native binary inspection;
- path authorization or traversal proof;
- interpretation of command intent;
- discovery of every encoded or split secret;
- safety certification from a LET IN result.

## Freeze rule

Stage 02C may be called a **verification freeze**, not an analyzer-completeness
freeze. Any confirmed mismatch remains documented and must be either corrected in
a later analyzer stage or explicitly accepted as outside the assurance boundary.

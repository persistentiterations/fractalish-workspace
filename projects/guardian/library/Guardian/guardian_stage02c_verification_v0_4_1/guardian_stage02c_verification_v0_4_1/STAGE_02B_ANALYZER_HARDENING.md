# Guardian Stage 02B — Scope-Aware Analyzer Hardening

Version: 0.4.1

## Why Stage 02 was reopened

External adversarial review identified indirect-call and false-positive cases not covered by the original Stage 02 tests. Stage 02B converted those claims into an executable bypass corpus before modifying the analyzer.

## Confirmed v0.4.0 gaps addressed

- `sys.modules["os"].system(...)`
- `__builtins__.eval(...)` and `__builtins__["exec"](...)`
- `globals()["eval"]` and `locals()["exec"]`
- tuple/list assignment of dangerous callables
- constant-index list/dict callable indirection
- class-level dangerous callable attributes
- `functools.partial`, `operator.attrgetter`, and `operator.methodcaller`
- `ctypes`, `cffi`, and `zipimport` loader surfaces
- wildcard imports now produce HOLD
- unresolved dynamic `getattr` on dangerous modules produces REJECT plus uncertainty evidence
- false positives for unrelated user methods named `touch` or `replace`

## Architecture change

The global assignment map was replaced by a scope-aware `ast.NodeVisitor`. It tracks lexical scopes, imports, aliases, tuple/list bindings, simple containers, class attributes, named expressions, simple function returns, and selected callable factories. Findings retain source line numbers internally.

## Decision rules

- Proven process execution, dynamic loading, network access, or secrets: REJECT
- Proven direct file mutation: HOLD
- Wildcard imports and unresolved suspicious indirection: HOLD
- Unresolved dynamic selection on a known dangerous module: REJECT

## Evidence

- All inherited Stage 01 and Stage 02 tests must pass.
- A 36-case bypass corpus must produce the specified outcomes.
- Original four sample outcomes must remain unchanged.
- Ledger replay must pass.

## Limits

This is still lightweight static analysis. It does not prove code is safe and does not implement complete interprocedural, control-flow, points-to, taint, dependency, malware, or runtime analysis.

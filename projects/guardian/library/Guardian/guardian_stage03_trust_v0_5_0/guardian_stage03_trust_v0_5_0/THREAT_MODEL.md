# Guardian Threat Model

Version: Guardian 0.5.0  
Slip schema: guardian-result-slip 1.0  
Policy schema: 1.0

## Design goal

Guardian provides a reproducible, policy-bound intake record for static analysis
of one UTF-8 Python source file. Guardian reads the submitted file as data and
does not execute it.

## Assets

Guardian is intended to protect the integrity of:

- the policy used to make an intake decision;
- the file fingerprint tied to that decision;
- the result slip;
- the order and integrity of the local ledger;
- the HMAC key, when signing is enabled.

## Trust boundaries

The principal trust boundaries are:

1. the Guardian executable and Python runtime;
2. the validated policy;
3. the ledger and its lock file;
4. the HMAC key;
5. the submitted source file;
6. the caller that enforces LET IN, HOLD, or REJECT.

## Attacker capabilities considered

Guardian considers malformed files, ambiguous manifests, selected static
indirection and obfuscation, unauthorized policy edits, accidental or deliberate
ledger-line edits, reordering, insertion, malformed tails, and concurrent local
append attempts.

## Security goals

- Reject malformed or unsupported policies before scanning.
- Tie each result slip to the exact canonical policy content.
- Tie each result slip to the exact file bytes inspected.
- Produce one linear ledger chain under concurrent local appends.
- Detect protected-field modification and chain-link modification.
- Verify HMAC signatures when the key is available.
- Require explicit acknowledgement for unsigned append mode.

## Supported evidence

The analyzer evidence boundary is the frozen Stage 02C coverage report. It
includes strict manifest validation and a documented collection of direct and
selected indirect AST patterns for network access, process execution, file
mutation, dynamic loading, obvious hardcoded secrets, and suspicious
obfuscation.

## Intentional non-detections

Guardian does not claim:

- complete control-flow, data-flow, points-to, taint, or interprocedural analysis;
- repository-wide or dependency-source inspection;
- runtime sandboxing, behavioral malware detection, or execution prevention;
- native binary inspection;
- complete modeling of descriptors, metaclasses, monkey-patching, `global`,
  `nonlocal`, closures, or arbitrary computed values;
- proof of path authorization or command safety;
- discovery of every secret or encoded payload;
- protection against an attacker who controls Guardian, its runtime, its HMAC
  key, and its storage.

## Meaning of outcomes

- LET IN: no configured check failed. This is not a safety certification.
- HOLD: configured evidence requires review before admission.
- REJECT: at least one configured reject-level check failed.
- SCAN/POLICY/LEDGER ERROR: the decision process could not complete reliably.

## Ledger properties

The ledger is tamper-evident, not immutable. Hash chaining detects protected
content changes and chain discontinuities. HMAC authentication makes
recomputation harder only while the signing key remains secret. Deleting the
entire ledger cannot be detected without an external anchor or independent
backup.

## Required defense in depth

A production deployment should separately provide quarantine, access control,
dependency scanning, sandboxed or isolated execution, runtime monitoring,
backups, protected key storage, and an enforcement point that respects
Guardian's decision.

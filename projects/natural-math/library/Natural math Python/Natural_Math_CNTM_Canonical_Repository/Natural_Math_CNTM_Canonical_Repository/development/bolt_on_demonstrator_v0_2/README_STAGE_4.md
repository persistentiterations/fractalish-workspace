# Bolt-On Demonstrator v0.2 — Stage 4

## Bounded multi-action lifecycle qualification

Stage 4 composes the previously qualified HOLD and RELEASE mechanisms across
four isolated lifecycle sessions. It introduces no additional host action and
does not modify the ordinary host, Stage 1 authority, Stage 2 mediation,
Stage 3 release, or any frozen file.

The campaign qualifies:

1. repeated HOLD and RELEASE cycles;
2. rejection of expired RELEASE authority followed by fresh reauthorization;
3. interruption checkpoint creation, validation, recovery, and tamper rejection;
4. ordinary-host detach while a HOLD remains active;
5. later RELEASE after detach without loss or mutation of the held job;
6. cross-cycle HOLD and RELEASE permit rejection;
7. cycle-bound consumption keys derived from permit hashes;
8. exact eight-action campaign budget: four HOLD plus four RELEASE;
9. per-cycle and campaign deterministic receipt replay.

`RELEASE` still restores a job to the ordinary host. It does not force execution
or bypass dependency validation. The baseline held job `J005` therefore remains
delayed by the unchanged host because dependency `J999` is absent.

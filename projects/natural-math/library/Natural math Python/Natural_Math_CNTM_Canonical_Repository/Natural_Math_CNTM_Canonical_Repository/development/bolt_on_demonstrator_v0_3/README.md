# Bolt-On Demonstrator v0.3 — Development

## External Host Portability and Adapter Substitution

This development tree begins after the frozen Bolt-On Demonstrator v0.2 release.

Do not edit:

- `frozen/bolt_on/v0.1`
- `frozen/bolt_on/v0.2`

v0.3 must prove that the same bounded governance, mediation, release, receipt,
and replay semantics can attach to materially different host systems through
replaceable adapters. Hosts must not be rebuilt around the bolt-on, and the
bolt-on must not acquire hidden execution authority.

Planned sequence:

1. portable adapter contract;
2. second independent host;
3. equivalent-event cross-host replay;
4. live host substitution;
5. adversarial adapter testing;
6. portability qualification and RC.

Each stage requires deterministic tests and an explicit advancement decision.
Qualification and freeze remain separate commits.

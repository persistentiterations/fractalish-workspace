# Bolt-On Demonstrator v0.4 — Development

## External-System Integration Pilot

This development tree begins after the frozen Bolt-On Demonstrator v0.3 release.

Do not edit:

- `frozen/bolt_on/v0.1`
- `frozen/bolt_on/v0.2`
- `frozen/bolt_on/v0.3`

v0.4 must move the portability architecture from purpose-built qualification
hosts toward an independently existing host interface. The bolt-on must be
installable and removable as a sidecar, ordinary host behavior must remain
unchanged when the bolt-on is absent, and no adapter may receive execution
authority.

Planned sequence:

1. external host integration contract;
2. independent ordinary host fixture and native baseline;
3. read-only external observation adapter;
4. host-owned bounded command gateway;
5. live sidecar installation, removal, and failure recovery;
6. external pilot qualification and release candidate.

Each stage requires deterministic tests and an explicit advancement decision.
Qualification and freeze remain separate commits.

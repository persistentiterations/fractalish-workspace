# Product Contract — v0.3 Stage 0

Bolt-On Continuity for Docker v0.3 is a local, observation-first continuity and incident product foundation.

Stage 0 qualifies packaging, contracts, deterministic record primitives, configuration defaults, storage boundaries, a narrow Docker adapter interface, and a disabled-by-default first-party module registry.

Permitted user-visible behavior:

- install the Python package;
- import `bolt_on`;
- run `bolt version`;
- inspect command help.

Stage 0 does not start an observer, enroll a container, create operational databases, contact Docker, write telemetry, or mutate Docker.

Future commands and modules require later stage contracts and qualification. Their names do not grant authority.

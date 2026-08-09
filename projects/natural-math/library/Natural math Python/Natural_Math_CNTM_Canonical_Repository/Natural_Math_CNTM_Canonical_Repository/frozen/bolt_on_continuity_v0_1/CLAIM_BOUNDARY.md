# Claim Boundary — Product Prototype v0.1

## Stage 0 claim

A passing Stage 0 verifies only that a separate product contract has been defined
for one local Linux Docker container, with bounded observation, deterministic
receipts, `HOLD`/`RELEASE` projection, host-owned execution, fail-closed behavior,
and explicit qualification gates.

Stage 0 does not prove that the product works against Docker.

## Future bounded claim after all required qualification

After implementation and successful qualification, evidence may support wording
similar to:

> Bolt-On Continuity for Docker v0.1 observed one configured Linux Docker
> container in the qualified local environments, produced deterministic incident
> receipts, projected bounded hold or release requests, and preserved host-owned
> execution through a separate validating gateway.

The final wording must identify the tested contract and environments.

## Prohibited or unsupported claims

Do not claim:

- zero drift;
- perfect continuity;
- prevention of all failures;
- autonomous recovery;
- universal Docker compatibility;
- universal host compatibility;
- production security;
- enterprise readiness;
- arbitrary third-party integration;
- cloud-provider compatibility;
- Kubernetes compatibility;
- distributed operation;
- no data loss;
- infallible incident reconstruction;
- root-cause identification;
- performance at production scale;
- customer demand;
- commercially proven value.

## Zero-drift rule

The phrase `zero drift` may be used only if:

1. drift is formally defined;
2. the bounded state and observation contract is stated;
3. a measurement method is frozen;
4. test populations and duration are reported;
5. exceptions and unobserved surfaces are disclosed;
6. independent replay results are included.

Absent those conditions, use `drift detection under the qualified contract`.

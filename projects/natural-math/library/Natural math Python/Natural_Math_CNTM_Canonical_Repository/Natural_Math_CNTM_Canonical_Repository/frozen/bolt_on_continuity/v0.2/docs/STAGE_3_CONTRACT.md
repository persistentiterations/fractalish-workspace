# Stage 3 Contract — Discovery and Enrollment

## Objective

Provide a bounded, deterministic way for an operator to discover eligible local containers and enroll exactly one immutable Docker subject without granting mutation authority.

## Discovery contract

Discovery may execute only:

```text
docker container ls --all --no-trunc --format {{json .}}
```

The command is a fixed argument vector and never uses a shell. Each non-empty output line must be one JSON object. Discovery rejects malformed JSON, missing fields, truncated IDs, duplicate IDs, non-Linux evidence when present, and ambiguous records.

Normalized discovery entries contain only:

- `container_id` — lowercase 64-character hexadecimal ID;
- `names` — bounded display string;
- `image` — bounded display string;
- `state` — normalized lowercase display state;
- `status` — bounded display string.

Entries are sorted by `container_id`. Names and images are not authority.

## Selection contract

The operator selects one entry by its exact full container ID. Prefixes, names, indexes, wildcards, whitespace-altered IDs, uppercase IDs, and unknown IDs are rejected.

## Confirmation contract

Enrollment requires the operator to provide the same exact full ID a second time. There is no yes/no shortcut and no implicit confirmation.

## Inspection contract

After exact selection and confirmation, Stage 3 may execute only:

```text
docker inspect <full 64-character container ID>
```

Inspection must return one object whose `Id` exactly equals the selected ID. The record must identify a Linux container when platform evidence is available. Name differences are recorded but do not change subject identity.

## Enrollment record

A successful enrollment produces canonical JSON containing:

- schema and contract identifiers;
- exact container ID;
- display name;
- image reference;
- observed lifecycle state;
- `observation_only: true`;
- `gateway_enabled: false`;
- a canonical SHA-256 enrollment digest.

The digest excludes itself and is computed over UTF-8 canonical JSON using sorted keys and compact separators.

The record is returned as data only. Stage 3 does not write it to a product configuration location.

## Replacement rule

A later container with the same name but a different ID is a different subject. It cannot inherit enrollment.

## Failure behavior

All uncertainty fails closed. Stable failures include discovery unavailable, malformed discovery, duplicate subject, invalid selection, confirmation mismatch, inspection unavailable, inspection mismatch, unsupported platform, and malformed inspection.

## Non-authority

Stage 3 contains no pause, unpause, stop, restart, kill, remove, exec, run, create, network, volume, image, gateway, decision, projection, or incident authority.

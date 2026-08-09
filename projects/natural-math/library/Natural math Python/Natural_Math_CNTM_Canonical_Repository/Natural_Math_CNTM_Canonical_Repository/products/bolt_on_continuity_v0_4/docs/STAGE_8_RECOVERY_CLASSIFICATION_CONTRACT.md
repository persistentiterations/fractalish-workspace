# Bolt-On Continuity v0.4 — Stage 8 Recovery Classification Contract

Stage 8 consumes bounded operator-supplied evidence and produces one deterministic recovery classification. It does not perform recovery.

Subject classifications are `SUBJECT_MATCHED`, `SUBJECT_MISSING`, `SUBJECT_REPLACED`, `SUBJECT_STOPPED`, and `SUBJECT_AMBIGUOUS`. Container names are descriptive only; a same-name container with a different full ID requires reenrollment.

Store classifications are `STORE_HEALTHY`, `STORE_MISSING`, `STORE_PERMISSION_DENIED`, `STORE_PARTIAL_WRITE`, `STORE_CORRUPT`, `STORE_DISK_FULL`, and `STORE_AMBIGUOUS`. Only `STORE_HEALTHY` permits normal recovery classification.

Dispositions are `RESUME_OBSERVATION_ONLY`, `SUPPRESS_DUPLICATE`, `REQUIRE_REENROLLMENT`, `REPORT_SUBJECT_UNAVAILABLE`, `FAIL_CLOSED_STORE`, and `FAIL_CLOSED_UNCERTAIN`.

Terminal prior requests are suppressed. Projected, approved, conflicting, malformed, or otherwise unresolved action evidence fails closed.

Every result states `observation_only: true`, `gateway_enabled: false`, and `native_execution_authorized: false`. Stage 8 performs no Docker call, filesystem access, gateway action, command construction, subprocess execution, networking, process control, automatic recovery, publication, or production claim.

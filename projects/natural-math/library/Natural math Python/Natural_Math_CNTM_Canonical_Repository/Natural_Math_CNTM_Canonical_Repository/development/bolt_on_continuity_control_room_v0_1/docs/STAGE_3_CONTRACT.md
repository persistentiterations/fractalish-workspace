# Stage 3 — Running-to-Stopped Observation Contract

Stage 3 observes exactly one operator-selected container before and after an
operator-confirmed manual stop. It uses the existing read-only adapter and the
existing retained-entry fields. The transition evidence schema is
`bolt-on-continuity-control-room-state-transition/v1`; it holds one earlier and
one later Stage 1 canonical observation, each paired with its verified retained
entry. External observation times are retained but excluded from all digests.

`SAME_SUBJECT_STOPPED` requires a confirmed manual stop, contiguous indices 1
and 2, valid Stage 1 receipts, matching full container IDs, earlier
`state=running`/`running=true`, and later `state=exited`/`running=false`.
Everything else is `INDETERMINATE` with a bounded reason. Different IDs do not
mean replacement; states do not explain cause, severity, recovery, or intent.

The deterministic transition receipt schema is
`bolt-on-continuity-control-room-state-transition-receipt/v1`. Its SHA-256
input contains only schema values, subject selector, each retained index/full ID/
receipt ID/observed state/running flag, classification, and reason.

The operator must explicitly confirm the manual `docker stop bolt-on-demo`
outside Bolt-On before the later capture. No Stage 3 code, test, verifier, or
helper may execute a mutation-capable Docker command. Presentation labels
observed facts, retained evidence, derived comparison, classification, and
operator-entered confirmation separately.

Qualification requires the exact Stage 2 commit
`b75d2dbe5de814232e3b0f1731405941af5cc4e8`, fixture tests, a Docker-required
live running-to-stopped path, all Control Room tests, frozen verification, an
unchanged `frozen/` tree, intended-only changes, and a clean committed tree.

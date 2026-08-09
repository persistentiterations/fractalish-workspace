# Guardian Stage 03 Freeze Record

Version: **0.5.0**

Status: **PASS**

## Verified results

- Frozen Stage 02C manifest/analyzer block unchanged: **True**
- Automated tests: **81 passed**
- Policy validation: **passed**
- Original sample outcomes: **passed**
- Signed ledger replay: **passed**
- Concurrent append test: **passed**
- Wrong-HMAC-key detection: **passed**
- Receipt fingerprint recomputation: **passed**
- Stage 02C classification boundary preserved: **passed**

## Frozen formats

- Engine version: `0.5.0`
- Result-slip schema: `guardian-result-slip` version `1.0`
- Policy schema: `1.0`
- Frozen analyzer block SHA-256: `f47b9a570b75fea839207182b989f02e99212c5d99c09575537bf491f248d4ab`

## Product boundary

Guardian is a static, manifest-first intake checkpoint with a policy-bound,
tamper-evident decision record. It is not a sandbox, runtime enforcement point,
malware guarantee, or safety certification.

The 19 confirmed Stage 02C analyzer mismatches remain documented. Stage 03 did
not alter, hide, or reclassify them.

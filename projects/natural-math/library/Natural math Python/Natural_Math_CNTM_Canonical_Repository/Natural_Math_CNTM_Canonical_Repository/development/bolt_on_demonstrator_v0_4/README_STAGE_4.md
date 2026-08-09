# Bolt-On Demonstrator v0.4 — Stage 4

## Host-Owned Bounded Command Gateway

Stage 4 performs the first bounded command crossing into the independently
implemented ordinary job service.

The projection adapter may translate only:

```text
HOLD    -> PAUSE_JOB
RELEASE -> RESUME_JOB
```

The adapter does not receive the native host authority token, a command
transport, a host object, a gateway callable, or an execution method. It emits a
deterministic envelope with `executed=False`.

A separate host-owned gateway independently validates the envelope, checks an
exact host-owner permit, binds the request to the current native subject, state,
version, observation, and native receipt, constructs the native command, and
submits that command using authority retained inside the host boundary.

## Qualified live sequence

```text
Native REGISTER_JOB
Native START_JOB
Native CHECKPOINT_JOB
Observed HOLD request
Host-owned PAUSE_JOB
Observed RELEASE request
Host-owned RESUME_JOB
Native COMPLETE_JOB
```

The resulting six-command host journal is byte-for-byte equal to a direct-native
control run using the same native commands. The two projected envelopes remain
non-executing evidence; the gateway records the only two host-owned command
crossings.

## Files

```text
README_STAGE_4.md
adapters/bounded_action_projector.py
gateways/host_owned_command_gateway.py
integration/host_owned_bounded_command_gateway.py
tests/test_host_owned_bounded_command_gateway.py
```

The archive adds only these five Stage 4 files. It does not alter Stages 1–3 or
any frozen release.

## Security and authority boundaries

- frozen v0.3 remains the source of the portable `HOLD` and `RELEASE` request
  contract;
- the Stage 3 observer remains read-only;
- the projector imports no host or gateway module;
- the projector has no command transport and no execution method;
- the gateway imports no observer or projector module;
- the gateway accepts plain envelope mappings rather than an adapter callback;
- a host-owner permit binds one action, subject, state, version, observation,
  receipt, governance session, authority digest, and projector identity;
- only the gateway constructs a native command;
- only the native host applies `PAUSE_JOB` and `RESUME_JOB`;
- duplicate and conflicting idempotency reuse fail closed;
- bolt-on executed actions remain zero.

## Adversarial qualification

The Stage 4 matrix contains 54 deterministic rejection cases covering:

- non-mapping, missing-field, extra-field, and malformed envelopes;
- invalid envelope, request, observation, receipt, authority, and projector
  bindings;
- unsupported actions and operation-map substitution;
- stale and future native versions;
- wrong subjects and native states;
- `would_dispatch=False` and fraudulent `executed=True` claims;
- invalid, forged, or mismatched host-owner permits;
- stale native receipt binding;
- duplicate gateway requests and idempotency conflicts.

Every adversarial case preserves the exact native host run and command count.

## Install

From the canonical repository PowerShell window:

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\Bolt_On_Demonstrator_v0_4_Stage_4.zip" `
  -DestinationPath "." `
  -Force
```

## Run component self-checks

```powershell
python .\development\bolt_on_demonstrator_v0_4\adapters\bounded_action_projector.py
python .\development\bolt_on_demonstrator_v0_4\gateways\host_owned_command_gateway.py
```

Required endings:

```text
BOUNDED ACTION PROJECTOR SELF-CHECK: PASS
HOST-OWNED COMMAND GATEWAY SELF-CHECK: PASS
```

## Run Stage 4

```powershell
python .\development\bolt_on_demonstrator_v0_4\integration\host_owned_bounded_command_gateway.py
```

Expected fixed output:

```text
Stage: HOST-OWNED BOUNDED COMMAND GATEWAY 0.4.4
Mode: LIVE_HOST_OWNED_COMMAND_CROSSING
Bolt-on execution authority: NONE
Gateway execution owner: HOST
Host execution boundary: NATIVE_HOST_ONLY
Stage 3 commit: d4c7dd0f84b4aeed32dcd6fabc15e82ae4f37c10
Frozen v0.3 manifest: 57f7026ff9dcc69d6dcacb51fda89a40700828e110e74145a0edfaf266c5f6fa
Frozen v0.3 entries: 20
Host: ORDINARY VERSIONED JOB SERVICE 1.0
Host source: 14a3b86d4cabee409d84904f3db4feb416be905c3c54edb3ca5ef4d50e41a797
Observer source: 176232fe8f4a9266fc90259ea82f19e36b36863fb14f328786c8ddb7ebcf6f68
Projector source: 9031999d62820a971e7e201c3393a710716c20f9973c8c33a2a0b3e8b455f57d
Gateway source: ab41240248100acff9b4e599ac2109f609d75528c954c101a2fd9bc241667fea
Portable actions: HOLD, RELEASE
Native operations: PAUSE_JOB, RESUME_JOB
Projected requests: 2
Gateway permits: 2
Gateway accepted: 2
Gateway rejected: 0
Gateway host actions: 2
Surrounding native host actions: 4
Total native host actions: 6
Bolt-on executed actions: 0
Direct-native equivalence: True
Deterministic second pass: True
Native replay: True
Observation replay: True
Gateway decision replay: True
Duplicate request rejection: True
Idempotency conflict rejection: True
Adversarial cases: 54
Adversarial cases safely rejected: 54
Final state: DONE
Final version: 6
Native run digest: b0037e3d7b4e9949b0366d80b38d28de2b81e2c41c1aa557e31565c8ab5ea2f9
Native replay digest: b0037e3d7b4e9949b0366d80b38d28de2b81e2c41c1aa557e31565c8ab5ea2f9
Direct run digest: b0037e3d7b4e9949b0366d80b38d28de2b81e2c41c1aa557e31565c8ab5ea2f9
Final observation digest: 89f8fe05a01198e1dcb7c37c41dccc8bede576f5f73caa56a40d321edc9518e1
Gateway decision digest: 42bd208be4137e14ebca684e69d9e4b150725d72bc89a6a96c192b2f5d38a909
Adversarial digest: 6a9227ae9338c19202aaddf1845cc19320290af69d9dda5d14695b2ed92ab3c1
Qualification receipt digest: 60e1efa13f8e69d5f5e26f60de43adfa9e5651c6e5b8975088ef5768e10cf9ea
Qualification replay digest: 60e1efa13f8e69d5f5e26f60de43adfa9e5651c6e5b8975088ef5768e10cf9ea
STAGE 4 HOST-OWNED BOUNDED COMMAND GATEWAY: PASS
```

## Run the complete v0.4 suite

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_4\tests `
  -p "test_*.py" `
  -v
```

Stage 4 contributes 115 tests. With the existing 230 Stage 1–3 tests, the
complete suite must end with:

```text
Ran 345 tests

OK
```

## Verify frozen releases

```powershell
python .\tools\verify_all_frozen.py
```

Required final line:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

## Claim boundary

A passing Stage 4 proves that frozen portable `HOLD` and `RELEASE` requests can
be projected through a non-executing adapter and accepted by a separately
implemented host-owned gateway, while the native host retains all execution
authority and produces a journal exactly equivalent to direct native operation.

It does not yet prove production authentication, network transport, distributed
coordination, crash recovery during a command crossing, or integration with an
unmodified third-party production service. Live install/remove and failure
recovery remain Stage 5.

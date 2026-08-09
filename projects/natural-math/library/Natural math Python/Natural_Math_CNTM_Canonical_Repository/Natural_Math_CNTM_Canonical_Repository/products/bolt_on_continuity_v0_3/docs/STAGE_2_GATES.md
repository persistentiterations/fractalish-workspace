# Stage 2 Gates

- G2.1: only the two declared Docker probe vectors are executable.
- G2.2: shell execution is always disabled.
- G2.3: each probe has a bounded timeout.
- G2.4: malformed, failed, missing, remote, or ambiguous evidence fails closed.
- G2.5: canonical reports exclude executable paths, usernames, environment values, socket addresses, and timestamps.
- G2.6: Linux engine mode is required.
- G2.7: observation-only remains true and gateway-enabled remains false.
- G2.8: fake probe runners produce deterministic qualification evidence.

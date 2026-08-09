# Stage 9 Contract

Stage 9 qualifies failure behavior without expanding product authority.

## Adversarial requirements

The product must reject:

- short, named, nonhexadecimal, or mismatched container identifiers;
- operations outside inspect, pause, and unpause;
- extra command arguments;
- shell-mediated commands;
- malformed Docker inspect responses;
- HOLD against a stopped or already-paused container;
- RELEASE against a stopped or unpaused container;
- negative or noninteger sequence and time values;
- failed native operations;
- unverifiable postconditions;
- altered or cross-subject pipeline records;
- broken receipt links;
- nonadvancing stage sequences.

## Bounded recovery requirements

A recovery trial must:

1. begin running and unpaused;
2. complete and verify HOLD;
3. inject one failure before the first RELEASE reaches Docker;
4. verify that the container remains running and paused;
5. permit exactly one recovery RELEASE;
6. verify running and unpaused;
7. emit a deterministic recovery qualification receipt.

The harness never removes the target container.

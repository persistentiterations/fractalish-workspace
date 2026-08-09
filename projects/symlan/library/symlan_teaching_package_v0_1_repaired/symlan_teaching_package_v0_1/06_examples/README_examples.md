# Teaching examples

| File | Profile | Intent |
|------|---------|--------|
| `board_hal_section7.symlan` | projected_3space | Minimal board program (HAL §7) |
| `attractor_hal_section7.symlan` | attractor_graph | Minimal graph program (HAL §7) |

## Run

From `04_runtime/`:

```bash
# Board
python -c "
from materializer_v0_1 import materialize, PROFILE_PROJECTED, canonical_json
src = open('../06_examples/board_hal_section7.symlan').read()
print(canonical_json(materialize(src, profile=PROFILE_PROJECTED))[:500], '...')
"

# Attractor
python materializer_v0_1.py --attractor
```

## Exercise for learners

1. Change only the seed string; re-materialize; compare node placement / T_obs.
2. Change only κ on one coupling; observe whether gate band shifts.
3. Remove one arm of `branch on T`; confirm the materializer rejects incomplete ternary.
4. Add a second structural node and coupling; materialize attractor profile; list new vertices and edges.

# Natural Math v5 Scale Gate 5 Two-Parameter Interaction Mapping

Spec SHA256: `E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B`
Seeds: `0-49`
Steps per run: `140`
Total runs: `5400`

## Pair Summary

- `rest_gain_x_decay_cost`: `7` stable cells, `6` transition cells, `7` collapse cells across `20` grid cells.
- `rest_gain_x_damage_energy_loss`: `3` stable cells, `10` transition cells, `3` collapse cells across `16` grid cells.
- `move_cost_x_world_size`: `1` stable cells, `9` transition cells, `6` collapse cells across `16` grid cells.
- `max_bonds_x_damage_energy_loss`: `2` stable cells, `12` transition cells, `2` collapse cells across `16` grid cells.
- `max_bonds_x_world_size`: `2` stable cells, `11` transition cells, `3` collapse cells across `16` grid cells.
- `resource_absorb_rate_x_world_size`: `3` stable cells, `7` transition cells, `2` collapse cells across `12` grid cells.
- `repair_cost_x_max_bonds`: `6` stable cells, `6` transition cells, `0` collapse cells across `12` grid cells.

## Interaction Matrices

### rest_gain_x_decay_cost

Rows: `rest_gain`. Columns: `decay_cost`. Cells show pass rate and band.

| value | `160` | `220` | `280` | `340` |
|---|---|---|---|---|
| `140` | `50/50` stable | `6/50` transition | `0/50` collapse | `0/50` collapse |
| `170` | `50/50` stable | `28/50` transition | `0/50` collapse | `0/50` collapse |
| `200` | `50/50` stable | `47/50` transition | `1/50` transition | `0/50` collapse |
| `220` | `50/50` stable | `50/50` stable | `15/50` transition | `0/50` collapse |
| `260` | `50/50` stable | `50/50` stable | `36/50` transition | `0/50` collapse |

### rest_gain_x_damage_energy_loss

Rows: `rest_gain`. Columns: `damage_energy_loss`. Cells show pass rate and band.

| value | `14000` | `17000` | `21000` | `25000` |
|---|---|---|---|---|
| `170` | `28/50` transition | `9/50` transition | `0/50` collapse | `0/50` collapse |
| `200` | `47/50` transition | `32/50` transition | `11/50` transition | `0/50` collapse |
| `220` | `50/50` stable | `47/50` transition | `26/50` transition | `2/50` transition |
| `260` | `50/50` stable | `50/50` stable | `47/50` transition | `28/50` transition |

### move_cost_x_world_size

Rows: `move_cost`. Columns: `world_size`. Cells show pass rate and band.

| value | `25` | `35` | `45` | `60` |
|---|---|---|---|---|
| `300` | `50/50` stable | `24/50` transition | `12/50` transition | `0/50` collapse |
| `450` | `43/50` transition | `11/50` transition | `6/50` transition | `0/50` collapse |
| `600` | `30/50` transition | `8/50` transition | `0/50` collapse | `0/50` collapse |
| `750` | `25/50` transition | `1/50` transition | `0/50` collapse | `0/50` collapse |

### max_bonds_x_damage_energy_loss

Rows: `max_bonds`. Columns: `damage_energy_loss`. Cells show pass rate and band.

| value | `14000` | `17000` | `21000` | `25000` |
|---|---|---|---|---|
| `2` | `7/50` transition | `5/50` transition | `0/50` collapse | `0/50` collapse |
| `3` | `41/50` transition | `35/50` transition | `21/50` transition | `1/50` transition |
| `4` | `50/50` stable | `47/50` transition | `26/50` transition | `2/50` transition |
| `5` | `50/50` stable | `45/50` transition | `28/50` transition | `4/50` transition |

### max_bonds_x_world_size

Rows: `max_bonds`. Columns: `world_size`. Cells show pass rate and band.

| value | `25` | `35` | `45` | `60` |
|---|---|---|---|---|
| `2` | `7/50` transition | `1/50` transition | `1/50` transition | `0/50` collapse |
| `3` | `41/50` transition | `13/50` transition | `8/50` transition | `0/50` collapse |
| `4` | `50/50` stable | `24/50` transition | `12/50` transition | `0/50` collapse |
| `5` | `50/50` stable | `32/50` transition | `21/50` transition | `1/50` transition |

### resource_absorb_rate_x_world_size

Rows: `resource_absorb_rate`. Columns: `world_size`. Cells show pass rate and band.

| value | `25` | `35` | `45` | `60` |
|---|---|---|---|---|
| `7000` | `50/50` stable | `31/50` transition | `17/50` transition | `1/50` transition |
| `14000` | `50/50` stable | `24/50` transition | `12/50` transition | `0/50` collapse |
| `21000` | `50/50` stable | `20/50` transition | `13/50` transition | `0/50` collapse |

### repair_cost_x_max_bonds

Rows: `repair_cost`. Columns: `max_bonds`. Cells show pass rate and band.

| value | `2` | `3` | `4` | `5` |
|---|---|---|---|---|
| `175` | `7/50` transition | `42/50` transition | `50/50` stable | `50/50` stable |
| `350` | `7/50` transition | `41/50` transition | `50/50` stable | `50/50` stable |
| `700` | `5/50` transition | `39/50` transition | `50/50` stable | `50/50` stable |

## Artifact Hashes

- Run CSV SHA256: `A88684FA3C9FD2DEBF19DB73B6EC09B424E88C80A068633B3C995180EC6F6C20`
- Cell CSV SHA256: `D327154EEF30514D8AAFB83832EFC63E11780C29C3386C36B206F0B4133FFA6A`
- Summary JSON SHA256: `BA195D6A29F76105435A5FED059EFC4CF046109B4CDFAF18D37D25DF748B49D8`

## Claim Boundary

This maps the listed two-parameter grids only. It tests interaction zones around known thresholds, not the full parameter space.

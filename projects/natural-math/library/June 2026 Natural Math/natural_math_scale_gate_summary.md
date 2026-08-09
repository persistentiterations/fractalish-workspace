# Natural Math v5 Scale Gate Summary

Spec SHA256: `E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B`

## Scale Gate 1: Default Seed Sweep

- `default`: 50/50 pass, avg alive 30, avg energy 44542

## Scale Gate 2: Steps Sweep

- steps `0`: 0/50 pass, avg alive 30, avg energy 55034, resource reached 0/50
  - failures: `{'resource_reached=False': 50, 'success_distance_passed=False': 50}`
- steps `1`: 0/50 pass, avg alive 30, avg energy 54514, resource reached 0/50
  - failures: `{'resource_reached=False': 50, 'success_distance_passed=False': 50}`
- steps `35`: 42/50 pass, avg alive 30, avg energy 44963, resource reached 50/50
  - failures: `{'component_count!=1': 7, 'success_distance_passed=False': 1}`
- steps `70`: 50/50 pass, avg alive 30, avg energy 44542, resource reached 50/50
- steps `140`: 50/50 pass, avg alive 30, avg energy 44542, resource reached 50/50
- steps `210`: 50/50 pass, avg alive 30, avg energy 44542, resource reached 50/50
- steps `300`: 50/50 pass, avg alive 30, avg energy 44542, resource reached 50/50

## Scale Gate 3: Parameter Sensitivity

- `max_bonds=2`: 7/50 pass, avg alive 26, avg energy 31317, resource reached 50/50
  - failures: `{'average_energy<38000': 22, 'success_distance_passed=False': 35, 'alive_count<24': 13}`
- `max_bonds=6`: 50/50 pass, avg alive 30, avg energy 45274, resource reached 50/50
- `move_cost=150`: 50/50 pass, avg alive 30, avg energy 47277, resource reached 50/50
- `move_cost=600`: 30/50 pass, avg alive 30, avg energy 39508, resource reached 50/50
  - failures: `{'average_energy<38000': 20, 'success_distance_passed=False': 6}`
- `rest_gain=110`: 0/50 pass, avg alive 30, avg energy 31927, resource reached 50/50
  - failures: `{'average_energy<38000': 50}`
- `rest_gain=440`: 50/50 pass, avg alive 30, avg energy 69528, resource reached 50/50
- `world_size=15`: 49/50 pass, avg alive 29, avg energy 48999, resource reached 50/50
  - failures: `{'average_energy<38000': 1}`
- `world_size=35`: 24/50 pass, avg alive 29, avg energy 39688, resource reached 50/50
  - failures: `{'success_distance_passed=False': 19, 'alive_count<24': 1, 'average_energy<38000': 8}`
- `decay_cost=110`: 50/50 pass, avg alive 30, avg energy 60154, resource reached 50/50
- `decay_cost=440`: 0/50 pass, avg alive 27, avg energy 14562, resource reached 50/50
  - failures: `{'average_energy<38000': 50, 'success_distance_passed=False': 8, 'alive_count<24': 7}`
- `repair_cost=175`: 50/50 pass, avg alive 30, avg energy 44629, resource reached 50/50
- `repair_cost=700`: 50/50 pass, avg alive 30, avg energy 44377, resource reached 50/50
- `damage_energy_loss=7000`: 50/50 pass, avg alive 30, avg energy 51824, resource reached 50/50
- `damage_energy_loss=21000`: 26/50 pass, avg alive 30, avg energy 37895, resource reached 50/50
  - failures: `{'average_energy<38000': 24, 'success_distance_passed=False': 1}`
- `resource_absorb_rate=7000`: 50/50 pass, avg alive 30, avg energy 45307, resource reached 50/50
- `resource_absorb_rate=21000`: 50/50 pass, avg alive 30, avg energy 44208, resource reached 50/50

## Artifact Hashes

- Seed sweep CSV SHA256: `9EF72C6BAA963D804EBB483D2CBD7F11D677B6B72A146D9486CA09793282955D`
- Steps sweep CSV SHA256: `84934BE4E9C20776DE8DF0498C897E9F0802C56DA9108870D32F323277A2AD1E`
- Parameter sensitivity CSV SHA256: `E5AFFEBA1D028F25BD621F5EC172150307B231AD4F44A9EB90D8C9162760DAD9`
- Summary JSON SHA256: `E7288AA690CBBB07971C21AC9332A77A1DC9C239C38F047EE8623A261A60FC97`

## Claim Boundary

This is a scale behavior report over exact frozen-v5 integer runs. It supports claims about these listed seeds, steps, and one-at-a-time parameter variants only.

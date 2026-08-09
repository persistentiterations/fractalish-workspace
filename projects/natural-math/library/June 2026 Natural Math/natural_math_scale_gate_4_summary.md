# Natural Math v5 Scale Gate 4 Threshold Mapping

Spec SHA256: `E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B`
Seeds: `0-49`
Steps per run: `140`

## Threshold Results


### damage_energy_loss

- `7000`: `50/50` pass, band `stable`, avg alive `30`, avg energy `51824`, success distance `50/50`
- `14000`: `50/50` pass, band `stable`, avg alive `30`, avg energy `44542`, success distance `50/50`
- `17000`: `47/50` pass, band `transition`, avg alive `30`, avg energy `41632`, success distance `49/50`
  - failures: `{'average_energy<38000': 3, 'success_distance_passed=False': 1}`
- `21000`: `26/50` pass, band `transition`, avg alive `30`, avg energy `37895`, success distance `49/50`
  - failures: `{'average_energy<38000': 24, 'success_distance_passed=False': 1}`
- `25000`: `2/50` pass, band `transition`, avg alive `30`, avg energy `34013`, success distance `49/50`
  - failures: `{'average_energy<38000': 48, 'success_distance_passed=False': 1}`

### decay_cost

- `110`: `50/50` pass, band `stable`, avg alive `30`, avg energy `60154`, success distance `50/50`
- `160`: `50/50` pass, band `stable`, avg alive `30`, avg energy `53044`, success distance `50/50`
- `220`: `50/50` pass, band `stable`, avg alive `30`, avg energy `44542`, success distance `50/50`
- `280`: `15/50` pass, band `transition`, avg alive `30`, avg energy `35932`, success distance `49/50`
  - failures: `{'average_energy<38000': 35, 'success_distance_passed=False': 1}`
- `340`: `0/50` pass, band `failure`, avg alive `30`, avg energy `27651`, success distance `48/50`
  - failures: `{'average_energy<38000': 50, 'success_distance_passed=False': 2}`
- `400`: `0/50` pass, band `failure`, avg alive `29`, avg energy `19435`, success distance `45/50`
  - failures: `{'average_energy<38000': 50, 'success_distance_passed=False': 5}`
- `440`: `0/50` pass, band `failure`, avg alive `27`, avg energy `14562`, success distance `42/50`
  - failures: `{'average_energy<38000': 50, 'success_distance_passed=False': 8, 'alive_count<24': 7}`

### max_bonds

- `1`: `0/50` pass, band `failure`, avg alive `0`, avg energy `0`, success distance `0/50`
  - failures: `{'alive_count<24': 50, 'component_count!=1': 50, 'average_energy<38000': 50, 'resource_reached=False': 50, 'success_distance_passed=False': 50}`
- `2`: `7/50` pass, band `transition`, avg alive `26`, avg energy `31317`, success distance `15/50`
  - failures: `{'average_energy<38000': 22, 'success_distance_passed=False': 35, 'alive_count<24': 13}`
- `3`: `41/50` pass, band `transition`, avg alive `29`, avg energy `42019`, success distance `43/50`
  - failures: `{'average_energy<38000': 3, 'success_distance_passed=False': 7, 'alive_count<24': 1}`
- `4`: `50/50` pass, band `stable`, avg alive `30`, avg energy `44542`, success distance `50/50`
- `5`: `50/50` pass, band `stable`, avg alive `30`, avg energy `45050`, success distance `50/50`
- `6`: `50/50` pass, band `stable`, avg alive `30`, avg energy `45274`, success distance `50/50`

### move_cost

- `150`: `50/50` pass, band `stable`, avg alive `30`, avg energy `47277`, success distance `50/50`
- `300`: `50/50` pass, band `stable`, avg alive `30`, avg energy `44542`, success distance `50/50`
- `450`: `43/50` pass, band `transition`, avg alive `30`, avg energy `42001`, success distance `49/50`
  - failures: `{'average_energy<38000': 6, 'success_distance_passed=False': 1}`
- `600`: `30/50` pass, band `transition`, avg alive `30`, avg energy `39508`, success distance `44/50`
  - failures: `{'average_energy<38000': 20, 'success_distance_passed=False': 6}`
- `750`: `25/50` pass, band `transition`, avg alive `30`, avg energy `37050`, success distance `41/50`
  - failures: `{'average_energy<38000': 25, 'success_distance_passed=False': 9}`

### rest_gain

- `80`: `0/50` pass, band `failure`, avg alive `30`, avg energy `28558`, success distance `50/50`
  - failures: `{'average_energy<38000': 50}`
- `110`: `0/50` pass, band `failure`, avg alive `30`, avg energy `31927`, success distance `50/50`
  - failures: `{'average_energy<38000': 50}`
- `140`: `6/50` pass, band `transition`, avg alive `30`, avg energy `35281`, success distance `50/50`
  - failures: `{'average_energy<38000': 44}`
- `170`: `28/50` pass, band `transition`, avg alive `30`, avg energy `38679`, success distance `50/50`
  - failures: `{'average_energy<38000': 22}`
- `200`: `47/50` pass, band `transition`, avg alive `30`, avg energy `42182`, success distance `50/50`
  - failures: `{'average_energy<38000': 3}`
- `220`: `50/50` pass, band `stable`, avg alive `30`, avg energy `44542`, success distance `50/50`
- `260`: `50/50` pass, band `stable`, avg alive `30`, avg energy `49067`, success distance `50/50`
- `300`: `50/50` pass, band `stable`, avg alive `30`, avg energy `53604`, success distance `50/50`
- `360`: `50/50` pass, band `stable`, avg alive `30`, avg energy `60424`, success distance `50/50`
- `440`: `50/50` pass, band `stable`, avg alive `30`, avg energy `69528`, success distance `50/50`

### world_size

- `15`: `49/50` pass, band `transition`, avg alive `29`, avg energy `48999`, success distance `50/50`
  - failures: `{'average_energy<38000': 1}`
- `25`: `50/50` pass, band `stable`, avg alive `30`, avg energy `44542`, success distance `50/50`
- `35`: `24/50` pass, band `transition`, avg alive `29`, avg energy `39688`, success distance `31/50`
  - failures: `{'success_distance_passed=False': 19, 'alive_count<24': 1, 'average_energy<38000': 8}`
- `45`: `12/50` pass, band `transition`, avg alive `22`, avg energy `29647`, success distance `17/50`
  - failures: `{'average_energy<38000': 17, 'success_distance_passed=False': 33, 'alive_count<24': 13, 'component_count!=1': 11, 'resource_reached=False': 11}`
- `60`: `0/50` pass, band `failure`, avg alive `12`, avg energy `16195`, success distance `1/50`
  - failures: `{'alive_count<24': 29, 'component_count!=1': 29, 'average_energy<38000': 33, 'resource_reached=False': 29, 'success_distance_passed=False': 49}`

## Artifact Hashes

- Threshold CSV SHA256: `7AF11987D9F875CA19023C786ABF2E7BDEC481C456EC648C5B1B27A04A329BCE`
- Summary JSON SHA256: `460B062B88B9292D9626AC7E268189AFB532FD87813793F8D30119B45F78C4F3`

## Claim Boundary

This maps one-parameter-at-a-time stability bands for the listed values only. It does not test interacting parameter changes.

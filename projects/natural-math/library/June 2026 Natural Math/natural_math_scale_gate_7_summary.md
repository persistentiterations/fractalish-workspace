# Natural Math v5 Scale Gate 7 Larger Seed Sweep

Spec SHA256: `E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B`
Seeds: `0-499`
Steps: `140`
Runs: `3500`

## Results

- `damage_energy_loss=17000`: `465/500` pass, avg alive `29`, avg energy `41540`, min avg energy `14488`
  - failures: `{'average_energy<38000': 26, 'success_distance_passed=False': 12}`
- `decay_cost=280`: `115/500` pass, avg alive `29`, avg energy `35857`, min avg energy `11667`
  - failures: `{'average_energy<38000': 385, 'success_distance_passed=False': 11}`
- `default`: `494/500` pass, avg alive `29`, avg energy `44398`, min avg energy `14638`
  - failures: `{'average_energy<38000': 6, 'success_distance_passed=False': 1}`
- `max_bonds=3`: `426/500` pass, avg alive `29`, avg energy `42776`, min avg energy `11372`
  - failures: `{'average_energy<38000': 35, 'success_distance_passed=False': 52, 'alive_count<24': 2}`
- `move_cost=450`: `434/500` pass, avg alive `29`, avg energy `41900`, min avg energy `14488`
  - failures: `{'average_energy<38000': 58, 'success_distance_passed=False': 19}`
- `rest_gain=200`: `469/500` pass, avg alive `29`, avg energy `42037`, min avg energy `13787`
  - failures: `{'average_energy<38000': 31, 'success_distance_passed=False': 1}`
- `world_size=35`: `281/500` pass, avg alive `29`, avg energy `40684`, min avg energy `9573`
  - failures: `{'success_distance_passed=False': 183, 'alive_count<24': 1, 'average_energy<38000': 53}`

## Artifact Hashes

- CSV SHA256: `2AEC91B953BFA6AA377B6DAFB4BF9B4A4492CE238392537DE010DC88CC4ACBA4`
- Summary JSON SHA256: `0843317FFBC6E99AD27E6FB22A3E45027F089FB7237611424EF015F596B559EB`

## Claim Boundary

This expands seed coverage for the default and listed boundary settings only. It does not tune parameters or change the frozen model.

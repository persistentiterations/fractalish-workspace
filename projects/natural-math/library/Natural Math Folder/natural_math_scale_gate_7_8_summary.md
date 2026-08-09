# Natural Math v5 Scale Gates 7 and 8

Spec SHA256: `E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B`

## Gate 7: Larger Seed Sweep

Seeds: `0-499`
Steps: `140`

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

## Gate 8: Long-Run Stability

Seeds: `0-199`
Steps: `[140, 300, 600, 1000]`

- `default`, steps `140`: `196/200` pass, avg alive `29`, avg energy `44269`, resource reached `200/200`
  - failures: `{'average_energy<38000': 4, 'success_distance_passed=False': 1}`
- `default`, steps `300`: `196/200` pass, avg alive `29`, avg energy `44269`, resource reached `200/200`
  - failures: `{'average_energy<38000': 4, 'success_distance_passed=False': 1}`
- `default`, steps `600`: `196/200` pass, avg alive `29`, avg energy `44269`, resource reached `200/200`
  - failures: `{'average_energy<38000': 4, 'success_distance_passed=False': 1}`
- `default`, steps `1000`: `196/200` pass, avg alive `29`, avg energy `44269`, resource reached `200/200`
  - failures: `{'average_energy<38000': 4, 'success_distance_passed=False': 1}`
- `stable_stressed_resource_absorb_rate=7000`, steps `140`: `197/200` pass, avg alive `29`, avg energy `45058`, resource reached `200/200`
  - failures: `{'average_energy<38000': 3, 'alive_count<24': 1}`
- `stable_stressed_resource_absorb_rate=7000`, steps `300`: `197/200` pass, avg alive `29`, avg energy `45058`, resource reached `200/200`
  - failures: `{'average_energy<38000': 3, 'alive_count<24': 1}`
- `stable_stressed_resource_absorb_rate=7000`, steps `600`: `197/200` pass, avg alive `29`, avg energy `45058`, resource reached `200/200`
  - failures: `{'average_energy<38000': 3, 'alive_count<24': 1}`
- `stable_stressed_resource_absorb_rate=7000`, steps `1000`: `197/200` pass, avg alive `29`, avg energy `45058`, resource reached `200/200`
  - failures: `{'average_energy<38000': 3, 'alive_count<24': 1}`
- `stable_stressed_rest260_damage17000`, steps `140`: `197/200` pass, avg alive `29`, avg energy `45610`, resource reached `200/200`
  - failures: `{'average_energy<38000': 3, 'success_distance_passed=False': 1}`
- `stable_stressed_rest260_damage17000`, steps `300`: `198/200` pass, avg alive `29`, avg energy `51986`, resource reached `200/200`
  - failures: `{'average_energy<38000': 2}`
- `stable_stressed_rest260_damage17000`, steps `600`: `199/200` pass, avg alive `29`, avg energy `63986`, resource reached `200/200`
  - failures: `{'average_energy<38000': 1}`
- `stable_stressed_rest260_damage17000`, steps `1000`: `200/200` pass, avg alive `29`, avg energy `79972`, resource reached `200/200`

## Artifact Hashes

- Gate 7 CSV SHA256: `2AEC91B953BFA6AA377B6DAFB4BF9B4A4492CE238392537DE010DC88CC4ACBA4`
- Gate 8 CSV SHA256: `E1F586E75BC35396360D66BA4403AD0DE68241581AADC33AB9004FB37B131B71`
- Summary JSON SHA256: `DCAB048E7506E1FC779EAD1C28201210D4FE0CF94A5CB1E1B1F6ECEABDF911B4`

## Claim Boundary

Gate 7 expands seed coverage for the default and listed boundary settings. Gate 8 checks long-run stability for the default and listed stable-stressed settings. These gates do not tune parameters, alter the model, or validate future extensions.

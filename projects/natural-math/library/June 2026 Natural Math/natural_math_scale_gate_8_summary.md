# Natural Math v5 Scale Gate 8 Long-Run Stability

Spec SHA256: `E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B`
Seeds: `0-199`
Steps: `[140, 300, 600, 1000]`
Runs: `2400`

## Results

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

- CSV SHA256: `E1F586E75BC35396360D66BA4403AD0DE68241581AADC33AB9004FB37B131B71`
- Summary JSON SHA256: `0E6D90312E42E76BE4ABF20B8DF291A8F5F3FA321E0DAC1A544931AF74797BBF`

## Claim Boundary

This checks long-run stability for the default and listed stable-stressed settings only. It does not tune parameters or change the frozen model.

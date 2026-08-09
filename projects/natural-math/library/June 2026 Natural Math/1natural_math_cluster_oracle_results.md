# Natural Math v5 Cluster Oracle Provenance Report

Overall result: PASS
Cases passed: 15/15

## Provenance

- Spec path: `C:\Users\big_b\Downloads\Natural Math v5 - Status Frozen Int.txt`
- Spec SHA256 expected: `E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B`
- Spec SHA256 actual: `E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B`
- Fixture path: `C:\Users\big_b\Documents\Codex\2026-06-22\we\outputs\natural_math_cluster_oracle_fixtures.json`
- Fixture SHA256: `031B21ECD272ECB8E47A7AA517C6DFD9B4E97B3507254F2228B6EFC101AF0BC2`
- Runner: `natural_math_cluster_oracle_runner.py`

## Covered Sections

- 18 Cluster Benchmark
- 19 Cluster Step
- 20 Cluster Metrics
- 21 Cluster Actions
- 22 Cluster Result

## Case Results

- PASS `cluster_seed_3_initialization_summary` (initialization)
  - resource_pos: `[2, 24, 0]`
  - live_bond_pair_count: `51`
  - random_bond_draw_count: `435`
  - metrics: `{'alive_count': 30, 'component_count': 1, 'average_energy': 55206, 'min_energy': 50248, 'center_sum': [365, 368, 0], 'center_denominator': 30, 'success_distance_passed': False, 'gini_num': 1701188, 'gini_den': 49685880, 'gini_over_threshold': False}`
- PASS `cluster_seed_11_initialization_summary` (initialization)
  - resource_pos: `[2, 6, 0]`
  - live_bond_pair_count: `49`
  - random_bond_draw_count: `435`
  - metrics: `{'alive_count': 30, 'component_count': 1, 'average_energy': 55249, 'min_energy': 50008, 'center_sum': [353, 350, 0], 'center_denominator': 30, 'success_distance_passed': False, 'gini_num': 1523492, 'gini_den': 49724100, 'gini_over_threshold': False}`
- PASS `cluster_metrics_empty_state` (metrics)
- PASS `cluster_metrics_connected_success_low_gini` (metrics)
- PASS `cluster_metrics_fragmented_high_gini_far_resource` (metrics)
- PASS `cluster_action_policy_seek_moves_toward_resource` (action)
  - selected_action: `SEEK`
  - resource_left: `450000`
  - resource_reached: `False`
  - rng_draws: `[474354, 907796]`
- PASS `cluster_action_policy_rest_adds_rest_gain` (action)
  - selected_action: `REST`
  - resource_left: `450000`
  - resource_reached: `True`
  - rng_draws: `[]`
- PASS `cluster_action_redistribute_transfers_energy_over_live_bond` (action)
  - selected_action: `REDISTRIBUTE`
  - resource_left: `450000`
  - resource_reached: `False`
  - rng_draws: `[]`
- PASS `cluster_action_policy_repair_fragmented_adds_first_valid_bond` (action)
  - selected_action: `REPAIR`
  - resource_left: `450000`
  - resource_reached: `False`
  - rng_draws: `[474354]`
- PASS `cluster_resource_absorption_shares_integer_energy` (action)
  - selected_action: `None`
  - resource_left: `1`
  - resource_reached: `True`
  - rng_draws: `[]`
- PASS `cluster_damage_loses_energy_and_breaks_seeded_bonds` (damage)
  - live_bond_pairs: `[[1, 2]]`
  - rng_draws: `[474354, 907796]`
- PASS `cluster_seed_3_steps_0_exact_result` (cluster_run)
  - alive_count: `30`
  - resource_left: `450000`
  - resource_reached: `False`
  - passed: `False`
  - rng_ppm_draw_count: `435`
- PASS `cluster_seed_3_steps_1_exact_result` (cluster_run)
  - alive_count: `30`
  - resource_left: `450000`
  - resource_reached: `False`
  - passed: `False`
  - rng_ppm_draw_count: `465`
- PASS `cluster_seed_3_steps_35_damage_gate_exact_result` (cluster_run)
  - alive_count: `30`
  - resource_left: `0`
  - resource_reached: `True`
  - passed: `True`
  - rng_ppm_draw_count: `1206`
- PASS `cluster_seed_3_steps_140_exact_result` (cluster_run)
  - alive_count: `30`
  - resource_left: `0`
  - resource_reached: `True`
  - passed: `True`
  - rng_ppm_draw_count: `1206`

## Claim Boundary

This report validates cluster initialization summaries, standalone metrics fixtures, cluster action/resource micro-fixtures, damage micro-fixtures, and listed seeded cluster runs. A 140-step pass is a validation claim only for an exact listed seed fixture.

# Natural Math v5 Integer Oracle Provenance Report

Overall result: FAIL
Cases passed: 20/20

## Provenance

- Spec path: `C:\Users\big_b\Downloads\Natural Math v5 - Status Frozen Int.txt`
- Spec SHA256 expected: `E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B`
- Spec SHA256 actual: `None`
- Fixture path: `C:\June 2026 Natural Math\natural_math_integer_oracle_fixtures.json`
- Fixture SHA256: `B00CCD05CDFC0CAC5C635CE80F5B71844B393335B0EDDC29F73C7C0FE66BA536`
- Runner: `natural_math_integer_oracle_runner.py`

## Covered Sections

- 2 Integer Number Rule
- 2A Entry Points
- 3 Node Record
- 4 Node Types And Occupancy
- 5 Parameters
- 6 Validation Rules
- 7 Helper Rules
- 8 Randomness
- 10 Integer Gradient Choice
- 11 Contact And Decisions
- 12 One Full run_step
- 13 Movement And Blocking
- 14 Bifurcation
- 15 Child Direction Table
- 16 Pressure
- 17 Bonding

## Case Results

- PASS `empty_list_returns_empty`
- PASS `energy_below_tau_restrict_dies_before_pressure`
- PASS `duplicate_live_position_contact_death`
- PASS `adjacent_live_nodes_sense_and_pressure`
- PASS `integer_gradient_successful_extend`
- PASS `fallback_extend_with_seeded_rng`
  - rng seed: `11`
  - draw_ppm trace: `[474354]`
- PASS `blocked_fallback_target_pays_sense_and_conflict_pressure`
  - rng seed: `11`
  - draw_ppm trace: `[474354]`
- PASS `contested_unblocked_fallback_target_high_energy_wins`
  - rng seed: `7`
  - draw_ppm trace: `[339563, 993908]`
- PASS `bifurcation_successful_split_from_fallback_extend`
  - rng seed: `11`
  - draw_ppm trace: `[474354]`
- PASS `bifurcation_pressure_below_threshold_moves_normally`
  - rng seed: `11`
  - draw_ppm trace: `[474354]`
- PASS `bifurcation_energy_threshold_must_be_strictly_greater`
  - rng seed: `11`
  - draw_ppm trace: `[474354]`
- PASS `bifurcation_child_position_blocked_by_frozen_occupancy`
  - rng seed: `11`
  - draw_ppm trace: `[474354]`
- PASS `bifurcation_child_position_outside_boundary_moves_normally`
  - rng seed: `11`
  - draw_ppm trace: `[474354]`
- PASS `bifurcation_reserved_child_position_blocks_later_split`
  - rng seed: `7`
  - draw_ppm trace: `[339563, 993908]`
- PASS `bonding_adjacent_pair_forms_after_pressure_and_equalizes_energy`
- PASS `bonding_strict_rejects_distance_equal_to_threshold`
  - rng seed: `11`
  - draw_ppm trace: `[474354, 907796]`
- PASS `bonding_non_strict_allows_distance_equal_to_threshold`
  - rng seed: `11`
  - draw_ppm trace: `[474354, 907796]`
- PASS `bonding_max_live_degree_blocks_extra_pairs`
- PASS `bonding_historical_dead_bonds_do_not_count_against_live_capacity`
- PASS `bonding_collapse_positions_keeps_bonded_duplicate_live_nodes_alive`

## Claim Boundary

This report proves only that the listed integer fixture packs pass this runner against the named frozen spec hash. It is not a claim that all Natural Math v5 behavior is validated.

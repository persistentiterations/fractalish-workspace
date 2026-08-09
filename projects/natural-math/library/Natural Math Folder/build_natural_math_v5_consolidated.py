#!/usr/bin/env python3
"""Build the consolidated Natural Math v5 frozen base working paper."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(r"C:\Users\big_b\Documents\Codex\2026-06-22\we")
OUT = ROOT / "outputs"
SOURCE = Path(r"C:\Users\big_b\Downloads\Natural Math v5 - Status Frozen Int.txt")
DEST = OUT / "Natural Math v5 - Frozen Integer Base and Validation Record.md"


SPEC_SHA256 = "E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B"


ARTIFACTS = [
    ("Frozen integer source", SOURCE),
    ("Integer oracle fixtures", OUT / "natural_math_integer_oracle_fixtures.json"),
    ("Integer oracle runner", OUT / "natural_math_integer_oracle_runner.py"),
    ("Integer oracle results", OUT / "natural_math_integer_oracle_results.md"),
    ("Cluster oracle fixtures", OUT / "natural_math_cluster_oracle_fixtures.json"),
    ("Cluster oracle runner", OUT / "natural_math_cluster_oracle_runner.py"),
    ("Cluster oracle results", OUT / "natural_math_cluster_oracle_results.md"),
    ("Scale Gate 1-3 runner", OUT / "natural_math_scale_gate_runner.py"),
    ("Scale Gate 1 seed sweep CSV", OUT / "natural_math_scale_gate_seed_sweep.csv"),
    ("Scale Gate 2 steps sweep CSV", OUT / "natural_math_scale_gate_steps_sweep.csv"),
    ("Scale Gate 3 parameter sensitivity CSV", OUT / "natural_math_scale_gate_parameter_sensitivity.csv"),
    ("Scale Gate 1-3 summary JSON", OUT / "natural_math_scale_gate_summary.json"),
    ("Scale Gate 1-3 summary report", OUT / "natural_math_scale_gate_summary.md"),
    ("Scale Gate 4 runner", OUT / "natural_math_scale_gate_4_runner.py"),
    ("Scale Gate 4 threshold mapping CSV", OUT / "natural_math_scale_gate_4_threshold_mapping.csv"),
    ("Scale Gate 4 summary JSON", OUT / "natural_math_scale_gate_4_summary.json"),
    ("Scale Gate 4 summary report", OUT / "natural_math_scale_gate_4_summary.md"),
    ("Scale Gate 5 runner", OUT / "natural_math_scale_gate_5_runner.py"),
    ("Scale Gate 5 raw interaction CSV", OUT / "natural_math_scale_gate_5_two_parameter_interactions.csv"),
    ("Scale Gate 5 cell summary CSV", OUT / "natural_math_scale_gate_5_two_parameter_cells.csv"),
    ("Scale Gate 5 summary JSON", OUT / "natural_math_scale_gate_5_summary.json"),
    ("Scale Gate 5 summary report", OUT / "natural_math_scale_gate_5_summary.md"),
    ("Scale Gate 6 runner", OUT / "natural_math_scale_gate_6_runner.py"),
    ("Scale Gate 6 per-step history CSV", OUT / "natural_math_scale_gate_6_per_step_history.csv"),
    ("Scale Gate 6 run classification CSV", OUT / "natural_math_scale_gate_6_run_classification.csv"),
    ("Scale Gate 6 failure summary CSV", OUT / "natural_math_scale_gate_6_failure_summary_by_cell.csv"),
    ("Scale Gate 6 summary JSON", OUT / "natural_math_scale_gate_6_summary.json"),
    ("Scale Gate 6 summary report", OUT / "natural_math_scale_gate_6_summary.md"),
    ("Scale Gate 7 runner", OUT / "natural_math_scale_gate_7_runner.py"),
    ("Scale Gate 7 larger seed sweep CSV", OUT / "natural_math_scale_gate_7_larger_seed_sweep_clean.csv"),
    ("Scale Gate 7 summary JSON", OUT / "natural_math_scale_gate_7_summary.json"),
    ("Scale Gate 7 summary report", OUT / "natural_math_scale_gate_7_summary.md"),
    ("Scale Gate 8 runner", OUT / "natural_math_scale_gate_8_runner.py"),
    ("Scale Gate 8 long-run stability CSV", OUT / "natural_math_scale_gate_8_long_run_stability_clean.csv"),
    ("Scale Gate 8 summary JSON", OUT / "natural_math_scale_gate_8_summary.json"),
    ("Scale Gate 8 summary report", OUT / "natural_math_scale_gate_8_summary.md"),
]


def sha256(path: Path) -> str:
    if not path.exists():
        return "not provided"
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def artifact_table() -> str:
    lines = [
        "| Artifact | Path | SHA256 |",
        "|---|---|---|",
    ]
    for name, path in ARTIFACTS:
        digest = sha256(path)
        display_path = str(path)
        lines.append(f"| {name} | `{display_path}` | `{digest}` |")
    return "\n".join(lines)


def validation_tail() -> str:
    return f"""## 23. Validation Record

This section records validation results for the frozen integer base. It does not add model behavior, new mechanics, future extensions, or theory claims.

- Local integer oracle suite passed: 25/25.
- Cluster oracle suite passed: 15/15.
- Total validated fixtures: 40/40.
- Default seed sweep, seeds 0-499, steps 140: default passed 494/500.
- Step sweep showed default behavior stabilizing after enough steps.
- One-parameter threshold sweeps mapped stability, transition, and failure bands.
- Two-parameter interaction sweeps mapped compensation, transition, stability, and collapse zones.
- Failure diagnosis classified weak-zone failures by energy collapse, recovery failure, distance failure, fragmentation, population loss, resource failure, and post-damage failure.
- Long-run stability testing checked selected conditions through 1000 steps and did not show slow collapse under the tested conditions.

The larger seed sweep also tested these boundary settings at seeds 0-499, steps 140:

| Setting | Result |
|---|---:|
| default | 494/500 |
| rest_gain=200 | 469/500 |
| decay_cost=280 | 115/500 |
| max_bonds=3 | 426/500 |
| world_size=35 | 281/500 |
| damage_energy_loss=17000 | 465/500 |
| move_cost=450 | 434/500 |

The long-run stability gate tested seeds 0-199 at steps 140, 300, 600, and 1000:

| Setting | 140 | 300 | 600 | 1000 |
|---|---:|---:|---:|---:|
| default | 196/200 | 196/200 | 196/200 | 196/200 |
| resource_absorb_rate=7000 | 197/200 | 197/200 | 197/200 | 197/200 |
| rest_gain=260 and damage_energy_loss=17000 | 197/200 | 198/200 | 199/200 | 200/200 |

---

## 24. Strongest Honest Claim

Natural Math v5 frozen integer base passed exact oracle validation, showed strong default stability across seeds 0-499 at 140 steps, mapped single- and two-parameter stability/failure regions, diagnosed failure modes, and showed no slow-collapse pattern in the tested long-run conditions through 1000 steps.

These results validate the listed frozen-v5 benchmark behavior under the tested seeds, steps, parameters, fixtures, and runner artifacts. They do not prove all possible seeds, all parameter combinations, future extensions, production readiness, or a complete theory claim.

---

## 25. Claim Boundaries

- This is a frozen integer base, not a final theory proof.
- Validation applies only to the listed fixtures, seeds, parameters, step counts, and benchmark conditions.
- Older decimal or non-integer results do not transfer automatically.
- Future behavior is not base behavior unless it has integer rules, exact fixtures, known outputs, and validation.
- Any new feature must be versioned separately and tested against this frozen base.
- The cluster benchmark is open-system because resource absorption adds external energy.
- For runs other than 140 steps, `passed` remains the same diagnostic; validation claims are limited to the cited test conditions and artifacts.

---

## 26. Artifact Provenance

Primary frozen source SHA256: `{SPEC_SHA256}`

{artifact_table()}

---

## 27. Do Not Add Yet

The following items are intentionally excluded from this frozen base because they are not part of the validated integer rule source:

- Local Flow Trail Memory.
- Scars.
- Roles.
- Dead-end behavior.
- Backing-out behavior.
- Maze logic.
- Global planning.
- Learned behavior.
- BFS.
- A*.
- Hidden maps.
- Decimal or continuous fields.
- Any other unvalidated behavior or future extension.

---

## 28. Rule For Future Changes

A future change is not base behavior unless:

1. It uses integer arithmetic only.
2. It has complete input fixtures.
3. It has exact known outputs.
4. It lists the random seed and exact random-call order if stochastic.
5. It says whether it is closed-system or open-system.
6. It is written plainly enough that a student can restate the rule without hidden project history.
7. It is versioned separately when it adds behavior beyond this frozen base.
8. It is tested against this frozen base when the purpose is to compare an extension against v5.

---

## 29. Change Log

- Inserted the completed Validation Record.
- Inserted the Strongest Honest Claim.
- Inserted explicit Claim Boundaries.
- Inserted Artifact Provenance using available local artifact hashes; missing artifacts would be marked `not provided`.
- Inserted the Do Not Add Yet exclusion list.
- Consolidated the older Current Validation Status, Known Limits, Future Work, and Rule For Future Changes sections into the updated validation and boundary sections.
- Removed the outdated statement that no standalone pass claim exists, because integer fixtures and scale-gate validation artifacts now exist.
- Removed outdated future-work bullets that requested fixture creation for core movement, bifurcation, bonding, PoC scream, and cluster behavior, because those fixtures are now represented by the validated oracle suites.
- Preserved the frozen base rule sections before the validation record without adding new behavior.
"""


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    marker = "\n## 23. Current Validation Status"
    if marker not in text:
        raise RuntimeError("could not find validation status section")
    rules = text.split(marker, 1)[0].rstrip()
    lines = rules.splitlines()
    lines[0] = "# Natural Math v5 — Frozen Integer Base and Validation Record"
    body = "\n".join(lines)
    DEST.write_text(body + "\n\n" + validation_tail(), encoding="utf-8")
    print(DEST)
    print(sha256(DEST))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

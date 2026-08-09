#!/usr/bin/env python3
"""Scale Gate 7 larger seed sweep for Natural Math v5."""

from __future__ import annotations

import json
from pathlib import Path

from natural_math_cluster_oracle_runner import sha256
from natural_math_scale_gate_7_8_runner import (
    GATE7_SEEDS,
    GATE7_STEPS,
    GATE7_VARIANTS,
    SPEC_PATH,
    SPEC_SHA256,
    file_hash,
    run_gate7,
    summarize,
    write_csv,
)


def main() -> int:
    out_dir = Path(__file__).resolve().parent
    if sha256(SPEC_PATH) != SPEC_SHA256:
        raise RuntimeError("spec hash mismatch")

    rows = run_gate7()
    summary = summarize(rows, ["variant"])

    csv_path = out_dir / "natural_math_scale_gate_7_larger_seed_sweep_clean.csv"
    json_path = out_dir / "natural_math_scale_gate_7_summary.json"
    md_path = out_dir / "natural_math_scale_gate_7_summary.md"
    write_csv(csv_path, rows)

    payload = {
        "suite": "Natural Math v5 Scale Gate 7 larger seed sweep",
        "spec_path": str(SPEC_PATH),
        "spec_sha256": SPEC_SHA256,
        "seeds": [GATE7_SEEDS[0], GATE7_SEEDS[-1]],
        "seed_count": len(GATE7_SEEDS),
        "steps": GATE7_STEPS,
        "variants": GATE7_VARIANTS,
        "run_count": len(rows),
        "summary": summary,
        "csv": str(csv_path),
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Natural Math v5 Scale Gate 7 Larger Seed Sweep",
        "",
        f"Spec SHA256: `{SPEC_SHA256}`",
        f"Seeds: `{GATE7_SEEDS[0]}-{GATE7_SEEDS[-1]}`",
        f"Steps: `{GATE7_STEPS}`",
        f"Runs: `{len(rows)}`",
        "",
        "## Results",
        "",
    ]
    for item in summary:
        lines.append(
            f"- `{item['variant']}`: `{item['pass_rate']}` pass, avg alive `{item['avg_alive_count']}`, "
            f"avg energy `{item['avg_average_energy']}`, min avg energy `{item['min_average_energy']}`"
        )
        if item["failure_counts"]:
            lines.append(f"  - failures: `{item['failure_counts']}`")
    lines.extend(
        [
            "",
            "## Artifact Hashes",
            "",
            f"- CSV SHA256: `{file_hash(csv_path)}`",
            f"- Summary JSON SHA256: `{file_hash(json_path)}`",
            "",
            "## Claim Boundary",
            "",
            "This expands seed coverage for the default and listed boundary settings only. It does not tune parameters or change the frozen model.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"passed": True, "runs": len(rows), "summary": str(md_path), "csv": str(csv_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

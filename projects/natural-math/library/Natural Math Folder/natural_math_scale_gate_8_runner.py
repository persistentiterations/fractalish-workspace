#!/usr/bin/env python3
"""Scale Gate 8 long-run stability for Natural Math v5."""

from __future__ import annotations

import json
from pathlib import Path

from natural_math_cluster_oracle_runner import sha256
from natural_math_scale_gate_7_8_runner import (
    GATE8_SEEDS,
    GATE8_STEPS,
    GATE8_VARIANTS,
    SPEC_PATH,
    SPEC_SHA256,
    file_hash,
    run_gate8,
    summarize,
    write_csv,
)


def main() -> int:
    out_dir = Path(__file__).resolve().parent
    if sha256(SPEC_PATH) != SPEC_SHA256:
        raise RuntimeError("spec hash mismatch")

    rows = run_gate8()
    summary = summarize(rows, ["variant", "steps"])

    csv_path = out_dir / "natural_math_scale_gate_8_long_run_stability_clean.csv"
    json_path = out_dir / "natural_math_scale_gate_8_summary.json"
    md_path = out_dir / "natural_math_scale_gate_8_summary.md"
    write_csv(csv_path, rows)

    payload = {
        "suite": "Natural Math v5 Scale Gate 8 long-run stability",
        "spec_path": str(SPEC_PATH),
        "spec_sha256": SPEC_SHA256,
        "seeds": [GATE8_SEEDS[0], GATE8_SEEDS[-1]],
        "seed_count": len(GATE8_SEEDS),
        "steps": GATE8_STEPS,
        "variants": GATE8_VARIANTS,
        "run_count": len(rows),
        "summary": summary,
        "csv": str(csv_path),
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Natural Math v5 Scale Gate 8 Long-Run Stability",
        "",
        f"Spec SHA256: `{SPEC_SHA256}`",
        f"Seeds: `{GATE8_SEEDS[0]}-{GATE8_SEEDS[-1]}`",
        f"Steps: `{GATE8_STEPS}`",
        f"Runs: `{len(rows)}`",
        "",
        "## Results",
        "",
    ]
    for item in summary:
        lines.append(
            f"- `{item['variant']}`, steps `{item['steps']}`: `{item['pass_rate']}` pass, "
            f"avg alive `{item['avg_alive_count']}`, avg energy `{item['avg_average_energy']}`, "
            f"resource reached `{item['resource_reached']}/{item['runs']}`"
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
            "This checks long-run stability for the default and listed stable-stressed settings only. It does not tune parameters or change the frozen model.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"passed": True, "runs": len(rows), "summary": str(md_path), "csv": str(csv_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

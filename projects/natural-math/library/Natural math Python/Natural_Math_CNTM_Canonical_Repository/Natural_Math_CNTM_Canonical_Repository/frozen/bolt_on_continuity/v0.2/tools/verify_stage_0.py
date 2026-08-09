#!/usr/bin/env python3
"""Verify the Bolt-On Continuity for Docker v0.2 Stage 0 contract."""

from __future__ import annotations

import sys
from pathlib import Path


BASELINE_COMMIT = "205bee21b279fa63aef510fb23854eab17d44eb7"
PRODUCT_ROOT_NAME = "bolt_on_continuity_v0_2"

REQUIRED_FILES = {
    "README.md": (
        "Bolt-On Continuity for Docker v0.2",
        BASELINE_COMMIT,
        "observation-only",
    ),
    "PRODUCT_CONTRACT.md": (
        "BONACQUI_BOLT_ON_CONTINUITY_DOCKER_PRODUCT_CONTRACT_0_2_STAGE_0",
        "full 64-character immutable container ID",
        "No autonomous-action mode is defined for v0.2",
        "Frozen-baseline rule",
    ),
    "AUTHORITY_AND_CLAIM_BOUNDARY.md": (
        "docker inspect <full 64-character container ID>",
        "docker pause <full 64-character container ID>",
        "docker unpause <full 64-character container ID>",
        "docker restart",
        "When safe execution cannot be proven",
    ),
    "REUSE_AND_QUALIFICATION_MATRIX.md": (
        "Frozen v0.1 is a proven engine baseline",
        "Canonical serialization",
        "Clean-environment usability",
        "No silent inheritance",
    ),
    "STAGE_0_GATES.md": (
        "Gate 1 — Isolated development location",
        "Gate 8 — Authority ceiling",
        "Gate 12 — Repository verification",
        BASELINE_COMMIT,
    ),
}

PROHIBITED_OPERATIONAL_MARKERS = (
    "subprocess.run([\"docker\"",
    "subprocess.Popen([\"docker\"",
    "os.system(\"docker ",
    "docker.from_env(",
    "import docker",
)

ALLOWED_STAGE_0_SUFFIXES = {".md", ".py"}


def locate_product_root() -> Path:
    here = Path(__file__).resolve()
    product_root = here.parent.parent
    if product_root.name != PRODUCT_ROOT_NAME:
        raise RuntimeError(f"unexpected product root: {product_root}")
    return product_root


def verify_required_files(product_root: Path, errors: list[str]) -> None:
    for relative_path, markers in REQUIRED_FILES.items():
        path = product_root / relative_path
        if not path.is_file():
            errors.append(f"missing required file: {relative_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"missing marker in {relative_path}: {marker!r}")


def verify_stage_structure(product_root: Path, errors: list[str]) -> None:
    allowed_files = set(REQUIRED_FILES) | {"tools/verify_stage_0.py"}
    for path in sorted(product_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(product_root).as_posix()
        if path.suffix not in ALLOWED_STAGE_0_SUFFIXES:
            errors.append(f"unexpected Stage 0 file type: {relative}")
        if relative not in allowed_files:
            errors.append(f"unexpected Stage 0 file: {relative}")


def verify_no_operational_docker(product_root: Path, errors: list[str]) -> None:
    for path in sorted(product_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if path.name == "verify_stage_0.py":
            # The verifier contains marker strings as data; exclude the tuple block.
            scan_text = text.split("PROHIBITED_OPERATIONAL_MARKERS =", 1)[0]
        else:
            scan_text = text
        for marker in PROHIBITED_OPERATIONAL_MARKERS:
            if marker in scan_text:
                relative = path.relative_to(product_root).as_posix()
                errors.append(f"operational Docker marker in {relative}: {marker!r}")


def main() -> int:
    errors: list[str] = []
    try:
        product_root = locate_product_root()
        verify_required_files(product_root, errors)
        verify_stage_structure(product_root, errors)
        verify_no_operational_docker(product_root, errors)
    except Exception as exc:  # deterministic top-level failure reporting
        errors.append(f"verifier exception: {exc}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("BOLT-ON CONTINUITY V0.2 STAGE 0 VERIFICATION: FAIL")
        return 1

    print("Verified isolated Stage 0 product contract files.")
    print("Verified immutable v0.1 baseline references.")
    print("Verified unchanged Docker authority ceiling.")
    print("Verified no operational Docker code in v0.2 Stage 0.")
    print("BOLT-ON CONTINUITY V0.2 STAGE 0 VERIFICATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

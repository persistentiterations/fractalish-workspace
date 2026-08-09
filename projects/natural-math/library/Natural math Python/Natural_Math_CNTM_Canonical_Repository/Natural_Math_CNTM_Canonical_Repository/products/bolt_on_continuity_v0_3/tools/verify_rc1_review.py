"""Verify the complete v0.3 candidate tree for formal RC review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
REQUIRED_FILES = {
    "README.md",
    "docs/RC1_PREPARATION_CONTRACT.md",
    "docs/RC1_REVIEW_CONTRACT.md",
    "src/bolt_on/rc1_preparation.py",
    "tests/test_rc1_preparation.py",
    "tests/test_rc1_review.py",
    "tools/verify_rc1_preparation.py",
    "tools/verify_rc1_review.py",
    *(f"tools/verify_stage_{index}.py" for index in range(11)),
}
REQUIRED_README_TERMS = {
    "Stages 0–10",
    "native execution unauthorized",
    "container mutation unauthorized",
    "RC1 is therefore not approved for freezing",
}


def fail(message: str) -> None:
    raise SystemExit(f"RC1 FORMAL REVIEW VERIFICATION FAILED: {message}")


def included_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(relative)
    return sorted(files, key=lambda item: item.as_posix())


def verify_required_files(files: list[Path]) -> None:
    names = {path.as_posix() for path in files}
    missing = sorted(REQUIRED_FILES - names)
    if missing:
        fail(f"missing required files: {missing}")


def verify_no_generated_artifacts(files: list[Path]) -> None:
    for relative in files:
        if any(part in EXCLUDED_PARTS for part in relative.parts) or relative.suffix in EXCLUDED_SUFFIXES:
            fail(f"generated artifact included: {relative.as_posix()}")


def verify_readme() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    missing = sorted(term for term in REQUIRED_README_TERMS if term not in text)
    if missing:
        fail(f"README review terms missing: {missing}")


def tree_manifest(files: list[Path]) -> tuple[str, int]:
    entries = []
    for relative in files:
        data = (ROOT / relative).read_bytes()
        entries.append(
            {
                "bytes": len(data),
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest(), len(entries)


def run() -> None:
    files = included_files()
    verify_required_files(files)
    verify_no_generated_artifacts(files)
    verify_readme()
    digest, count = tree_manifest(files)
    print(f"RC CANDIDATE TREE FILES {count}")
    print(f"RC CANDIDATE TREE SHA256 {digest}")
    print("RC1 DISPOSITION NEEDS_CORRECTION")
    print("BOLT-ON CONTINUITY V0.3 RC1 FORMAL REVIEW VERIFICATION PASSED")


if __name__ == "__main__":
    run()

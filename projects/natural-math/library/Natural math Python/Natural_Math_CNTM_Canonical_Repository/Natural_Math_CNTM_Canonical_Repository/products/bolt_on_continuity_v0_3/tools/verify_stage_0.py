"""Deterministic Stage 0 verifier with a stage-scoped authority set."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.configuration import ProductConfiguration
from bolt_on.receipts import CanonicalReceipt

FORBIDDEN_IMPORTS = {"docker", "subprocess"}
AUTHORITY_FILES = (
    "pyproject.toml",
    "PRODUCT_CONTRACT.md",
    "AUTHORITY_AND_CLAIM_BOUNDARY.md",
    "docs/STAGE_0_CONTRACT.md",
    "docs/STAGE_0_GATES.md",
    "src/bolt_on/__init__.py",
    "src/bolt_on/version.py",
    "src/bolt_on/core.py",
    "src/bolt_on/configuration.py",
    "src/bolt_on/receipts.py",
    "src/bolt_on/storage.py",
    "src/bolt_on/docker_adapter.py",
    "src/bolt_on/modules.py",
    "tests/conftest.py",
    "tests/test_stage_0.py",
    "tools/verify_stage_0.py",
)


def fail(message: str) -> None:
    raise SystemExit(f"STAGE 0 VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [path for path in AUTHORITY_FILES if not (ROOT / path).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_import_boundary() -> None:
    for relative in AUTHORITY_FILES:
        path = ROOT / relative
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = {node.module.split(".")[0]}
            else:
                continue
            forbidden = names & FORBIDDEN_IMPORTS
            if forbidden:
                fail(f"forbidden import {sorted(forbidden)} in {path.relative_to(ROOT)}")


def verify_contracts() -> None:
    config = ProductConfiguration()
    config.validate()
    if not config.observation_only or config.telemetry_enabled or config.enabled_modules:
        fail("unsafe configuration defaults")
    receipt = CanonicalReceipt("stage0.example", 1, {"b": 2, "a": 1})
    expected = "27512887656836eb9acf44756e12c23ffdf9369d0d8cda5490f7ea16b41b60cf"
    if receipt.digest() != expected:
        fail("canonical receipt vector mismatch")


def manifest_digest() -> str:
    entries = []
    for relative in AUTHORITY_FILES:
        data = (ROOT / relative).read_bytes()
        entries.append({"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run() -> None:
    verify_files()
    verify_import_boundary()
    verify_contracts()
    print(f"STAGE 0 MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 STAGE 0 VERIFICATION PASSED")


if __name__ == "__main__":
    run()

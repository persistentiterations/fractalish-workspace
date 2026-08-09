from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

FINAL_PASS = "BOLT-ON CONTINUITY V0.2 STAGE 1 VERIFICATION: PASS"
FINAL_FAIL = "BOLT-ON CONTINUITY V0.2 STAGE 1 VERIFICATION: FAIL"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    print(FINAL_FAIL)
    raise SystemExit(1)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    product_root = Path(__file__).resolve().parents[1]
    repo_root = product_root.parents[1]

    required = [
        product_root / "README_STAGE_1.md",
        product_root / "docs" / "STAGE_1_CONTRACT.md",
        product_root / "docs" / "STAGE_1_GATES.md",
        product_root / "config" / "frozen_engine_boundary.json",
        product_root / "src" / "bolt_on_continuity_v0_2" / "__init__.py",
        product_root / "src" / "bolt_on_continuity_v0_2" / "engine_boundary.py",
        product_root / "tests" / "test_stage_1_scaffold.py",
    ]
    for path in required:
        if not path.is_file():
            fail(f"missing required file: {path.relative_to(repo_root)}")

    manifest_path = product_root / "config" / "frozen_engine_boundary.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"manifest cannot be loaded: {exc}")

    if manifest.get("schema_version") != 1 or manifest.get("stage") != 1:
        fail("unsupported manifest schema or stage")
    if manifest.get("allowed_actions") != ["NO_ACTION", "HOLD", "RELEASE"]:
        fail("action authority changed")
    if manifest.get("authoritative_commit") != "205bee21b279fa63aef510fb23854eab17d44eb7":
        fail("authoritative commit mismatch")

    components = manifest.get("components")
    if not isinstance(components, list) or len(components) != 7:
        fail("expected exactly seven named boundary candidates")

    seen: set[str] = set()
    for component in components:
        component_id = component.get("component_id")
        if not isinstance(component_id, str) or component_id in seen:
            fail("invalid or duplicate component identifier")
        seen.add(component_id)
        if component.get("disposition") != "candidate_only":
            fail(f"component is not candidate-only: {component_id}")
        source_path = component.get("source_path")
        if not isinstance(source_path, str) or not source_path.startswith(
            "frozen/bolt_on_continuity_v0_1/"
        ):
            fail(f"unsafe frozen source path: {component_id}")
        expected = component.get("expected_sha256")
        if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
            fail(f"invalid expected SHA-256: {component_id}")
        actual_path = repo_root / source_path
        if not actual_path.is_file():
            fail(f"declared frozen source missing: {source_path}")
        actual = sha256_file(actual_path)
        if actual != expected:
            fail(f"frozen source digest mismatch: {component_id}")

    package_root = product_root / "src" / "bolt_on_continuity_v0_2"
    forbidden_patterns = {
        r"(^|\n)\s*(from|import)\s+bolt_on_continuity(\s|\.|$)": "v0.1 operational import",
        r"(^|\n)\s*(from|import)\s+docker(\s|\.|$)": "Docker SDK import",
        r"(^|\n)\s*(from|import)\s+subprocess(\s|$)": "subprocess import",
        r"os\.system\s*\(": "os.system execution",
        r"subprocess\.(run|Popen|call|check_call|check_output)\s*\(": "subprocess execution",
        r"/var/run/docker\.sock": "Docker socket access",
    }
    for path in sorted(product_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for pattern, label in forbidden_patterns.items():
            if re.search(pattern, text):
                fail(f"{label} found in {path.relative_to(repo_root)}")

    loader_path = package_root / "engine_boundary.py"
    spec = importlib.util.spec_from_file_location("stage1_engine_boundary", loader_path)
    if spec is None or spec.loader is None:
        fail("unable to load boundary validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        validated = module.load_boundary(manifest_path)
    except Exception as exc:
        fail(f"boundary validation failed: {exc}")
    if len(validated["components"]) != 7:
        fail("validated boundary component count mismatch")

    print(FINAL_PASS)


if __name__ == "__main__":
    main()

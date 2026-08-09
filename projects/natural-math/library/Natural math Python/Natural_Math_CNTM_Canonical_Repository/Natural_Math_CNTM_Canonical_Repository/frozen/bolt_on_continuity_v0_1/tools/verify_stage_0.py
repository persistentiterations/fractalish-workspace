from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CONTRACT = "BONACQUI_BOLT_ON_CONTINUITY_DOCKER_PRODUCT_CONTRACT_0_1_STAGE_0"
FROZEN_COMMIT = "0d6de321ccac75bf8d634663396a0a4279b72261"

def canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)

def main() -> int:
    required_docs = [
        "README.md",
        "PRODUCT_CONTRACT.md",
        "SUPPORTED_ENVIRONMENT.md",
        "AUTHORITY_BOUNDARY.md",
        "CLAIM_BOUNDARY.md",
        "STAGE_0_GATES.md",
    ]
    for name in required_docs:
        if not (BASE / name).is_file():
            fail(f"missing {name}")

    schema_dir = BASE / "config" / "schemas"
    schema_paths = sorted(schema_dir.glob("*.json"))
    if len(schema_paths) != 4:
        fail(f"expected 4 schemas, found {len(schema_paths)}")

    schemas = [json.loads(path.read_text(encoding="utf-8")) for path in schema_paths]
    schema_ids = [schema.get("$id") for schema in schemas]
    if None in schema_ids or len(schema_ids) != len(set(schema_ids)):
        fail("schema identifiers are missing or duplicated")

    by_title = {schema["title"]: schema for schema in schemas}
    request = by_title["Bounded Action Request"]

    if request["properties"]["requested_action"]["enum"] != ["HOLD", "RELEASE"]:
        fail("portable action enumeration is not exact")
    if request.get("additionalProperties") is not False:
        fail("action request does not fail closed on additional properties")

    forbidden_request_fields = {
        "command",
        "shell",
        "args",
        "docker_socket",
        "executable",
        "target_pattern",
    }
    if forbidden_request_fields.intersection(request["properties"]):
        fail("action request exposes a forbidden execution field")

    config = json.loads(
        (BASE / "config" / "product.example.json").read_text(encoding="utf-8")
    )
    if config["product_contract"] != CONTRACT:
        fail("configuration contract mismatch")
    if config["actions"]["projection_enabled"] is not False:
        fail("action projection must default to disabled")
    if config["actions"]["allowed_actions"] != ["HOLD", "RELEASE"]:
        fail("configuration action allowlist mismatch")

    readme = (BASE / "README.md").read_text(encoding="utf-8")
    if FROZEN_COMMIT not in readme:
        fail("frozen v0.4 commit is not bound in README")

    # Stage 0 originally contained no operational source. Later qualified stages
    # may add source beneath src/, so Stage 0 re-verification must preserve the
    # contract without incorrectly rejecting legitimate later-stage code.
    forbidden_top_level_dirs = {"gateway", "installer", "service"}
    existing_dirs = {path.name for path in BASE.iterdir() if path.is_dir()}
    found = sorted(forbidden_top_level_dirs.intersection(existing_dirs))
    if found:
        fail(f"forbidden top-level operational directories present: {found}")

    stage_1_present = (BASE / "README_STAGE_1.md").is_file()
    if not stage_1_present and (BASE / "src").exists():
        fail("src directory present before a later-stage advancement record")

    digest_map = {
        str(path.relative_to(BASE)).replace("\\", "/"):
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(BASE.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    stage_digest = canonical_digest(digest_map)

    print("Stage: BOLT-ON CONTINUITY FOR DOCKER PRODUCT CONTRACT 0.1.0")
    print("Mode: CONTRACT_AND_SCHEMA_VERIFICATION")
    print("Frozen foundation commit:", FROZEN_COMMIT)
    print("Portable actions: HOLD, RELEASE")
    print("Schemas:", len(schema_paths))
    print("Required documents:", len(required_docs))
    print("Action projection default: DISABLED")
    print("Additional properties in action request: REJECTED")
    print("Forbidden execution fields: ABSENT")
    print("Later-stage source compatibility:", "ENABLED" if stage_1_present else "NOT PRESENT")
    print("Stage 0 package digest:", stage_digest)
    print("STAGE 0 PRODUCT CONTRACT VERIFICATION: PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())

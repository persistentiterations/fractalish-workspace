#!/usr/bin/env python3
"""Create the immutable Bolt-On Demonstrator v0.4 frozen release from the qualified RC commit."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence

RC_COMMIT = "b7992579104f9c9db9acd9d0fa78b622d9542037"
RELEASE = "v0.4"
EXPECTED_ENTRIES = 25
STAGE6_MARKER = "STAGE 6 EXTERNAL PILOT QUALIFICATION AND RELEASE CANDIDATE: PASS"

THIS_FILE = Path(__file__).resolve()
REPO = THIS_FILE.parent.parent
DEVELOPMENT_ROOT = REPO / "development" / "bolt_on_demonstrator_v0_4"
FROZEN_ROOT = REPO / "frozen" / "bolt_on" / RELEASE
VERIFY_V04 = REPO / "tools" / "verify_bolt_on_v0_4.py"
VERIFY_ALL = REPO / "tools" / "verify_all_frozen.py"

PAYLOAD_PATHS = (
    "README.md",
    "README_STAGE_1.md",
    "README_STAGE_2.md",
    "README_STAGE_3.md",
    "README_STAGE_4.md",
    "README_STAGE_5.md",
    "README_STAGE_6.md",
    "hosts/ordinary_job_service.py",
    "adapters/read_only_job_observer.py",
    "adapters/bounded_action_projector.py",
    "gateways/host_owned_command_gateway.py",
    "lifecycle/live_sidecar_lifecycle.py",
    "release_candidate/release_candidate_manifest.py",
    "integration/external_host_contract.py",
    "integration/independent_host_baseline.py",
    "integration/read_only_observation_adapter.py",
    "integration/host_owned_bounded_command_gateway.py",
    "integration/live_sidecar_failure_recovery.py",
    "integration/external_pilot_qualification.py",
    "tests/test_external_host_contract.py",
    "tests/test_independent_host_baseline.py",
    "tests/test_read_only_observation_adapter.py",
    "tests/test_host_owned_bounded_command_gateway.py",
    "tests/test_live_sidecar_failure_recovery.py",
    "tests/test_external_pilot_qualification.py",
)

LEGACY_VERIFY_ALL = '''#!/usr/bin/env python3
"""Temporary predecessor-only aggregate verifier used while creating v0.4."""

from pathlib import Path
import subprocess
import sys

def main() -> int:
    tools = Path(__file__).resolve().parent
    checks = (
        tools / "verify_frozen.py",
        tools / "verify_bolt_on_v0_1.py",
        tools / "verify_bolt_on_v0_2.py",
        tools / "verify_bolt_on_v0_3.py",
    )
    for check in checks:
        if not check.is_file():
            print(f"MISSING VERIFIER: {check}")
            return 1
        if subprocess.run([sys.executable, str(check)], check=False).returncode != 0:
            return 1
    print()
    print("ALL FROZEN RELEASE VERIFICATIONS PASSED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''


def run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def require(command: Sequence[str], marker: str | None = None) -> str:
    completed = run(command)
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0 or (marker is not None and marker not in output):
        print(output, end="")
        raise RuntimeError(f"command failed: {' '.join(command)}")
    return output


def git_bytes(commit: str, relative_path: str) -> bytes:
    object_path = f"development/bolt_on_demonstrator_v0_4/{relative_path}"
    completed = subprocess.run(
        ["git", "show", f"{commit}:{object_path}"],
        cwd=REPO,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"cannot read committed candidate file {object_path}: "
            + completed.stderr.decode("utf-8", errors="replace")
        )
    return completed.stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def run_candidate_qualification() -> None:
    original = VERIFY_ALL.read_bytes()
    try:
        VERIFY_ALL.write_text(LEGACY_VERIFY_ALL, encoding="utf-8", newline="\n")
        require(
            (
                sys.executable,
                "development/bolt_on_demonstrator_v0_4/integration/external_pilot_qualification.py",
            ),
            STAGE6_MARKER,
        )
        suite = require(
            (
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "development/bolt_on_demonstrator_v0_4/tests",
                "-p",
                "test_*.py",
                "-v",
            )
        )
        if "Ran 560 tests" not in suite or "\nOK" not in suite:
            raise RuntimeError("complete v0.4 suite did not report 560 tests and OK")
    finally:
        VERIFY_ALL.write_bytes(original)


def main() -> int:
    if len(PAYLOAD_PATHS) != EXPECTED_ENTRIES or len(set(PAYLOAD_PATHS)) != EXPECTED_ENTRIES:
        raise RuntimeError("payload path contract is invalid")

    head = require(("git", "rev-parse", "HEAD")).strip()
    if head != RC_COMMIT:
        raise RuntimeError(f"HEAD must be qualified RC commit {RC_COMMIT}; found {head}")

    for verifier in (
        "tools/verify_frozen.py",
        "tools/verify_bolt_on_v0_1.py",
        "tools/verify_bolt_on_v0_2.py",
        "tools/verify_bolt_on_v0_3.py",
    ):
        require((sys.executable, verifier))

    run_candidate_qualification()

    if FROZEN_ROOT.exists():
        raise RuntimeError(f"{FROZEN_ROOT} already exists; frozen releases are never overwritten")

    staged_root = FROZEN_ROOT.with_name(RELEASE + ".staging")
    if staged_root.exists():
        shutil.rmtree(staged_root)
    staged_root.mkdir(parents=True)

    manifest_rows: list[tuple[str, str]] = []
    try:
        for relative_path in PAYLOAD_PATHS:
            committed = git_bytes(RC_COMMIT, relative_path)
            working = DEVELOPMENT_ROOT / relative_path
            if not working.is_file():
                raise RuntimeError(f"working candidate file missing: {working}")
            if working.read_bytes() != committed:
                raise RuntimeError(f"working candidate differs from RC commit: {relative_path}")
            destination = staged_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(committed)
            manifest_rows.append((relative_path, sha256(committed)))

        manifest_rows.sort(key=lambda row: row[0])
        manifest_text = "".join(f"{digest}  {path}\n" for path, digest in manifest_rows)
        manifest_bytes = manifest_text.encode("utf-8")
        release_manifest_digest = sha256(manifest_bytes)

        (staged_root / "FILE_MANIFEST_SHA256.txt").write_bytes(manifest_bytes)
        (staged_root / "RELEASE_MANIFEST_SHA256.txt").write_text(
            release_manifest_digest + "\n", encoding="ascii", newline="\n"
        )
        metadata = {
            "entry_count": EXPECTED_ENTRIES,
            "freeze_commit_pending": True,
            "release": RELEASE,
            "release_manifest_sha256": release_manifest_digest,
            "source_commit": RC_COMMIT,
            "source_root": "development/bolt_on_demonstrator_v0_4",
            "status": "FROZEN",
        }
        (staged_root / "RELEASE_METADATA.json").write_bytes(canonical_json(metadata) + b"\n")
        staged_root.rename(FROZEN_ROOT)
    except Exception:
        if staged_root.exists():
            shutil.rmtree(staged_root)
        raise

    require((sys.executable, str(VERIFY_V04)), "BOLT-ON v0.4 FROZEN VERIFICATION PASSED: 25 files")
    require((sys.executable, str(VERIFY_ALL)), "ALL FROZEN RELEASE VERIFICATIONS PASSED")

    print(f"Source commit: {RC_COMMIT}")
    print(f"Frozen payload files: {EXPECTED_ENTRIES}")
    print(f"Frozen release manifest: {(FROZEN_ROOT / 'RELEASE_MANIFEST_SHA256.txt').read_text().strip()}")
    print("v0.4 development suite: 560 tests PASS")
    print("BOLT-ON v0.4 FINAL FREEZE: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"BOLT-ON v0.4 FINAL FREEZE: FAIL — {exc}")
        raise SystemExit(1)

#!/usr/bin/env python3
"""Final freeze procedure for Bolt-On Demonstrator v0.3.

This program consumes the approved v0.3-RC1 record, requalifies the complete
v0.3 development tree, copies that tree byte-for-byte into
``frozen/bolt_on/v0.3``, seals a release manifest and freeze receipt, installs a
standalone verifier, and extends the aggregate frozen-release verifier.

The procedure is transactional: if any post-copy gate fails, the new frozen
release and verifier are removed and the aggregate verifier is restored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Iterable, Sequence

sys.dont_write_bytecode = True

RELEASE = "v0.3"
RC_VERSION = "v0.3-RC1"
EXPECTED_FREEZE_SOURCE_COMMIT = "df41b99f880b5170bc8e8517d04f181dd109fe26"
EXPECTED_RC_SOURCE_COMMIT = "0e92ecaca48c4c5bf85bab658a4e693aae3d36f6"
EXPECTED_RC_RECORD_SHA256 = "179e5f1cae244df123de3e5edf1000ab1ae186be20c6041d24141560b963f2b2"
EXPECTED_DEVELOPMENT_MANIFEST_SHA256 = "aac2512cc908609ef73c8a94ccd86c74a18b22e004c80a722c391de7cabd3ddc"
EXPECTED_PRIOR_FROZEN_TREE_SHA256 = "f6dca84868be5e49e6a2f188a8d4c0ce20bbadc698eec315af9e9c230b92feb4"
EXPECTED_V02_RELEASE_MANIFEST_SHA256 = (
    "e020199f5327866bfcbe34877466ea06558eb6650c578ce841c37b4c9abd159c"
)
EXPECTED_TEST_COUNT = 256
EXPECTED_HOST_FAMILIES = 2
EXPECTED_SUBSTITUTIONS = 1
EXPECTED_BASELINE_HOST_ACTIONS = 2
EXPECTED_ATTACKS = 48
EXPECTED_FROZEN_MANIFEST_ENTRIES = 20

DEV = Path("development/bolt_on_demonstrator_v0_3")
RC_RECORD = DEV / "RC1_QUALIFICATION.json"
TARGET = Path("frozen/bolt_on/v0.3")
VERIFY = Path("tools/verify_bolt_on_v0_3.py")
VERIFY_ALL = Path("tools/verify_all_frozen.py")
FROZEN_ROOT = Path("frozen")
V02_MANIFEST = Path("frozen/bolt_on/v0.2/RELEASE_MANIFEST_SHA256.txt")

STAGES = (
    (
        "stage_1_portable_adapter_contract",
        Path("portability/portable_adapter_contract.py"),
        "STAGE 1 PORTABLE ADAPTER CONTRACT QUALIFICATION: PASS",
    ),
    (
        "workflow_host_self_qualification",
        Path("hosts/workflow_state_host.py"),
        "SECOND INDEPENDENT HOST SELF-QUALIFICATION: PASS",
    ),
    (
        "stage_2_second_independent_host",
        Path("portability/second_independent_host.py"),
        "STAGE 2 SECOND INDEPENDENT HOST QUALIFICATION: PASS",
    ),
    (
        "stage_3_cross_host_replay",
        Path("portability/cross_host_replay.py"),
        "STAGE 3 EQUIVALENT-EVENT CROSS-HOST REPLAY: PASS",
    ),
    (
        "queue_host_self_qualification",
        Path("hosts/queue_state_host.py"),
        "LEASE QUEUE HOST SELF-QUALIFICATION: PASS",
    ),
    (
        "stage_4_live_host_substitution",
        Path("portability/live_host_substitution.py"),
        "STAGE 4 LIVE HOST SUBSTITUTION QUALIFICATION: PASS",
    ),
    (
        "stage_5_adversarial_adapter_qualification",
        Path("portability/adversarial_adapter_qualification.py"),
        "STAGE 5 ADVERSARIAL ADAPTER QUALIFICATION: PASS",
    ),
)


class FreezeError(RuntimeError):
    """Raised when a release gate fails."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_digest(value: object) -> str:
    return sha256_bytes(canonical_json(value).encode("ascii"))


def is_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def iter_files(
    root: Path,
    *,
    exclude_rc_record: bool = False,
    exclude_release_manifest: bool = False,
    exclude_subtree: Path | None = None,
) -> Iterable[Path]:
    if not root.is_dir():
        raise FreezeError(f"missing directory: {root}")
    excluded_resolved = exclude_subtree.resolve() if exclude_subtree is not None else None
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if exclude_rc_record and path.name == "RC1_QUALIFICATION.json" and path.parent == root:
            continue
        if exclude_release_manifest and path.name == "RELEASE_MANIFEST_SHA256.txt" and path.parent == root:
            continue
        if excluded_resolved is not None:
            try:
                path.resolve().relative_to(excluded_resolved)
            except ValueError:
                pass
            else:
                continue
        yield path


def tree_manifest_digest(
    root: Path,
    *,
    exclude_rc_record: bool = False,
    exclude_subtree: Path | None = None,
) -> str:
    rows = [
        f"{sha256_file(path)}  {path.relative_to(root).as_posix()}"
        for path in iter_files(
            root,
            exclude_rc_record=exclude_rc_record,
            exclude_subtree=exclude_subtree,
        )
    ]
    if not rows:
        raise FreezeError(f"manifest tree contains no files: {root}")
    return sha256_bytes(("\n".join(rows) + "\n").encode("utf-8"))


def git_head(repository_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        raise FreezeError("could not resolve Git HEAD")
    return completed.stdout.strip()


def normalise_console(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"Ran (\d+) tests? in [0-9.]+s", r"Ran \1 tests in <TIME>s", text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip() + "\n"


def read_key_values(output: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for line in output.replace("\r", "").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key:
            values.setdefault(key, []).append(value.strip())
    return values


def single(values: dict[str, list[str]], key: str) -> str:
    rows = values.get(key, [])
    if len(rows) != 1:
        raise FreezeError(f"expected one output field {key!r}; observed {len(rows)}")
    return rows[0]


def validate_stage_output(name: str, output: str) -> None:
    values = read_key_values(output)
    if name in {
        "stage_1_portable_adapter_contract",
        "stage_2_second_independent_host",
        "stage_3_cross_host_replay",
    }:
        if single(values, "Executed actions") != "0":
            raise FreezeError(f"{name} reported nonzero execution")
    elif name == "workflow_host_self_qualification":
        if single(values, "Applied") != "4" or single(values, "Rejected") != "0":
            raise FreezeError("workflow host canonical counts changed")
        if single(values, "Final state") != "DONE":
            raise FreezeError("workflow host canonical final state changed")
    elif name == "queue_host_self_qualification":
        if single(values, "Applied") != "4" or single(values, "Rejected") != "0":
            raise FreezeError("queue host canonical counts changed")
        if single(values, "Final phase") != "COMPLETE":
            raise FreezeError("queue host canonical final phase changed")
    elif name == "stage_4_live_host_substitution":
        if single(values, "Executed host actions") != "2":
            raise FreezeError("Stage 4 host action count changed")
        if single(values, "Bolt-on executed actions") != "0":
            raise FreezeError("Stage 4 bolt-on execution is nonzero")
        if single(values, "Campaign digest") != single(values, "Replay digest"):
            raise FreezeError("Stage 4 campaign and replay digests differ")
    elif name == "stage_5_adversarial_adapter_qualification":
        expected = {
            "Attack categories": "4",
            "Attacks executed": "48",
            "Attacks safely rejected": "48",
            "Baseline host actions": "2",
            "Host actions during attacks": "0",
            "Bolt-on executed actions": "0",
        }
        for key, expected_value in expected.items():
            if single(values, key) != expected_value:
                raise FreezeError(f"Stage 5 field changed: {key}")
        if single(values, "Adversarial campaign digest") != single(values, "Replay digest"):
            raise FreezeError("Stage 5 campaign and replay digests differ")


def run_command(command: Sequence[str], repository_root: Path, marker: str, name: str) -> dict[str, object]:
    completed = subprocess.run(
        list(command),
        cwd=repository_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    combined = completed.stdout + "\n" + completed.stderr
    if completed.returncode or marker not in combined:
        raise FreezeError(
            f"command failed: {name}; marker={marker!r}; returncode={completed.returncode}\n{combined}"
        )
    if name in {stage_name for stage_name, _, _ in STAGES}:
        validate_stage_output(name, combined)
    return {
        "command": ["python", *[str(item) for item in command[1:]]],
        "marker": marker,
        "name": name,
        "normalized_output_sha256": sha256_bytes(normalise_console(combined).encode("utf-8")),
        "stderr_sha256": sha256_bytes(normalise_console(completed.stderr).encode("utf-8")),
        "stdout_sha256": sha256_bytes(normalise_console(completed.stdout).encode("utf-8")),
    }


def run_complete_tests(repository_root: Path) -> dict[str, object]:
    command = (
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(repository_root / DEV / "tests"),
        "-p",
        "test_*.py",
        "-v",
    )
    completed = subprocess.run(
        list(command),
        cwd=repository_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    combined = completed.stdout + "\n" + completed.stderr
    matches = re.findall(r"Ran\s+(\d+)\s+tests?", combined)
    if (
        completed.returncode
        or not matches
        or int(matches[-1]) != EXPECTED_TEST_COUNT
        or not re.search(r"(?:^|\n)OK(?:\n|$)", combined)
    ):
        raise FreezeError(f"complete v0.3 suite failed or count != {EXPECTED_TEST_COUNT}\n{combined}")
    return {
        "command": [
            "python",
            "-m",
            "unittest",
            "discover",
            "-s",
            DEV.as_posix() + "/tests",
            "-p",
            "test_*.py",
            "-v",
        ],
        "count": EXPECTED_TEST_COUNT,
        "marker": "OK",
        "name": "complete_v0_3_tests",
        "normalized_output_sha256": sha256_bytes(normalise_console(combined).encode("utf-8")),
        "stderr_sha256": sha256_bytes(normalise_console(completed.stderr).encode("utf-8")),
        "stdout_sha256": sha256_bytes(normalise_console(completed.stdout).encode("utf-8")),
    }


def load_and_validate_rc(repository_root: Path) -> tuple[dict[str, object], str]:
    path = repository_root / RC_RECORD
    if not path.is_file():
        raise FreezeError("RC1 qualification record is missing")
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FreezeError(f"RC1 qualification record is unreadable: {error}") from error
    if not isinstance(envelope, dict) or set(envelope) != {"record", "record_sha256"}:
        raise FreezeError("RC1 qualification envelope is malformed")
    record = envelope["record"]
    record_digest = envelope["record_sha256"]
    if not isinstance(record, dict) or not is_digest(record_digest):
        raise FreezeError("RC1 qualification record fields are malformed")
    if canonical_digest(record) != record_digest:
        raise FreezeError("RC1 qualification record digest mismatch")
    if record_digest != EXPECTED_RC_RECORD_SHA256:
        raise FreezeError("RC1 qualification record is not the approved canonical record")

    expected = {
        "approved_for_freeze_procedure": True,
        "bolt_on_executed_actions": 0,
        "deterministic_second_pass": True,
        "development_manifest_sha256": EXPECTED_DEVELOPMENT_MANIFEST_SHA256,
        "expected_test_count": EXPECTED_TEST_COUNT,
        "frozen_manifest_sha256": EXPECTED_PRIOR_FROZEN_TREE_SHA256,
        "frozen_v02_release_manifest_sha256": EXPECTED_V02_RELEASE_MANIFEST_SHA256,
        "host_actions_during_attacks": 0,
        "host_families_qualified": EXPECTED_HOST_FAMILIES,
        "observed_test_count": EXPECTED_TEST_COUNT,
        "portable_actions": ["HOLD", "RELEASE"],
        "prohibited_action_hits": [],
        "qualified_attack_count": EXPECTED_ATTACKS,
        "qualified_attack_rejections": EXPECTED_ATTACKS,
        "qualified_baseline_host_actions": EXPECTED_BASELINE_HOST_ACTIONS,
        "qualified_substitutions": EXPECTED_SUBSTITUTIONS,
        "rc_version": RC_VERSION,
        "source_commit": EXPECTED_RC_SOURCE_COMMIT,
    }
    for key, expected_value in expected.items():
        if record.get(key) != expected_value:
            raise FreezeError(f"RC1 requirement failed: {key}")
    return record, record_digest


def release_verifier_source() -> str:
    return '''#!/usr/bin/env python3
"""Verify the frozen Bolt-On Demonstrator v0.3 release."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json

EXPECTED_RC_RECORD_SHA256 = "179e5f1cae244df123de3e5edf1000ab1ae186be20c6041d24141560b963f2b2"
EXPECTED_DEVELOPMENT_MANIFEST_SHA256 = "aac2512cc908609ef73c8a94ccd86c74a18b22e004c80a722c391de7cabd3ddc"
EXPECTED_ENTRIES = 20

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def canonical_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()

def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    root = repository_root / "frozen" / "bolt_on" / "v0.3"
    manifest = root / "RELEASE_MANIFEST_SHA256.txt"
    if not root.is_dir() or not manifest.is_file():
        print("MISSING v0.3 frozen release")
        return 1
    expected: dict[str, str] = {}
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if (
            len(parts) != 2
            or len(parts[0]) != 64
            or any(character not in "0123456789abcdef" for character in parts[0])
            or not parts[1]
            or parts[1] in expected
        ):
            print(f"INVALID MANIFEST LINE {line_number}: {line}")
            return 1
        expected[parts[1]] = parts[0]
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path != manifest
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }
    failed = False
    for relative in sorted(set(expected) - actual):
        print("MISSING ", relative)
        failed = True
    for relative in sorted(actual - set(expected)):
        print("EXTRA   ", relative)
        failed = True
    for relative in sorted(set(expected) & actual):
        if sha256_file(root / relative) != expected[relative]:
            print("CHANGED ", relative)
            failed = True
    if len(expected) != EXPECTED_ENTRIES:
        print(f"ENTRY COUNT MISMATCH: expected {EXPECTED_ENTRIES}, observed {len(expected)}")
        failed = True
    receipt_path = root / "FREEZE_RECEIPT.json"
    try:
        envelope = json.loads(receipt_path.read_text(encoding="utf-8"))
        record = envelope["record"]
        record_digest = envelope["record_sha256"]
    except Exception as error:
        print(f"INVALID FREEZE RECEIPT: {error}")
        return 1
    if canonical_digest(record) != record_digest:
        print("FREEZE RECEIPT DIGEST MISMATCH")
        failed = True
    if record.get("release") != "v0.3" or record.get("status") != "FROZEN":
        print("FREEZE RECEIPT RELEASE STATUS MISMATCH")
        failed = True
    if record.get("rc_record_sha256") != EXPECTED_RC_RECORD_SHA256:
        print("FREEZE RECEIPT RC BINDING MISMATCH")
        failed = True
    if record.get("development_manifest_sha256") != EXPECTED_DEVELOPMENT_MANIFEST_SHA256:
        print("FREEZE RECEIPT DEVELOPMENT BINDING MISMATCH")
        failed = True
    if failed:
        print("BOLT-ON v0.3 FROZEN VERIFICATION FAILED")
        return 1
    print(f"BOLT-ON v0.3 FROZEN VERIFICATION PASSED: {len(expected)} files")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''


def build_release_manifest(target: Path) -> tuple[str, int]:
    rows = [
        f"{sha256_file(path)}  {path.relative_to(target).as_posix()}"
        for path in iter_files(target, exclude_release_manifest=True)
    ]
    if len(rows) != EXPECTED_FROZEN_MANIFEST_ENTRIES:
        raise FreezeError(
            f"frozen manifest entry count mismatch: expected {EXPECTED_FROZEN_MANIFEST_ENTRIES}, observed {len(rows)}"
        )
    manifest = target / "RELEASE_MANIFEST_SHA256.txt"
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return sha256_file(manifest), len(rows)


def exact_copy_matches(source: Path, target: Path) -> bool:
    source_rows = {
        path.relative_to(source).as_posix(): sha256_file(path)
        for path in iter_files(source)
    }
    target_rows = {
        path.relative_to(target).as_posix(): sha256_file(path)
        for path in iter_files(target)
        if path.name not in {"FREEZE_RECEIPT.json", "RELEASE_MANIFEST_SHA256.txt"}
    }
    return source_rows == target_rows


def extend_aggregate_verifier(content: str) -> str:
    anchor = '        tools / "verify_bolt_on_v0_2.py",'
    entry = '        tools / "verify_bolt_on_v0_3.py",'
    if entry in content:
        raise FreezeError("aggregate verifier already includes v0.3")
    if content.count(anchor) != 1:
        raise FreezeError("cannot safely extend aggregate verifier")
    return content.replace(anchor, anchor + "\n" + entry, 1)


def qualify_development(repository_root: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for name, relative, marker in STAGES:
        results.append(
            run_command(
                (sys.executable, str(repository_root / DEV / relative)),
                repository_root,
                marker,
                name,
            )
        )
    results.append(run_complete_tests(repository_root))
    return results


def freeze(repository_root: Path) -> tuple[dict[str, object], str, int]:
    repository_root = repository_root.resolve()
    development = repository_root / DEV
    target = repository_root / TARGET
    verifier = repository_root / VERIFY
    aggregate = repository_root / VERIFY_ALL
    frozen_root = repository_root / FROZEN_ROOT
    v02_manifest = repository_root / V02_MANIFEST

    if target.exists() or verifier.exists():
        raise FreezeError("v0.3 freeze target or verifier already exists")
    if not aggregate.is_file():
        raise FreezeError("aggregate frozen verifier is missing")
    if git_head(repository_root) != EXPECTED_FREEZE_SOURCE_COMMIT:
        raise FreezeError("Git HEAD is not the approved v0.3 RC1 commit")

    record, record_digest = load_and_validate_rc(repository_root)
    development_manifest = tree_manifest_digest(development, exclude_rc_record=True)
    if development_manifest != EXPECTED_DEVELOPMENT_MANIFEST_SHA256:
        raise FreezeError("development tree differs from approved RC1 manifest")
    if development_manifest != record["development_manifest_sha256"]:
        raise FreezeError("development tree does not match RC1 record")

    prior_frozen_manifest = tree_manifest_digest(frozen_root)
    if prior_frozen_manifest != EXPECTED_PRIOR_FROZEN_TREE_SHA256:
        raise FreezeError("prior frozen tree differs from approved RC1 manifest")
    if prior_frozen_manifest != record["frozen_manifest_sha256"]:
        raise FreezeError("prior frozen tree does not match RC1 record")
    if not v02_manifest.is_file() or sha256_file(v02_manifest) != EXPECTED_V02_RELEASE_MANIFEST_SHA256:
        raise FreezeError("frozen v0.2 release manifest mismatch")

    development_full_before = tree_manifest_digest(development)
    aggregate_original = aggregate.read_text(encoding="utf-8")

    run_command(
        (sys.executable, str(aggregate)),
        repository_root,
        "ALL FROZEN RELEASE VERIFICATIONS PASSED",
        "all_frozen_verification_pre_freeze",
    )
    qualification = qualify_development(repository_root)

    if tree_manifest_digest(development) != development_full_before:
        raise FreezeError("development tree changed during final qualification")
    if tree_manifest_digest(frozen_root) != prior_frozen_manifest:
        raise FreezeError("prior frozen tree changed during final qualification")

    try:
        target.mkdir(parents=True)
        for source in iter_files(development):
            destination = target / source.relative_to(development)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        if not exact_copy_matches(development, target):
            raise FreezeError("frozen source copy differs from development source")

        receipt_record: dict[str, object] = {
            "attack_host_actions": 0,
            "attacks_qualified": EXPECTED_ATTACKS,
            "attacks_rejected": EXPECTED_ATTACKS,
            "baseline_host_actions": EXPECTED_BASELINE_HOST_ACTIONS,
            "bolt_on_executed_actions": 0,
            "development_manifest_sha256": development_manifest,
            "freeze_source_commit": EXPECTED_FREEZE_SOURCE_COMMIT,
            "host_families_qualified": EXPECTED_HOST_FAMILIES,
            "observed_tests": EXPECTED_TEST_COUNT,
            "portable_actions": ["HOLD", "RELEASE"],
            "prior_frozen_tree_sha256": prior_frozen_manifest,
            "qualification": qualification,
            "rc_record_sha256": record_digest,
            "rc_source_commit": record["source_commit"],
            "release": RELEASE,
            "status": "FROZEN",
            "substitutions_qualified": EXPECTED_SUBSTITUTIONS,
        }
        receipt_envelope = {
            "record": receipt_record,
            "record_sha256": canonical_digest(receipt_record),
        }
        (target / "FREEZE_RECEIPT.json").write_text(
            json.dumps(receipt_envelope, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        release_manifest, entry_count = build_release_manifest(target)
        verifier.write_text(release_verifier_source(), encoding="utf-8", newline="\n")
        aggregate.write_text(
            extend_aggregate_verifier(aggregate_original),
            encoding="utf-8",
            newline="\n",
        )

        run_command(
            (sys.executable, str(verifier)),
            repository_root,
            "BOLT-ON v0.3 FROZEN VERIFICATION PASSED",
            "v0_3_frozen_verification",
        )
        run_command(
            (sys.executable, str(aggregate)),
            repository_root,
            "ALL FROZEN RELEASE VERIFICATIONS PASSED",
            "all_frozen_verification_post_freeze",
        )

        if tree_manifest_digest(development) != development_full_before:
            raise FreezeError("development tree changed during freeze")
        unchanged_prior = tree_manifest_digest(
            frozen_root,
            exclude_subtree=target,
        )
        if unchanged_prior != prior_frozen_manifest:
            raise FreezeError("prior frozen releases changed during freeze")
        if not exact_copy_matches(development, target):
            raise FreezeError("frozen source copy changed after sealing")

        return receipt_record, release_manifest, entry_count
    except Exception:
        if target.exists():
            shutil.rmtree(target)
        if verifier.exists():
            verifier.unlink()
        aggregate.write_text(aggregate_original, encoding="utf-8", newline="\n")
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    try:
        receipt, release_manifest, entry_count = freeze(arguments.repo)
    except Exception as error:
        print(f"V0.3 FINAL FREEZE FAILED: {error}", file=sys.stderr)
        return 1

    print(f"Release: {receipt['release']}")
    print(f"Freeze source commit: {receipt['freeze_source_commit']}")
    print(f"RC source commit: {receipt['rc_source_commit']}")
    print(f"Observed tests: {receipt['observed_tests']}")
    print(f"Host families qualified: {receipt['host_families_qualified']}")
    print(f"Substitutions qualified: {receipt['substitutions_qualified']}")
    print(f"Attacks rejected: {receipt['attacks_rejected']}")
    print(f"Baseline host actions: {receipt['baseline_host_actions']}")
    print(f"Attack host actions: {receipt['attack_host_actions']}")
    print(f"Bolt-on executed actions: {receipt['bolt_on_executed_actions']}")
    print(f"Development manifest: {receipt['development_manifest_sha256']}")
    print(f"RC qualification record: {receipt['rc_record_sha256']}")
    print(f"Frozen manifest entries: {entry_count}")
    print(f"Release manifest: {release_manifest}")
    print("Prior frozen releases unchanged: True")
    print("Development tree unchanged: True")
    print("ALL FROZEN RELEASE VERIFICATIONS PASSED")
    print("BOLT-ON DEMONSTRATOR v0.3 FINAL FREEZE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

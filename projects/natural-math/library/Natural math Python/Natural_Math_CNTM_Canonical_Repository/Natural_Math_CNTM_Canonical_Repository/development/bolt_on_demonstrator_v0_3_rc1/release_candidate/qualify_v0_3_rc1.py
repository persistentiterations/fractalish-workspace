#!/usr/bin/env python3
"""Bolt-On Demonstrator v0.3 RC1 portability qualification.

This procedure qualifies the completed v0.3 development tree without freezing
it. It runs every Stage 1-5 executable, both independent host self-checks, the
complete exact-count test suite, and the aggregate frozen-release verifier twice.
It then compares normalized evidence, verifies the development and frozen trees
were unchanged, checks that adapters retain no execution surface, and writes one
canonical RC1 approval record into the v0.3 development directory.

The final freeze remains a separate package and commit.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable, Iterable, Sequence, Tuple

sys.dont_write_bytecode = True

RC_VERSION = "v0.3-RC1"
EXPECTED_SOURCE_COMMIT = "0e92ecaca48c4c5bf85bab658a4e693aae3d36f6"
EXPECTED_TEST_COUNT = 256
EXPECTED_V02_RELEASE_MANIFEST_SHA256 = (
    "e020199f5327866bfcbe34877466ea06558eb6650c578ce841c37b4c9abd159c"
)
RC_MARKER = "BOLT-ON DEMONSTRATOR v0.3 RC1 QUALIFICATION: PASS"
ZERO_DIGEST = "0" * 64

THIS_FILE = Path(__file__).resolve()
PACKAGE_ROOT = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
DEVELOPMENT_ROOT = REPOSITORY_ROOT / "development" / "bolt_on_demonstrator_v0_3"
RC_RECORD_PATH = DEVELOPMENT_ROOT / "RC1_QUALIFICATION.json"
FROZEN_ROOT = REPOSITORY_ROOT / "frozen"
FROZEN_V02_MANIFEST = FROZEN_ROOT / "bolt_on" / "v0.2" / "RELEASE_MANIFEST_SHA256.txt"
VERIFY_ALL_FROZEN = REPOSITORY_ROOT / "tools" / "verify_all_frozen.py"
TEST_ROOT = DEVELOPMENT_ROOT / "tests"

PROHIBITED_ADAPTER_METHODS = {
    "execute",
    "apply",
    "dispatch",
    "mutate_host",
    "modify_host",
    "write_host",
    "run_host",
}
EXPECTED_PORTABLE_ADAPTER_METHODS = {
    "identity",
    "normalize_event",
    "project_action",
}


@dataclass(frozen=True)
class CommandSpec:
    name: str
    portable_command: Tuple[str, ...]
    command: Tuple[str, ...]
    marker: str
    required_lines: Tuple[str, ...] = ()
    validator: str = "marker"


@dataclass(frozen=True)
class CommandEvidence:
    name: str
    command: Tuple[str, ...]
    marker: str
    stdout_sha256: str
    stderr_sha256: str
    normalized_output_sha256: str
    observed_test_count: int = 0

    def record(self) -> dict[str, object]:
        row: dict[str, object] = {
            "command": list(self.command),
            "marker": self.marker,
            "name": self.name,
            "normalized_output_sha256": self.normalized_output_sha256,
            "stderr_sha256": self.stderr_sha256,
            "stdout_sha256": self.stdout_sha256,
        }
        if self.observed_test_count:
            row["count"] = self.observed_test_count
        return row


class QualificationError(RuntimeError):
    pass


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _canonical_digest(value: object) -> str:
    return _sha256_bytes(_canonical_json(value).encode("ascii"))


def _is_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _normalise_console(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"Ran (\d+) tests? in [0-9.]+s", r"Ran \1 tests in <TIME>s", text)
    text = re.sub(r"^Python executable: .+$", "Python executable: <PYTHON>", text, flags=re.MULTILINE)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip() + "\n"


def _iter_manifest_files(root: Path, *, exclude_rc_record: bool = False) -> Iterable[Path]:
    if not root.is_dir():
        raise QualificationError(f"missing directory: {root}")
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if (
            exclude_rc_record
            and path.name == "RC1_QUALIFICATION.json"
            and path.parent == root
        ):
            continue
        yield path


def _tree_manifest_digest(root: Path, *, exclude_rc_record: bool = False) -> str:
    rows = [
        f"{_sha256_file(path)}  {path.relative_to(root).as_posix()}"
        for path in _iter_manifest_files(root, exclude_rc_record=exclude_rc_record)
    ]
    if not rows:
        raise QualificationError(f"manifest tree contains no files: {root}")
    return _sha256_bytes(("\n".join(rows) + "\n").encode("utf-8"))


def _git_head(repository_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        raise QualificationError("could not resolve Git HEAD")
    return completed.stdout.strip()


def _read_key_values(output: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for line in output.replace("\r", "").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key:
            values.setdefault(key, []).append(value.strip())
    return values


def _single(values: dict[str, list[str]], key: str) -> str:
    rows = values.get(key, [])
    if len(rows) != 1:
        raise QualificationError(f"expected exactly one output field {key!r}, observed {len(rows)}")
    return rows[0]


def _validate_stage_output(spec: CommandSpec, output: str) -> int:
    if spec.marker not in output:
        raise QualificationError(f"{spec.name} missing required marker: {spec.marker}")
    for line in spec.required_lines:
        if line not in output:
            raise QualificationError(f"{spec.name} missing required line: {line}")

    values = _read_key_values(output)
    if spec.validator in {"stage1", "stage2", "stage3"}:
        if _single(values, "Executed actions") != "0":
            raise QualificationError(f"{spec.name} reported nonzero execution")
    elif spec.validator == "stage4":
        if _single(values, "Executed host actions") != "2":
            raise QualificationError("Stage 4 baseline host-action count is not exactly two")
        if _single(values, "Bolt-on executed actions") != "0":
            raise QualificationError("Stage 4 bolt-on execution is nonzero")
        if _single(values, "Campaign digest") != _single(values, "Replay digest"):
            raise QualificationError("Stage 4 campaign and replay digests differ")
    elif spec.validator == "stage5":
        expected = {
            "Attack categories": "4",
            "Attacks executed": "48",
            "Attacks safely rejected": "48",
            "Baseline host actions": "2",
            "Host actions during attacks": "0",
            "Bolt-on executed actions": "0",
        }
        for key, value in expected.items():
            if _single(values, key) != value:
                raise QualificationError(f"Stage 5 field mismatch: {key}")
        if _single(values, "Adversarial campaign digest") != _single(values, "Replay digest"):
            raise QualificationError("Stage 5 campaign and replay digests differ")
    elif spec.validator == "workflow_host":
        if _single(values, "Applied") != "4" or _single(values, "Rejected") != "0":
            raise QualificationError("workflow-host canonical counts changed")
        if _single(values, "Final state") != "DONE":
            raise QualificationError("workflow-host canonical final state changed")
    elif spec.validator == "queue_host":
        if _single(values, "Applied") != "4" or _single(values, "Rejected") != "0":
            raise QualificationError("queue-host canonical counts changed")
        if _single(values, "Final phase") != "COMPLETE":
            raise QualificationError("queue-host canonical final phase changed")
    elif spec.validator == "tests":
        matches = re.findall(r"Ran\s+(\d+)\s+tests?", output)
        if not matches:
            raise QualificationError("complete test output did not report a test count")
        observed = int(matches[-1])
        if observed != EXPECTED_TEST_COUNT:
            raise QualificationError(
                f"complete test count mismatch: expected {EXPECTED_TEST_COUNT}, observed {observed}"
            )
        if not re.search(r"(?:^|\n)OK(?:\n|$)", output):
            raise QualificationError("complete test suite did not report OK")
        return observed
    elif spec.validator == "frozen":
        if "ALL FROZEN RELEASE VERIFICATIONS PASSED" not in output:
            raise QualificationError("aggregate frozen verification did not pass")
    return 0


def _command_specs(repository_root: Path = REPOSITORY_ROOT) -> Tuple[CommandSpec, ...]:
    development = repository_root / "development" / "bolt_on_demonstrator_v0_3"
    tools = repository_root / "tools"
    python = sys.executable

    def py(relative: str) -> Tuple[str, ...]:
        return (python, str(repository_root / relative))

    return (
        CommandSpec(
            "stage_1_portable_adapter_contract",
            ("python", "development/bolt_on_demonstrator_v0_3/portability/portable_adapter_contract.py"),
            py("development/bolt_on_demonstrator_v0_3/portability/portable_adapter_contract.py"),
            "STAGE 1 PORTABLE ADAPTER CONTRACT QUALIFICATION: PASS",
            ("Execution authority: NONE",),
            "stage1",
        ),
        CommandSpec(
            "workflow_host_self_qualification",
            ("python", "development/bolt_on_demonstrator_v0_3/hosts/workflow_state_host.py"),
            py("development/bolt_on_demonstrator_v0_3/hosts/workflow_state_host.py"),
            "SECOND INDEPENDENT HOST SELF-QUALIFICATION: PASS",
            (),
            "workflow_host",
        ),
        CommandSpec(
            "stage_2_second_independent_host",
            ("python", "development/bolt_on_demonstrator_v0_3/portability/second_independent_host.py"),
            py("development/bolt_on_demonstrator_v0_3/portability/second_independent_host.py"),
            "STAGE 2 SECOND INDEPENDENT HOST QUALIFICATION: PASS",
            ("Execution authority: NONE",),
            "stage2",
        ),
        CommandSpec(
            "stage_3_cross_host_replay",
            ("python", "development/bolt_on_demonstrator_v0_3/portability/cross_host_replay.py"),
            py("development/bolt_on_demonstrator_v0_3/portability/cross_host_replay.py"),
            "STAGE 3 EQUIVALENT-EVENT CROSS-HOST REPLAY: PASS",
            ("Execution authority: NONE",),
            "stage3",
        ),
        CommandSpec(
            "queue_host_self_qualification",
            ("python", "development/bolt_on_demonstrator_v0_3/hosts/queue_state_host.py"),
            py("development/bolt_on_demonstrator_v0_3/hosts/queue_state_host.py"),
            "LEASE QUEUE HOST SELF-QUALIFICATION: PASS",
            (),
            "queue_host",
        ),
        CommandSpec(
            "stage_4_live_host_substitution",
            ("python", "development/bolt_on_demonstrator_v0_3/portability/live_host_substitution.py"),
            py("development/bolt_on_demonstrator_v0_3/portability/live_host_substitution.py"),
            "STAGE 4 LIVE HOST SUBSTITUTION QUALIFICATION: PASS",
            ("Bolt-on execution authority: NONE", "Execution boundary: HOST_BOUNDARY_ONLY"),
            "stage4",
        ),
        CommandSpec(
            "stage_5_adversarial_adapter_qualification",
            ("python", "development/bolt_on_demonstrator_v0_3/portability/adversarial_adapter_qualification.py"),
            py("development/bolt_on_demonstrator_v0_3/portability/adversarial_adapter_qualification.py"),
            "STAGE 5 ADVERSARIAL ADAPTER QUALIFICATION: PASS",
            ("Bolt-on execution authority: NONE", "Execution boundary: HOST_BOUNDARY_ONLY"),
            "stage5",
        ),
        CommandSpec(
            "complete_v0_3_tests",
            ("python", "-m", "unittest", "discover", "-s", "development/bolt_on_demonstrator_v0_3/tests", "-p", "test_*.py", "-v"),
            (
                python,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(development / "tests"),
                "-p",
                "test_*.py",
                "-v",
            ),
            "OK",
            (),
            "tests",
        ),
        CommandSpec(
            "all_frozen_verification",
            ("python", "tools/verify_all_frozen.py"),
            (python, str(tools / "verify_all_frozen.py")),
            "ALL FROZEN RELEASE VERIFICATIONS PASSED",
            (),
            "frozen",
        ),
    )


def _run_command(spec: CommandSpec, repository_root: Path) -> CommandEvidence:
    completed = subprocess.run(
        list(spec.command),
        cwd=repository_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    combined = completed.stdout + "\n" + completed.stderr
    if completed.returncode:
        raise QualificationError(
            f"{spec.name} exited with {completed.returncode}\n{combined}"
        )
    observed_test_count = _validate_stage_output(spec, combined)
    normalized_stdout = _normalise_console(completed.stdout)
    normalized_stderr = _normalise_console(completed.stderr)
    normalized_combined = _normalise_console(combined)
    return CommandEvidence(
        name=spec.name,
        command=spec.portable_command,
        marker=spec.marker,
        stdout_sha256=_sha256_bytes(normalized_stdout.encode("utf-8")),
        stderr_sha256=_sha256_bytes(normalized_stderr.encode("utf-8")),
        normalized_output_sha256=_sha256_bytes(normalized_combined.encode("utf-8")),
        observed_test_count=observed_test_count,
    )


def _adapter_authority_scan(development_root: Path) -> Tuple[str, ...]:
    hits: list[str] = []
    portable_contract_methods: set[str] | None = None
    for path in sorted(development_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(development_root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, SyntaxError) as error:
            hits.append(f"{relative}:AST_PARSE:{error}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets: list[ast.expr] = []
                value: ast.expr | None = None
                if isinstance(node, ast.Assign):
                    targets = list(node.targets)
                    value = node.value
                else:
                    targets = [node.target]
                    value = node.value
                for target in targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if target.id in {"EXECUTION_AUTHORITY", "BOLT_ON_EXECUTION_AUTHORITY"}:
                        if not isinstance(value, ast.Constant) or value.value != "NONE":
                            hits.append(f"{relative}:{target.id}:NOT_NONE")

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            method_names = {
                item.name
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            is_adapter = "Adapter" in node.name or any(
                isinstance(base, ast.Attribute) and base.attr == "PortableHostAdapter"
                or isinstance(base, ast.Name) and base.id == "PortableHostAdapter"
                for base in node.bases
            )
            if is_adapter:
                for prohibited in sorted(method_names & PROHIBITED_ADAPTER_METHODS):
                    hits.append(f"{relative}:{node.name}:{prohibited}")
            if node.name == "PortableHostAdapter":
                portable_contract_methods = method_names

    if portable_contract_methods is None:
        hits.append("PortableHostAdapter:MISSING")
    elif portable_contract_methods != EXPECTED_PORTABLE_ADAPTER_METHODS:
        hits.append(
            "PortableHostAdapter:METHOD_SET:"
            + ",".join(sorted(portable_contract_methods))
        )
    return tuple(sorted(hits))


def _verify_v02_manifest(repository_root: Path = REPOSITORY_ROOT) -> str:
    manifest = repository_root / "frozen" / "bolt_on" / "v0.2" / "RELEASE_MANIFEST_SHA256.txt"
    if not manifest.is_file():
        raise QualificationError("frozen v0.2 release manifest is missing")
    digest = _sha256_file(manifest)
    if digest != EXPECTED_V02_RELEASE_MANIFEST_SHA256:
        raise QualificationError(
            "frozen v0.2 release manifest digest mismatch: " + digest
        )
    return digest


def _write_record(record: dict[str, object], path: Path = RC_RECORD_PATH) -> str:
    envelope = {"record": record, "record_sha256": _canonical_digest(record)}
    content = json.dumps(envelope, indent=2, sort_keys=True) + "\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != content:
            raise QualificationError(f"existing RC1 record differs: {path}")
    else:
        path.write_text(content, encoding="utf-8", newline="\n")
    return envelope["record_sha256"]


def qualify(
    repository_root: Path = REPOSITORY_ROOT,
    *,
    runner: Callable[[CommandSpec, Path], CommandEvidence] = _run_command,
    source_commit_provider: Callable[[Path], str] = _git_head,
) -> Tuple[dict[str, object], str]:
    repository_root = repository_root.resolve()
    development_root = repository_root / "development" / "bolt_on_demonstrator_v0_3"
    frozen_root = repository_root / "frozen"

    source_commit = source_commit_provider(repository_root)
    if source_commit != EXPECTED_SOURCE_COMMIT:
        raise QualificationError(
            f"source commit mismatch: expected {EXPECTED_SOURCE_COMMIT}, observed {source_commit}"
        )

    development_before = _tree_manifest_digest(
        development_root, exclude_rc_record=True
    )
    frozen_before = _tree_manifest_digest(frozen_root)

    v02_manifest = _verify_v02_manifest(repository_root)
    prohibited_hits = _adapter_authority_scan(development_root)
    if prohibited_hits:
        raise QualificationError(
            "prohibited adapter or authority surface detected: " + "; ".join(prohibited_hits)
        )

    specs = _command_specs(repository_root)
    first_pass = tuple(runner(spec, repository_root) for spec in specs)
    development_mid = _tree_manifest_digest(development_root, exclude_rc_record=True)
    frozen_mid = _tree_manifest_digest(frozen_root)
    if development_mid != development_before:
        raise QualificationError("development tree changed during first qualification pass")
    if frozen_mid != frozen_before:
        raise QualificationError("frozen tree changed during first qualification pass")

    second_pass = tuple(runner(spec, repository_root) for spec in specs)
    development_after = _tree_manifest_digest(development_root, exclude_rc_record=True)
    frozen_after = _tree_manifest_digest(frozen_root)

    if first_pass != second_pass:
        raise QualificationError("deterministic second-pass evidence mismatch")
    if development_after != development_before:
        raise QualificationError("development tree changed during qualification")
    if frozen_after != frozen_before:
        raise QualificationError("frozen tree changed during qualification")

    test_rows = [item for item in first_pass if item.name == "complete_v0_3_tests"]
    if len(test_rows) != 1 or test_rows[0].observed_test_count != EXPECTED_TEST_COUNT:
        raise QualificationError("complete v0.3 test-count evidence is invalid")

    record: dict[str, object] = {
        "approved_for_freeze_procedure": True,
        "bolt_on_executed_actions": 0,
        "commands": [item.record() for item in first_pass],
        "deterministic_second_pass": True,
        "development_manifest_sha256": development_before,
        "expected_test_count": EXPECTED_TEST_COUNT,
        "frozen_manifest_sha256": frozen_before,
        "frozen_v02_release_manifest_sha256": v02_manifest,
        "host_actions_during_attacks": 0,
        "host_families_qualified": 2,
        "observed_test_count": EXPECTED_TEST_COUNT,
        "portable_actions": ["HOLD", "RELEASE"],
        "prohibited_action_hits": list(prohibited_hits),
        "qualified_attack_count": 48,
        "qualified_attack_rejections": 48,
        "qualified_baseline_host_actions": 2,
        "qualified_substitutions": 1,
        "rc_version": RC_VERSION,
        "second_pass_comparison": "stable normalized qualification evidence; console timing excluded",
        "source_commit": source_commit,
    }
    record_digest = _write_record(
        record,
        development_root / "RC1_QUALIFICATION.json",
    )
    return record, record_digest


def main() -> int:
    try:
        record, record_digest = qualify()
    except Exception as error:
        print(f"V0.3 RC1 QUALIFICATION FAILED: {error}", file=sys.stderr)
        return 1

    print(f"Release candidate: {record['rc_version']}")
    print(f"Source commit: {record['source_commit']}")
    print(f"Expected tests: {record['expected_test_count']}")
    print(f"Observed tests: {record['observed_test_count']}")
    print(f"Development manifest: {record['development_manifest_sha256']}")
    print(f"Frozen tree manifest: {record['frozen_manifest_sha256']}")
    print(f"Frozen v0.2 manifest: {record['frozen_v02_release_manifest_sha256']}")
    print(f"Second pass exact: {record['deterministic_second_pass']}")
    print(f"Host families qualified: {record['host_families_qualified']}")
    print(f"Attacks rejected: {record['qualified_attack_rejections']}")
    print(f"Prohibited action hits: {len(record['prohibited_action_hits'])}")
    print(f"Approved for freeze procedure: {record['approved_for_freeze_procedure']}")
    print(f"RC1 record digest: {record_digest}")
    print(RC_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

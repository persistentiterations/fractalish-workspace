#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 Stage 3."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]

STAGE_2_PATHS = (
    "docs/STAGE_2_ACCEPTANCE_GATES.md",
    "docs/STAGE_2_DOCKER_PREREQUISITE_PROBE_CONTRACT.md",
    "src/bolt_on_v0_4/stage_2.py",
    "src/bolt_on_v0_4/stage_2_cli.py",
    "tests/test_stage_2.py",
    "tools/verify_stage_2.py",
)
EXPECTED_STAGE_2_BLOBS = {
    "docs/STAGE_2_ACCEPTANCE_GATES.md": "e18fef094e9a96bebc4346ba1a7bfb24cd8dfb13",
    "docs/STAGE_2_DOCKER_PREREQUISITE_PROBE_CONTRACT.md": "a6c57f57d861cdd98d6751985a027056b6163a94",
    "src/bolt_on_v0_4/stage_2.py": "59e6436695f20353437ec1c0a93044f3ec58827a",
    "src/bolt_on_v0_4/stage_2_cli.py": "454ce4c6e73c020a9586d77acd02fa703f887a98",
    "tests/test_stage_2.py": "f69b38007a1acb4db01135c9f1bb9e7d2fc6e163",
    "tools/verify_stage_2.py": "2cc351fe093d85edb8dd7fdeab21c9f33931e317",
}

STAGE_3_PATHS = (
    "docs/STAGE_3_ACCEPTANCE_GATES.md",
    "docs/STAGE_3_DISCOVERY_ENROLLMENT_CONTRACT.md",
    "src/bolt_on_v0_4/stage_3.py",
    "src/bolt_on_v0_4/stage_3_cli.py",
    "tests/test_stage_3.py",
    "tools/verify_stage_3.py",
)
STAGE_3_SOURCE_PATHS = (
    "src/bolt_on_v0_4/stage_3.py",
    "src/bolt_on_v0_4/stage_3_cli.py",
    "tools/verify_stage_3.py",
)

EXPECTED_STAGE_2_HEAD = "15e29c94d81e5e5eae3ddf384eb8fa6af8ffcdc4"
EXPECTED_STAGE_2_RECORD_SHA256 = "97b92c58c6bf342c44dd793bfe0a78401b9c606ecaccd27ca1f9c48cd2d6141e"
EXPECTED_STAGE_2_MANIFEST_SHA256 = "6f1c6c119c8114ed20e84c6d28dc1e9de9000e6df861939e5775373e4d957192"

ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "argparse",
    "ast",
    "collections",
    "dataclasses",
    "enum",
    "hashlib",
    "json",
    "pathlib",
    "re",
    "runpy",
    "shutil",
    "subprocess",
    "typing",
}
FORBIDDEN_IMPORT_ROOTS = {"docker", "socket"}
FORBIDDEN_CALL_NAMES = {
    "bind",
    "check_call",
    "check_output",
    "chmod",
    "chown",
    "connect",
    "install",
    "listen",
    "mkdir",
    "open",
    "popen",
    "recv",
    "remove",
    "rename",
    "rmdir",
    "send",
    "start",
    "stop",
    "restart",
    "kill",
    "pause",
    "unpause",
    "touch",
    "unlink",
    "write",
    "write_bytes",
    "write_text",
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(
        f"BOLT-ON CONTINUITY v0.4 STAGE 3 VERIFICATION FAILED: {message}"
    )


def manifest_hash(paths: tuple[str, ...]) -> str:
    entries = []
    for relative in paths:
        data = (ROOT / relative).read_bytes()
        entries.append(
            {
                "path": relative,
                "bytes": len(data),
                "sha256": sha256(data),
            }
        )
    return sha256(canonical_bytes(entries))


def verify_required_files() -> None:
    for relative in (*STAGE_2_PATHS, *STAGE_3_PATHS):
        if not (ROOT / relative).is_file():
            fail(f"missing required file: {relative}")


def verify_stage_two_binding() -> None:
    for relative in STAGE_2_PATHS:
        data = (ROOT / relative).read_bytes()
        observed_blob = git_blob_sha(data)
        if observed_blob != EXPECTED_STAGE_2_BLOBS[relative]:
            fail(f"qualified Stage 2 file changed: {relative}")

    observed_manifest = manifest_hash(STAGE_2_PATHS)
    if observed_manifest != EXPECTED_STAGE_2_MANIFEST_SHA256:
        fail(f"Stage 2 verifier manifest changed: {observed_manifest}")

    namespace = runpy.run_path(
        (ROOT / "src" / "bolt_on_v0_4" / "stage_2.py").as_posix()
    )
    Input = namespace["QualificationInput"]
    Result = namespace["ProbeResult"]
    qualify = namespace["qualify_prerequisites"]
    report = qualify(
        Input(
            "CPython",
            (3, 11, 9),
            "Windows",
            True,
            False,
            Result(
                0,
                '{"Endpoints":{"docker":{"Host":"npipe:////./pipe/'
                'dockerDesktopLinuxEngine"}},"Name":"desktop-linux"}',
            ),
            Result(
                0,
                '{"Client":{"Version":"29.0.0"},'
                '"Server":{"Version":"29.0.0"}}',
            ),
            Result(
                0,
                '{"DockerRootDir":"/var/lib/docker","OSType":"linux"}',
            ),
        )
    )
    observed_record = sha256(report.canonical_bytes())
    if observed_record != EXPECTED_STAGE_2_RECORD_SHA256:
        fail(f"Stage 2 qualification record changed: {observed_record}")


def _import_roots(node: ast.Import | ast.ImportFrom) -> set[str]:
    if isinstance(node, ast.Import):
        return {alias.name.split(".", 1)[0] for alias in node.names}
    if node.level:
        return set()
    return {(node.module or "").split(".", 1)[0]}


def _constant_keyword(call: ast.Call, name: str, expected: object) -> bool:
    for keyword in call.keywords:
        if keyword.arg == name:
            return (
                isinstance(keyword.value, ast.Constant)
                and keyword.value.value == expected
            )
    return False


def verify_subprocess_call(call: ast.Call, relative: str) -> None:
    if len(call.args) != 1 or not isinstance(call.args[0], ast.List):
        fail(f"subprocess argv is not a direct list in {relative}")
    elements = call.args[0].elts
    if (
        len(elements) != 2
        or not isinstance(elements[0], ast.Name)
        or elements[0].id != "executable"
        or not isinstance(elements[1], ast.Starred)
        or not isinstance(elements[1].value, ast.Name)
        or elements[1].value.id != "args"
    ):
        fail(f"subprocess argv vector changed in {relative}")
    for name, expected in (
        ("capture_output", True),
        ("text", True),
        ("shell", False),
        ("check", False),
    ):
        if not _constant_keyword(call, name, expected):
            fail(f"subprocess {name} boundary changed")
    timeout = next(
        (
            keyword.value
            for keyword in call.keywords
            if keyword.arg == "timeout"
        ),
        None,
    )
    if not isinstance(timeout, ast.Name) or timeout.id != "timeout":
        fail("subprocess timeout boundary changed")


def verify_stage_three_source_policy() -> None:
    subprocess_calls = 0
    for relative in STAGE_3_SOURCE_PATHS:
        path = ROOT / relative
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=path.as_posix(),
        )
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                roots = _import_roots(node)
                forbidden = roots & FORBIDDEN_IMPORT_ROOTS
                if forbidden:
                    fail(
                        f"forbidden import in {relative}: {sorted(forbidden)}"
                    )
                unauthorized = roots - ALLOWED_IMPORT_ROOTS
                if unauthorized:
                    fail(
                        f"unauthorized import in {relative}: "
                        f"{sorted(unauthorized)}"
                    )
                if (
                    "subprocess" in roots
                    and relative != "src/bolt_on_v0_4/stage_3.py"
                ):
                    fail(
                        "subprocess imported outside Stage 3 source: "
                        f"{relative}"
                    )
            elif isinstance(node, ast.Call):
                function = node.func
                name = (
                    function.attr
                    if isinstance(function, ast.Attribute)
                    else function.id
                    if isinstance(function, ast.Name)
                    else ""
                )
                if name in FORBIDDEN_CALL_NAMES:
                    fail(
                        "mutation, installation, socket, shell, or persistence "
                        f"call in {relative}: {name}"
                    )
                if (
                    isinstance(function, ast.Attribute)
                    and isinstance(function.value, ast.Name)
                    and function.value.id == "subprocess"
                    and function.attr == "run"
                ):
                    subprocess_calls += 1
                    if relative != "src/bolt_on_v0_4/stage_3.py":
                        fail(
                            "subprocess run outside Stage 3 source: "
                            f"{relative}"
                        )
                    verify_subprocess_call(node, relative)
    if subprocess_calls != 1:
        fail(
            f"expected one bounded subprocess implementation, "
            f"found {subprocess_calls}"
        )


class FakeRunner:
    def __init__(self, results: list[object]) -> None:
        self.results = list(results)
        self.calls: list[tuple[str, tuple[str, ...], int]] = []

    def run(
        self,
        executable: str,
        args: tuple[str, ...],
        timeout: int,
    ) -> object:
        self.calls.append((executable, args, timeout))
        return self.results.pop(0)


def verify_stage_three_vectors() -> object:
    namespace = runpy.run_path(
        (ROOT / "src" / "bolt_on_v0_4" / "stage_3.py").as_posix()
    )
    if namespace["QUALIFIED_STAGE_2_HEAD"] != EXPECTED_STAGE_2_HEAD:
        fail("qualified Stage 2 head binding mismatch")
    if (
        namespace["STAGE_2_QUALIFICATION_RECORD_SHA256"]
        != EXPECTED_STAGE_2_RECORD_SHA256
    ):
        fail("Stage 2 qualification-record binding mismatch")
    if (
        namespace["STAGE_2_VERIFIER_MANIFEST_SHA256"]
        != EXPECTED_STAGE_2_MANIFEST_SHA256
    ):
        fail("Stage 2 verifier-manifest binding mismatch")
    if namespace["PROBE_TIMEOUT_SECONDS"] != 5:
        fail("Stage 3 timeout changed")

    expected_discovery = (
        "container",
        "ls",
        "--all",
        "--no-trunc",
        "--format",
        "{{json .}}",
    )
    if namespace["DISCOVERY_ARGS"] != expected_discovery:
        fail("Stage 3 discovery vector changed")

    Result = namespace["ProbeResult"]
    discover = namespace["discover_candidates"]
    select = namespace["select_candidate"]
    enroll = namespace["inspect_and_enroll"]
    cid = "a" * 64
    discovery_line = json.dumps(
        {
            "ID": cid,
            "Names": "alpha",
            "Image": "alpine:latest",
            "State": "running",
        }
    )
    discovery_runner = FakeRunner([Result(0, discovery_line)])
    discovery = discover("docker", discovery_runner)
    if discovery.status != "STAGE_3_DISCOVERY_READY":
        fail("qualified discovery vector was not ready")
    if len(discovery.candidates) != 1:
        fail("qualified discovery candidate count changed")
    candidate = select(discovery.candidates, cid, cid)

    inspection = json.dumps(
        {
            "Id": cid,
            "Name": "/alpha",
            "Image": "alpine:latest",
            "State": "running",
            "Platform": "linux",
        }
    )
    inspection_runner = FakeRunner([Result(0, inspection)])
    record = enroll("docker", candidate, inspection_runner)
    if record.status != "STAGE_3_ENROLLED":
        fail("qualified enrollment vector did not enroll")
    enabled = {
        key for key, value in record.authority.items() if value
    }
    expected_enabled = {
        "docker_prerequisite_probe",
        "local_docker_daemon_contact",
        "container_enumeration",
        "single_container_inspection",
        "enrollment_record_construction",
    }
    if enabled != expected_enabled:
        fail(f"Stage 3 authority set changed: {sorted(enabled)}")
    if record.record_digest != sha256(
        canonical_bytes(record.body_without_digest())
    ):
        fail("Stage 3 enrollment digest mismatch")
    if record.canonical_bytes() != canonical_bytes(record.body()):
        fail("Stage 3 canonical serialization mismatch")
    serialized = record.canonical_json()
    for forbidden in (
        "docker.exe",
        "stderr",
        "DOCKER_HOST",
        "LogPath",
        "Config.Env",
        "/var/lib/docker",
    ):
        if forbidden in serialized:
            fail(f"sensitive material serialized: {forbidden}")

    try:
        select(discovery.candidates, cid, "b" * 64)
    except namespace["EnrollmentError"]:
        pass
    else:
        fail("confirmation mismatch did not fail closed")

    Runner = namespace["SubprocessDockerRunner"]
    bounded_runner = Runner()
    try:
        bounded_runner.run(
            "docker",
            ("container", "start", cid),
            5,
        )
    except ValueError:
        pass
    else:
        fail("mutation vector was accepted")

    tests = (ROOT / "tests" / "test_stage_3.py").read_text(
        encoding="utf-8"
    )
    if tests.count("def test_") != 21:
        fail("Stage 3 test inventory mismatch")
    return record


def main() -> int:
    verify_required_files()
    verify_stage_two_binding()
    verify_stage_three_source_policy()
    record = verify_stage_three_vectors()

    record_hash = sha256(record.canonical_bytes())
    stage_three_manifest = manifest_hash(STAGE_3_PATHS)
    print(f"Stage 3 qualification record SHA-256: {record_hash}")
    print(
        "Stage 3 verifier manifest SHA-256: "
        f"{stage_three_manifest}"
    )
    print(
        "BOLT-ON CONTINUITY v0.4 STAGE 3 VERIFICATION PASSED: "
        f"{len(STAGE_3_PATHS)} files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

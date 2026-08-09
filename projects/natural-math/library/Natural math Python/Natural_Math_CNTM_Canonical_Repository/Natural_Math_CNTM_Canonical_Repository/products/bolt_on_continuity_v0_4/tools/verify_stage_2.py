#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 Stage 2."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
STAGE_1_PATHS = (
    "docs/STAGE_1_ACCEPTANCE_GATES.md",
    "docs/STAGE_1_PREREQUISITE_DOCTOR_CONTRACT.md",
    "src/bolt_on_v0_4/__main__.py",
    "src/bolt_on_v0_4/cli.py",
    "src/bolt_on_v0_4/stage_1.py",
    "tests/test_stage_1.py",
    "tools/verify_stage_1.py",
)
EXPECTED_STAGE_1_BLOBS = {
    "docs/STAGE_1_ACCEPTANCE_GATES.md": "6c4a16fa2f2e489a4b4bd2f9f631cf3f0b40c087",
    "docs/STAGE_1_PREREQUISITE_DOCTOR_CONTRACT.md": "3ad4c9c6fdafa9e21af981ad2503d21e17b86029",
    "src/bolt_on_v0_4/__main__.py": "6312ac5505b5fbd91fae137ba1dc17775aa1a3f1",
    "src/bolt_on_v0_4/cli.py": "7c662e569dab923147a42c1eb8c2e6e5e0d9eab1",
    "src/bolt_on_v0_4/stage_1.py": "f4eaef3092c65e4c4d6e8894cc4f1837e004444f",
    "tests/test_stage_1.py": "8fc7a96ed60b5674690550222f3c0899007e6ee6",
    "tools/verify_stage_1.py": "7b7b97294502e7697a49f8fd07583b37b50879b9",
}
STAGE_2_PATHS = (
    "docs/STAGE_2_ACCEPTANCE_GATES.md",
    "docs/STAGE_2_DOCKER_PREREQUISITE_PROBE_CONTRACT.md",
    "src/bolt_on_v0_4/stage_2.py",
    "src/bolt_on_v0_4/stage_2_cli.py",
    "tests/test_stage_2.py",
    "tools/verify_stage_2.py",
)
STAGE_2_SOURCE_PATHS = (
    "src/bolt_on_v0_4/stage_2.py",
    "src/bolt_on_v0_4/stage_2_cli.py",
    "tools/verify_stage_2.py",
)
EXPECTED_STAGE_1_HEAD = "5cfc92e205d99e34ef02376ff0c560a62bbbf435"
EXPECTED_STAGE_1_RECORD_SHA256 = "9fcd999f9d1e3817f53a60ff9b61193ec0576d808b14bdbbb7d806e86a83da2b"
EXPECTED_STAGE_1_MANIFEST_SHA256 = "d94edb9ada5857f56d2785ae81dcf58768791fda46e7c1fc6e13c74ac57eaf18"
ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "argparse",
    "ast",
    "collections",
    "dataclasses",
    "enum",
    "hashlib",
    "json",
    "os",
    "pathlib",
    "platform",
    "runpy",
    "shutil",
    "subprocess",
    "sys",
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
        f"BOLT-ON CONTINUITY v0.4 STAGE 2 VERIFICATION FAILED: {message}"
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
    for relative in (*STAGE_1_PATHS, *STAGE_2_PATHS):
        if not (ROOT / relative).is_file():
            fail(f"missing required file: {relative}")


def verify_stage_one_binding() -> None:
    for relative in STAGE_1_PATHS:
        data = (ROOT / relative).read_bytes()
        observed_blob = git_blob_sha(data)
        if observed_blob != EXPECTED_STAGE_1_BLOBS[relative]:
            fail(f"qualified Stage 1 file changed: {relative}")

    observed_manifest = manifest_hash(STAGE_1_PATHS)
    if observed_manifest != EXPECTED_STAGE_1_MANIFEST_SHA256:
        fail(f"Stage 1 verifier manifest changed: {observed_manifest}")

    namespace = runpy.run_path(
        (ROOT / "src" / "bolt_on_v0_4" / "stage_1.py").as_posix()
    )
    Snapshot = namespace["EnvironmentSnapshot"]
    build = namespace["build_doctor_report"]
    report = build(
        Snapshot(
            (3, 11, 9),
            "Windows",
            {"LOCALAPPDATA": "C:/Users/Example/AppData/Local"},
            "C:/Program Files/Docker/docker.exe",
        )
    )
    observed_record = sha256(report.canonical_bytes())
    if observed_record != EXPECTED_STAGE_1_RECORD_SHA256:
        fail(f"Stage 1 qualification record changed: {observed_record}")
    if set(report.authority.values()) != {False}:
        fail("Stage 1 authority boundary changed")


def _root_names(node: ast.Import | ast.ImportFrom) -> set[str]:
    if isinstance(node, ast.Import):
        return {alias.name.split(".", 1)[0] for alias in node.names}
    if node.level:
        return set()
    return {(node.module or "").split(".", 1)[0]}


def _constant_keyword(call: ast.Call, name: str, expected: object) -> bool:
    for keyword in call.keywords:
        if keyword.arg == name:
            return isinstance(keyword.value, ast.Constant) and keyword.value.value == expected
    return False


def verify_subprocess_vector(call: ast.Call, relative: str) -> None:
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
    if not _constant_keyword(call, "capture_output", True):
        fail("subprocess capture_output boundary changed")
    if not _constant_keyword(call, "text", True):
        fail("subprocess text boundary changed")
    if not _constant_keyword(call, "shell", False):
        fail("subprocess shell boundary changed")
    if not _constant_keyword(call, "check", False):
        fail("subprocess check boundary changed")
    timeout = next(
        (keyword.value for keyword in call.keywords if keyword.arg == "timeout"),
        None,
    )
    if not isinstance(timeout, ast.Name) or timeout.id != "timeout":
        fail("subprocess timeout boundary changed")


def verify_stage_two_source_policy() -> None:
    subprocess_calls = 0
    for relative in STAGE_2_SOURCE_PATHS:
        path = ROOT / relative
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=path.as_posix(),
        )
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                roots = _root_names(node)
                forbidden = roots & FORBIDDEN_IMPORT_ROOTS
                if forbidden:
                    fail(f"forbidden import in {relative}: {sorted(forbidden)}")
                unauthorized = roots - ALLOWED_IMPORT_ROOTS
                if unauthorized:
                    fail(f"unauthorized import in {relative}: {sorted(unauthorized)}")
                if "subprocess" in roots and relative != "src/bolt_on_v0_4/stage_2.py":
                    fail(f"subprocess imported outside Stage 2 probe source: {relative}")
            elif isinstance(node, ast.Call):
                function = node.func
                name = (
                    function.attr
                    if isinstance(function, ast.Attribute)
                    else function.id
                    if isinstance(function, ast.Name)
                    else ""
                )
                if (
                    isinstance(function, ast.Attribute)
                    and isinstance(function.value, ast.Name)
                    and function.value.id == "os"
                    and function.attr == "system"
                ):
                    fail(f"shell call in {relative}: os.system")
                if name in FORBIDDEN_CALL_NAMES:
                    fail(f"mutation, installation, socket, or shell call in {relative}: {name}")
                if (
                    isinstance(function, ast.Attribute)
                    and isinstance(function.value, ast.Name)
                    and function.value.id == "subprocess"
                    and function.attr == "run"
                ):
                    subprocess_calls += 1
                    if relative != "src/bolt_on_v0_4/stage_2.py":
                        fail(f"subprocess run outside Stage 2 probe source: {relative}")
                    verify_subprocess_vector(node, relative)
    if subprocess_calls != 1:
        fail(f"expected one bounded subprocess vector, found {subprocess_calls}")


def verify_stage_two_vectors() -> object:
    namespace = runpy.run_path(
        (ROOT / "src" / "bolt_on_v0_4" / "stage_2.py").as_posix()
    )
    if namespace["QUALIFIED_STAGE_1_HEAD"] != EXPECTED_STAGE_1_HEAD:
        fail("qualified Stage 1 head binding mismatch")
    if namespace["STAGE_1_QUALIFICATION_RECORD_SHA256"] != EXPECTED_STAGE_1_RECORD_SHA256:
        fail("Stage 1 qualification record binding mismatch")
    if namespace["STAGE_1_VERIFIER_MANIFEST_SHA256"] != EXPECTED_STAGE_1_MANIFEST_SHA256:
        fail("Stage 1 verifier manifest binding mismatch")

    expected_vectors = (
        ("context", "inspect", "--format", "{{json .}}"),
        ("version", "--format", "{{json .}}"),
        ("info", "--format", "{{json .}}"),
    )
    if namespace["ALLOWED_PROBE_VECTORS"] != expected_vectors:
        fail("Docker prerequisite probe vectors changed")
    if namespace["PROBE_TIMEOUT_SECONDS"] != 5:
        fail("Docker prerequisite timeout changed")

    Input = namespace["QualificationInput"]
    Result = namespace["ProbeResult"]
    qualify = namespace["qualify_prerequisites"]
    data = Input(
        "CPython",
        (3, 11, 9),
        "Windows",
        True,
        False,
        Result(
            0,
            '{"Endpoints":{"docker":{"Host":"npipe:////./pipe/dockerDesktopLinuxEngine"}},"Name":"desktop-linux"}',
        ),
        Result(
            0,
            '{"Client":{"Version":"29.0.0"},"Server":{"Version":"29.0.0"}}',
        ),
        Result(0, '{"DockerRootDir":"/var/lib/docker","OSType":"linux"}'),
    )
    report = qualify(data)
    if not report.eligible or report.status != "STAGE_2_ELIGIBLE":
        fail("qualified Stage 2 vector was not eligible")
    enabled = {key for key, value in report.authority.items() if value}
    if enabled != {"docker_prerequisite_probe", "local_docker_daemon_contact"}:
        fail(f"Stage 2 authority set changed: {sorted(enabled)}")
    if report.report_digest != sha256(canonical_bytes(report.body_without_digest())):
        fail("Stage 2 report digest mismatch")
    if report.canonical_bytes() != canonical_bytes(report.body()):
        fail("Stage 2 canonical serialization mismatch")
    serialized = report.canonical_json()
    for forbidden in (
        "dockerDesktopLinuxEngine",
        "/var/lib/docker",
        "docker.exe",
        "DOCKER_HOST",
        "stderr",
    ):
        if forbidden in serialized:
            fail(f"sensitive probe material serialized: {forbidden}")

    remote = qualify(
        Input(
            "CPython",
            (3, 11, 9),
            "Windows",
            True,
            False,
            Result(0, '{"Endpoints":{"docker":{"Host":"tcp://example:2376"}}}'),
            data.version_result,
            data.info_result,
        )
    )
    if remote.eligible or "REMOTE_OR_AMBIGUOUS_CONTEXT" not in remote.reason_codes:
        fail("remote Docker context did not fail closed")

    override = qualify(
        Input(
            "CPython",
            (3, 11, 9),
            "Windows",
            True,
            True,
            data.context_result,
            data.version_result,
            data.info_result,
        )
    )
    if override.eligible or "REMOTE_OVERRIDE_PRESENT" not in override.reason_codes:
        fail("remote Docker environment override did not fail closed")

    tests = (ROOT / "tests" / "test_stage_2.py").read_text(encoding="utf-8")
    if tests.count("def test_") != 16:
        fail("Stage 2 test inventory mismatch")
    cli = (ROOT / "src" / "bolt_on_v0_4" / "stage_2_cli.py").read_text(encoding="utf-8")
    if cli.count("add_argument(") != 1 or '"--json"' not in cli:
        fail("Stage 2 CLI accepts more than the canonical output selector")
    return report


def main() -> int:
    verify_required_files()
    verify_stage_one_binding()
    verify_stage_two_source_policy()
    report = verify_stage_two_vectors()

    record_hash = sha256(report.canonical_bytes())
    stage_two_manifest = manifest_hash(STAGE_2_PATHS)
    print(f"Stage 2 qualification record SHA-256: {record_hash}")
    print(f"Stage 2 verifier manifest SHA-256: {stage_two_manifest}")
    print(
        "BOLT-ON CONTINUITY v0.4 STAGE 2 VERIFICATION PASSED: "
        f"{len(STAGE_2_PATHS)} files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

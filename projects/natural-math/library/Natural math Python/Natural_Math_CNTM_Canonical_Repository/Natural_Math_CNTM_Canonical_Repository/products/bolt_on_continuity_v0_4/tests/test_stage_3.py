import json

import pytest

from bolt_on_v0_4.stage_3 import (
    AUTHORITY,
    DISCOVERY_ARGS,
    INSPECTION_PREFIX,
    PROBE_TIMEOUT_SECONDS,
    ContainerCandidate,
    EnrollmentError,
    ProbeResult,
    SubprocessDockerRunner,
    build_discovery_report,
    canonical_bytes,
    discover_candidates,
    inspect_and_enroll,
    parse_discovery,
    select_candidate,
    sha256,
)


CID_A = "a" * 64
CID_B = "b" * 64


def discovery_line(
    container_id: str = CID_A,
    name: str = "alpha",
    image: str = "alpine:latest",
    state: str = "running",
) -> str:
    return json.dumps(
        {
            "ID": container_id,
            "Names": name,
            "Image": image,
            "State": state,
        }
    )


def inspection(
    container_id: str = CID_A,
    name: str = "/alpha",
    image: str = "alpine:latest",
    state: str = "running",
    platform: str = "linux",
) -> str:
    return json.dumps(
        {
            "Id": container_id,
            "Name": name,
            "Image": image,
            "State": state,
            "Platform": platform,
        }
    )


class FakeRunner:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def run(self, executable, args, timeout):
        self.calls.append((executable, args, timeout))
        return self.outputs.pop(0)


def candidate() -> ContainerCandidate:
    return ContainerCandidate(CID_A, "alpha", "alpine:latest", "running")


def test_discovery_parses_and_sorts_full_ids() -> None:
    parsed = parse_discovery(
        discovery_line(CID_B, "beta", "busybox:latest", "exited")
        + "\n"
        + discovery_line()
    )
    assert [item.container_id for item in parsed] == [CID_A, CID_B]


def test_empty_discovery_is_valid() -> None:
    assert parse_discovery("") == ()


def test_malformed_discovery_fails_closed() -> None:
    with pytest.raises(EnrollmentError, match="MALFORMED_DISCOVERY"):
        parse_discovery("not-json")


def test_truncated_id_fails_closed() -> None:
    with pytest.raises(EnrollmentError, match="INVALID_CONTAINER_ID"):
        parse_discovery(discovery_line("a" * 12))


def test_uppercase_id_fails_closed() -> None:
    with pytest.raises(EnrollmentError, match="INVALID_CONTAINER_ID"):
        parse_discovery(discovery_line("A" * 64))


def test_duplicate_id_fails_closed() -> None:
    with pytest.raises(EnrollmentError, match="DUPLICATE_CONTAINER_ID"):
        parse_discovery(discovery_line() + "\n" + discovery_line())


def test_unknown_state_fails_closed() -> None:
    with pytest.raises(EnrollmentError, match="UNSUPPORTED_CONTAINER_STATE"):
        parse_discovery(discovery_line(state="mysterious"))


def test_oversized_metadata_fails_closed() -> None:
    with pytest.raises(EnrollmentError, match="AMBIGUOUS_METADATA"):
        parse_discovery(discovery_line(name="x" * 257))


def test_selection_requires_exact_confirmed_id() -> None:
    assert select_candidate((candidate(),), CID_A, CID_A) == candidate()
    with pytest.raises(EnrollmentError, match="CONFIRMATION_MISMATCH"):
        select_candidate((candidate(),), CID_A, CID_B)


def test_unknown_selection_fails_closed() -> None:
    with pytest.raises(EnrollmentError, match="UNKNOWN_SELECTION"):
        select_candidate((candidate(),), CID_B, CID_B)


def test_discovery_runner_uses_only_fixed_vector() -> None:
    runner = FakeRunner([ProbeResult(0, discovery_line())])
    report = discover_candidates("docker.exe", runner)
    assert report.status == "STAGE_3_DISCOVERY_READY"
    assert runner.calls == [
        ("docker.exe", DISCOVERY_ARGS, PROBE_TIMEOUT_SECONDS)
    ]


def test_discovery_timeout_fails_closed() -> None:
    runner = FakeRunner([ProbeResult(124, "", "timeout", True)])
    with pytest.raises(EnrollmentError, match="DISCOVERY_TIMEOUT"):
        discover_candidates("docker.exe", runner)


def test_inspection_builds_deterministic_enrollment() -> None:
    runner = FakeRunner([ProbeResult(0, inspection())])
    first = inspect_and_enroll("docker.exe", candidate(), runner)
    runner = FakeRunner([ProbeResult(0, inspection())])
    second = inspect_and_enroll("docker.exe", candidate(), runner)
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.status == "STAGE_3_ENROLLED"
    assert first.record_digest == sha256(
        canonical_bytes(first.body_without_digest())
    )
    assert set(key for key, value in first.authority.items() if value) == {
        "docker_prerequisite_probe",
        "local_docker_daemon_contact",
        "container_enumeration",
        "single_container_inspection",
        "enrollment_record_construction",
    }


def test_inspection_runner_uses_exact_full_id() -> None:
    runner = FakeRunner([ProbeResult(0, inspection())])
    inspect_and_enroll("docker.exe", candidate(), runner)
    assert runner.calls == [
        (
            "docker.exe",
            (*INSPECTION_PREFIX, CID_A),
            PROBE_TIMEOUT_SECONDS,
        )
    ]


def test_inspection_identity_mismatch_fails_closed() -> None:
    runner = FakeRunner([ProbeResult(0, inspection(container_id=CID_B))])
    with pytest.raises(EnrollmentError, match="INSPECTION_IDENTITY_MISMATCH"):
        inspect_and_enroll("docker.exe", candidate(), runner)


def test_inspection_name_mismatch_fails_closed() -> None:
    runner = FakeRunner([ProbeResult(0, inspection(name="/other"))])
    with pytest.raises(EnrollmentError, match="INSPECTION_NAME_MISMATCH"):
        inspect_and_enroll("docker.exe", candidate(), runner)


def test_inspection_image_mismatch_fails_closed() -> None:
    runner = FakeRunner([ProbeResult(0, inspection(image="other:latest"))])
    with pytest.raises(EnrollmentError, match="INSPECTION_IMAGE_MISMATCH"):
        inspect_and_enroll("docker.exe", candidate(), runner)


def test_non_linux_inspection_fails_closed() -> None:
    runner = FakeRunner([ProbeResult(0, inspection(platform="windows"))])
    with pytest.raises(EnrollmentError, match="UNSUPPORTED_PLATFORM"):
        inspect_and_enroll("docker.exe", candidate(), runner)


def test_discovery_report_is_deterministic() -> None:
    first = build_discovery_report((candidate(),))
    second = build_discovery_report((candidate(),))
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.report_digest == sha256(
        canonical_bytes(first.body_without_digest())
    )


def test_subprocess_runner_rejects_unapproved_commands() -> None:
    runner = SubprocessDockerRunner()
    with pytest.raises(ValueError, match="unsupported Stage 3 Docker vector"):
        runner.run("docker", ("container", "start", CID_A), 5)
    with pytest.raises(ValueError, match="unsupported Stage 3 Docker vector"):
        runner.run("docker", (*INSPECTION_PREFIX, "a" * 12), 5)
    with pytest.raises(ValueError, match="unsupported Stage 3 timeout"):
        runner.run("docker", DISCOVERY_ARGS, 6)


def test_record_excludes_raw_or_mutating_material() -> None:
    runner = FakeRunner([ProbeResult(0, inspection())])
    record = inspect_and_enroll("docker.exe", candidate(), runner)
    rendered = record.canonical_json()
    assert "stderr" not in rendered
    assert "docker.exe" not in rendered
    assert "start_stop_restart" in rendered
    assert AUTHORITY["docker_mutation"] is False

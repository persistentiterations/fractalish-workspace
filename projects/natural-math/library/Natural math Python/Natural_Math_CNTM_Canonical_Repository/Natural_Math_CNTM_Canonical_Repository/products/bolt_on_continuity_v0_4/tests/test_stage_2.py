import json

import pytest

from bolt_on_v0_4.stage_2 import (
    ALLOWED_PROBE_VECTORS,
    AUTHORITY,
    CONTEXT_ARGS,
    INFO_ARGS,
    PROBE_TIMEOUT_SECONDS,
    VERSION_ARGS,
    ProbeResult,
    QualificationInput,
    SubprocessProbeRunner,
    canonical_bytes,
    qualify_prerequisites,
    sha256,
)


def qualified_input(**overrides: object) -> QualificationInput:
    values: dict[str, object] = {
        "python_implementation": "CPython",
        "python_version": (3, 11, 9),
        "platform_system": "Windows",
        "docker_cli_present": True,
        "remote_override_present": False,
        "context_result": ProbeResult(
            0,
            json.dumps(
                {
                    "Name": "desktop-linux",
                    "Endpoints": {
                        "docker": {
                            "Host": "npipe:////./pipe/dockerDesktopLinuxEngine"
                        }
                    },
                }
            ),
        ),
        "version_result": ProbeResult(
            0,
            json.dumps(
                {
                    "Client": {"Version": "29.0.0"},
                    "Server": {"Version": "29.0.0"},
                }
            ),
        ),
        "info_result": ProbeResult(
            0,
            json.dumps({"OSType": "linux", "DockerRootDir": "/var/lib/docker"}),
        ),
    }
    values.update(overrides)
    return QualificationInput(**values)


def test_qualified_local_docker_is_eligible() -> None:
    report = qualify_prerequisites(qualified_input())
    assert report.eligible is True
    assert report.status == "STAGE_2_ELIGIBLE"
    assert report.reason_codes == ()


def test_report_is_deterministic() -> None:
    first = qualify_prerequisites(qualified_input()).canonical_bytes()
    second = qualify_prerequisites(qualified_input()).canonical_bytes()
    assert first == second


def test_authority_is_exactly_bounded() -> None:
    report = qualify_prerequisites(qualified_input())
    assert dict(report.authority) == AUTHORITY
    enabled = {key for key, value in report.authority.items() if value}
    assert enabled == {
        "docker_prerequisite_probe",
        "local_docker_daemon_contact",
    }


def test_old_python_fails_closed() -> None:
    report = qualify_prerequisites(
        qualified_input(python_version=(3, 10, 14))
    )
    assert "UNSUPPORTED_PYTHON" in report.reason_codes
    assert report.eligible is False


def test_missing_cli_fails_closed() -> None:
    report = qualify_prerequisites(
        qualified_input(
            docker_cli_present=False,
            context_result=None,
            version_result=None,
            info_result=None,
        )
    )
    assert "DOCKER_CLI_MISSING" in report.reason_codes


def test_remote_environment_override_fails_closed() -> None:
    report = qualify_prerequisites(
        qualified_input(remote_override_present=True)
    )
    assert "REMOTE_OVERRIDE_PRESENT" in report.reason_codes


def test_remote_tcp_context_fails_closed() -> None:
    context = ProbeResult(
        0,
        json.dumps(
            {"Endpoints": {"docker": {"Host": "tcp://example:2376"}}}
        ),
    )
    report = qualify_prerequisites(qualified_input(context_result=context))
    assert "REMOTE_OR_AMBIGUOUS_CONTEXT" in report.reason_codes


def test_local_unix_context_is_allowed() -> None:
    context = ProbeResult(
        0,
        json.dumps(
            {"Endpoints": {"docker": {"Host": "unix:///var/run/docker.sock"}}}
        ),
    )
    report = qualify_prerequisites(
        qualified_input(platform_system="Linux", context_result=context)
    )
    assert report.eligible is True


def test_context_timeout_fails_closed() -> None:
    report = qualify_prerequisites(
        qualified_input(
            context_result=ProbeResult(124, "", "timeout", True)
        )
    )
    assert "CONTEXT_PROBE_UNAVAILABLE" in report.reason_codes


def test_malformed_version_json_fails_closed() -> None:
    report = qualify_prerequisites(
        qualified_input(version_result=ProbeResult(0, "not-json"))
    )
    assert "DOCKER_CLIENT_UNAVAILABLE" in report.reason_codes
    assert "DOCKER_SERVER_UNAVAILABLE" in report.reason_codes


def test_nonzero_server_probe_fails_closed() -> None:
    report = qualify_prerequisites(
        qualified_input(version_result=ProbeResult(1, "", "daemon unavailable"))
    )
    assert "DOCKER_SERVER_UNAVAILABLE" in report.reason_codes


def test_windows_engine_fails_closed() -> None:
    report = qualify_prerequisites(
        qualified_input(info_result=ProbeResult(0, '{"OSType":"windows"}'))
    )
    assert "ENGINE_NOT_LINUX" in report.reason_codes


def test_report_digest_recomputes() -> None:
    report = qualify_prerequisites(qualified_input())
    assert report.report_digest == sha256(
        canonical_bytes(report.body_without_digest())
    )


def test_report_excludes_sensitive_paths_and_endpoints() -> None:
    rendered = qualify_prerequisites(qualified_input()).canonical_json()
    assert "dockerDesktopLinuxEngine" not in rendered
    assert "/var/lib/docker" not in rendered
    assert "Users" not in rendered
    assert "docker.exe" not in rendered


def test_fixed_probe_vectors_are_distinct() -> None:
    assert ALLOWED_PROBE_VECTORS == (CONTEXT_ARGS, VERSION_ARGS, INFO_ARGS)
    assert len(set(ALLOWED_PROBE_VECTORS)) == 3
    assert PROBE_TIMEOUT_SECONDS == 5


def test_runner_rejects_unauthorized_vector_and_timeout() -> None:
    runner = SubprocessProbeRunner()
    with pytest.raises(ValueError):
        runner.run("docker", ("ps",), PROBE_TIMEOUT_SECONDS)
    with pytest.raises(ValueError):
        runner.run("docker", CONTEXT_ARGS, 30)

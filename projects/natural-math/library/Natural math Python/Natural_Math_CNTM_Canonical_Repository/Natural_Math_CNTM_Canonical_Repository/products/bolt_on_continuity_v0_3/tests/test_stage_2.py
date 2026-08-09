import json

from bolt_on.prerequisites import (
    INFO_ARGS,
    VERSION_ARGS,
    ProbeResult,
    QualificationInput,
    SubprocessProbeRunner,
    qualify_host,
)


def qualified_input():
    return QualificationInput(
        "CPython",
        (3, 14, 6),
        "Windows",
        "AMD64",
        True,
        ProbeResult(0, json.dumps({"Client": {"Version": "29.0.0"}, "Server": {"Version": "29.0.0"}})),
        ProbeResult(0, json.dumps({"OSType": "linux", "Name": "desktop-linux", "DockerRootDir": "/var/lib/docker"})),
    )


def test_qualified_host_is_eligible():
    report = qualify_host(qualified_input())
    assert report.eligible is True
    assert report.reason_codes == ()
    assert report.details["gateway_enabled"] is False
    assert report.details["observation_only"] is True


def test_windows_engine_fails_closed():
    data = qualified_input()
    report = qualify_host(QualificationInput(data.python_implementation, data.python_version, data.host_family, data.machine, True, data.version_result, ProbeResult(0, json.dumps({"OSType": "windows", "Name": "default", "DockerRootDir": "C:/docker"}))))
    assert "ENGINE_NOT_LINUX" in report.reason_codes


def test_malformed_json_fails_closed():
    data = qualified_input()
    report = qualify_host(QualificationInput(data.python_implementation, data.python_version, data.host_family, data.machine, True, ProbeResult(0, "not-json"), data.info_result))
    assert report.eligible is False
    assert "DOCKER_CLIENT_UNAVAILABLE" in report.reason_codes


def test_timeout_fails_closed():
    data = qualified_input()
    report = qualify_host(QualificationInput(data.python_implementation, data.python_version, data.host_family, data.machine, True, ProbeResult(124, "", "timeout", True), data.info_result))
    assert report.eligible is False


def test_report_excludes_sensitive_paths():
    body = qualify_host(qualified_input()).body()
    text = json.dumps(body)
    assert "docker.exe" not in text
    assert "Users" not in text
    assert "DockerRootDir" not in text


def test_runner_rejects_unapproved_vector():
    runner = SubprocessProbeRunner()
    try:
        runner.run("docker", ("ps",), 5)
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported vector accepted")
    assert VERSION_ARGS != INFO_ARGS

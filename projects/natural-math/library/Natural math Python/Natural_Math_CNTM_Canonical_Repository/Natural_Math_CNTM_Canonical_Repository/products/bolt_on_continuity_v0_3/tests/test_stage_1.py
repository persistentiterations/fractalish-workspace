from bolt_on.environment import CheckStatus, EnvironmentSnapshot, build_doctor_report, recommended_data_directory


def windows_snapshot(**overrides):
    values = {
        "python_version": (3, 14, 6),
        "platform_system": "Windows",
        "environment": {"LOCALAPPDATA": r"C:\\Users\\Example\\AppData\\Local"},
        "docker_cli_path": r"C:\\Program Files\\Docker\\docker.exe",
    }
    values.update(overrides)
    return EnvironmentSnapshot(**values)


def test_doctor_report_is_deterministic():
    report_a = build_doctor_report(windows_snapshot())
    report_b = build_doctor_report(windows_snapshot())
    assert report_a.canonical_json() == report_b.canonical_json()
    assert report_a.ready is True


def test_old_python_fails_closed():
    report = build_doctor_report(windows_snapshot(python_version=(3, 10, 9)))
    assert report.ready is False
    assert report.checks[0].status is CheckStatus.FAIL


def test_missing_docker_cli_is_warning_only():
    report = build_doctor_report(windows_snapshot(docker_cli_path=None))
    docker_check = next(check for check in report.checks if check.check_id == "docker.cli")
    assert docker_check.status is CheckStatus.WARN
    assert report.ready is True


def test_windows_recommended_path():
    path = recommended_data_directory(windows_snapshot())
    assert str(path) == r"C:\Users\Example\AppData\Local\BoltOn\Continuity"


def test_linux_recommended_path():
    snapshot = EnvironmentSnapshot((3, 11, 0), "Linux", {"HOME": "/home/example"}, None)
    assert str(recommended_data_directory(snapshot)) == "/home/example/.local/state/bolt-on/continuity"


def test_json_contains_observation_only_authority():
    report = build_doctor_report(windows_snapshot())
    assert '"authority_class":"OBSERVATION_ONLY"' in report.canonical_json()

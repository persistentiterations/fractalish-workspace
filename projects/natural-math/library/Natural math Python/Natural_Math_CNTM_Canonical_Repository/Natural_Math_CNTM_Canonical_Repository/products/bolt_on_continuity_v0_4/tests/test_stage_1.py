from bolt_on_v0_4.cli import render_doctor
from bolt_on_v0_4.stage_1 import (
    AUTHORITY,
    CheckStatus,
    EnvironmentSnapshot,
    STAGE_0_QUALIFICATION_RECORD_SHA256,
    STAGE_0_VERIFIER_MANIFEST_SHA256,
    build_doctor_report,
    canonical_bytes,
    recommended_data_directory,
    sha256,
)


def windows_snapshot(**overrides: object) -> EnvironmentSnapshot:
    values: dict[str, object] = {
        "python_version": (3, 11, 9),
        "platform_system": "Windows",
        "environment": {"LOCALAPPDATA": "C:/Users/Example/AppData/Local"},
        "docker_cli_path": "C:/Program Files/Docker/docker.exe",
    }
    values.update(overrides)
    return EnvironmentSnapshot(**values)


def test_qualified_snapshot_is_ready() -> None:
    report = build_doctor_report(windows_snapshot())
    assert report.ready is True
    assert report.status == "STAGE_1_READY"


def test_report_is_deterministic() -> None:
    first = build_doctor_report(windows_snapshot()).canonical_bytes()
    second = build_doctor_report(windows_snapshot()).canonical_bytes()
    assert first == second


def test_old_python_fails_closed() -> None:
    report = build_doctor_report(
        windows_snapshot(python_version=(3, 10, 14))
    )
    assert report.status == "NOT_READY"
    python_check = next(
        check for check in report.checks if check.check_id == "python.version"
    )
    assert python_check.status is CheckStatus.FAIL


def test_missing_docker_cli_is_warning_only() -> None:
    report = build_doctor_report(windows_snapshot(docker_cli_path=None))
    docker_check = next(
        check for check in report.checks if check.check_id == "docker.cli"
    )
    assert docker_check.status is CheckStatus.WARN
    assert report.ready is True


def test_unsupported_platform_is_warning_only() -> None:
    report = build_doctor_report(
        windows_snapshot(platform_system="Plan9")
    )
    platform_check = next(
        check for check in report.checks if check.check_id == "platform.system"
    )
    assert platform_check.status is CheckStatus.WARN
    assert report.ready is True


def test_windows_recommended_path() -> None:
    assert str(recommended_data_directory(windows_snapshot())) == (
        "C:\\Users\\Example\\AppData\\Local\\BoltOn\\Continuity\\v0.4"
    )


def test_linux_recommended_paths() -> None:
    home = EnvironmentSnapshot(
        (3, 11, 0),
        "Linux",
        {"HOME": "/home/example"},
        None,
    )
    xdg = EnvironmentSnapshot(
        (3, 11, 0),
        "Linux",
        {"XDG_STATE_HOME": "/state/example"},
        None,
    )
    assert str(recommended_data_directory(home)) == (
        "/home/example/.local/state/bolt-on-continuity/v0.4"
    )
    assert str(recommended_data_directory(xdg)) == (
        "/state/example/bolt-on-continuity/v0.4"
    )


def test_all_authority_remains_denied() -> None:
    report = build_doctor_report(windows_snapshot())
    assert dict(report.authority) == AUTHORITY
    assert set(report.authority.values()) == {False}


def test_report_digest_recomputes() -> None:
    report = build_doctor_report(windows_snapshot())
    assert report.report_digest == sha256(
        canonical_bytes(report.body_without_digest())
    )


def test_json_does_not_serialize_full_environment() -> None:
    snapshot = windows_snapshot(
        environment={
            "LOCALAPPDATA": "C:/Safe",
            "SECRET_TOKEN": "must-not-appear",
        }
    )
    rendered = render_doctor(snapshot, as_json=True)
    assert "must-not-appear" not in rendered
    assert "SECRET_TOKEN" not in rendered


def test_human_and_json_rendering_are_repeatable() -> None:
    snapshot = windows_snapshot()
    assert render_doctor(snapshot, as_json=False) == render_doctor(
        snapshot,
        as_json=False,
    )
    assert render_doctor(snapshot, as_json=True) == render_doctor(
        snapshot,
        as_json=True,
    )


def test_stage_zero_hash_bindings_are_present() -> None:
    assert len(STAGE_0_QUALIFICATION_RECORD_SHA256) == 64
    assert len(STAGE_0_VERIFIER_MANIFEST_SHA256) == 64

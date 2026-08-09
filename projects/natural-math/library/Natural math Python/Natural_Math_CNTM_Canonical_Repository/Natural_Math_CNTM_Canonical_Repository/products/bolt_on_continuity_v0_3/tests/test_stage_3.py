from __future__ import annotations

import json
import subprocess

import pytest

from bolt_on.discovery import (
    DISCOVERY_VECTOR,
    ContainerCandidate,
    DiscoveryError,
    inspect_and_enroll,
    parse_discovery,
    select,
)

CID = "a" * 64


def completed(args, stdout: str, code: int = 0):
    return subprocess.CompletedProcess(args, code, stdout=stdout, stderr="")


def test_parse_discovery_normalizes_and_sorts():
    other = "0" * 64
    text = "\n".join([
        json.dumps({"ID": CID, "Names": "z", "Image": "img:z", "State": "RUNNING", "Status": "Up"}),
        json.dumps({"ID": other, "Names": "a", "Image": "img:a", "State": "exited", "Status": "Exited"}),
    ])
    items = parse_discovery(text)
    assert [item.container_id for item in items] == [other, CID]
    assert items[1].state == "running"


def test_rejects_truncated_and_duplicate_ids():
    with pytest.raises(DiscoveryError, match="INVALID_CONTAINER_ID"):
        parse_discovery(json.dumps({"ID": "abc", "Names": "x", "Image": "i", "State": "running", "Status": "Up"}))
    line = json.dumps({"ID": CID, "Names": "x", "Image": "i", "State": "running", "Status": "Up"})
    with pytest.raises(DiscoveryError, match="DUPLICATE_SUBJECT"):
        parse_discovery(line + "\n" + line)


def test_selection_requires_exact_id_and_repeat_confirmation():
    candidate = ContainerCandidate(CID, "x", "img", "running", "Up")
    assert select((candidate,), CID, CID) is candidate
    with pytest.raises(DiscoveryError, match="INVALID_SELECTION"):
        select((candidate,), CID[:12], CID[:12])
    with pytest.raises(DiscoveryError, match="CONFIRMATION_MISMATCH"):
        select((candidate,), CID, "b" * 64)


def test_inspect_vector_and_deterministic_digest():
    candidate = ContainerCandidate(CID, "x", "img", "running", "Up")
    calls = []
    def runner(vector, timeout):
        calls.append((tuple(vector), timeout))
        return completed(vector, json.dumps([{"Id": CID, "Name": "/renamed", "Platform": "linux"}]))
    first = inspect_and_enroll(candidate, runner)
    second = inspect_and_enroll(candidate, runner)
    assert calls[0][0] == ("docker", "inspect", CID)
    assert first == second
    assert first.display_name == "renamed"
    assert len(first.enrollment_digest) == 64


def test_inspection_identity_and_platform_fail_closed():
    candidate = ContainerCandidate(CID, "x", "img", "running", "Up")
    def wrong_id(vector, timeout):
        return completed(vector, json.dumps([{"Id": "b" * 64, "Platform": "linux"}]))
    with pytest.raises(DiscoveryError, match="INSPECTION_MISMATCH"):
        inspect_and_enroll(candidate, wrong_id)
    def windows(vector, timeout):
        return completed(vector, json.dumps([{"Id": CID, "Platform": "windows"}]))
    with pytest.raises(DiscoveryError, match="UNSUPPORTED_PLATFORM"):
        inspect_and_enroll(candidate, windows)


def test_discovery_vector_is_fixed():
    assert DISCOVERY_VECTOR == ("docker", "container", "ls", "--all", "--no-trunc", "--format", "{{json .}}")

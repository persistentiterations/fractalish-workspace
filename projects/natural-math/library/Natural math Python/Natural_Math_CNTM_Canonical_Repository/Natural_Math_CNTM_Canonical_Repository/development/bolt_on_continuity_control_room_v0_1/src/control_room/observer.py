"""Read-only, exactly-one-container observation boundary."""
from __future__ import annotations
from abc import ABC, abstractmethod
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Mapping

SOURCE_INTERFACE = "Docker CLI inspect (read-only)"
class ObservationError(RuntimeError): pass

class ContainerObserver(ABC):
    source_interface = SOURCE_INTERFACE
    @abstractmethod
    def inspect_one(self, subject: str) -> Mapping[str, Any]:
        """Return one Docker inspection object without changing the subject."""
    def source_command(self, subject: str) -> str:
        return f"docker inspect --type container {subject}"

class DockerCliObserver(ContainerObserver):
    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or shutil.which("docker") or "docker"
    def inspect_one(self, subject: str) -> Mapping[str, Any]:
        if not subject or subject.strip() != subject:
            raise ObservationError("one non-empty container name or ID is required")
        try:
            completed = subprocess.run([self.executable, "inspect", "--type", "container", subject], check=False, capture_output=True, text=True, timeout=15)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise ObservationError(f"Docker observation unavailable: {exc}") from exc
        if completed.returncode != 0:
            raise ObservationError(completed.stderr.strip() or "docker inspect failed")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ObservationError("Docker returned invalid inspection JSON") from exc
        if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
            raise ObservationError("Docker did not return exactly one container inspection")
        return payload[0]

class FixtureObserver(ContainerObserver):
    source_interface = "Retained Docker inspect fixture"
    def __init__(self, fixture: Path) -> None: self.fixture = fixture
    def inspect_one(self, subject: str) -> Mapping[str, Any]:
        payload = json.loads(self.fixture.read_text(encoding="utf-8"))
        item = payload[0] if isinstance(payload, list) and len(payload) == 1 else payload
        if not isinstance(item, dict): raise ObservationError("fixture must contain exactly one inspection object")
        return item
    def source_command(self, subject: str) -> str: return "retained Docker inspect fixture"

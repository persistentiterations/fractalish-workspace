"""Narrow observation-only Docker adapter boundary."""

from dataclasses import dataclass
from typing import Protocol, Tuple

from .core import ContainerIdentity


@dataclass(frozen=True)
class DockerEnvironment:
    available: bool
    engine_version: str | None
    detail: str


@dataclass(frozen=True)
class ContainerSummary:
    identity: ContainerIdentity
    name: str
    state: str
    compose_project: str | None = None
    compose_service: str | None = None


class DockerObservationAdapter(Protocol):
    def check_environment(self) -> DockerEnvironment: ...
    def list_containers(self) -> Tuple[ContainerSummary, ...]: ...
    def inspect_container(self, identity: ContainerIdentity) -> ContainerSummary: ...


@dataclass(frozen=True)
class FakeDockerObservationAdapter:
    environment: DockerEnvironment
    containers: Tuple[ContainerSummary, ...] = ()

    def check_environment(self) -> DockerEnvironment:
        return self.environment

    def list_containers(self) -> Tuple[ContainerSummary, ...]:
        return tuple(sorted(self.containers, key=lambda item: item.identity.full_id))

    def inspect_container(self, identity: ContainerIdentity) -> ContainerSummary:
        for container in self.list_containers():
            if container.identity == identity:
                return container
        raise KeyError(identity.full_id)

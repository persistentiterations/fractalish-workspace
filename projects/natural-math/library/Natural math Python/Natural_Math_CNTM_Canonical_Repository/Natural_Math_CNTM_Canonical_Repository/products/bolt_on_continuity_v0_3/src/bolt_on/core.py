"""Core Stage 0 contracts."""

from dataclasses import dataclass
from enum import Enum


class ContractError(ValueError):
    """Raised when a Stage 0 contract is violated."""


class AuthorityClass(str, Enum):
    OBSERVATION_ONLY = "OBSERVATION_ONLY"


@dataclass(frozen=True)
class ContainerIdentity:
    full_id: str

    def __post_init__(self) -> None:
        value = self.full_id.lower()
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ContractError("container identity must be an exact 64-character hexadecimal ID")
        object.__setattr__(self, "full_id", value)

"""Side-effect-free configuration model."""

from dataclasses import dataclass, field
from typing import Tuple

from .core import AuthorityClass, ContractError


@dataclass(frozen=True)
class ProductConfiguration:
    schema_version: int = 1
    product_version: str = "0.3.0.dev0"
    observation_only: bool = True
    telemetry_enabled: bool = False
    enabled_modules: Tuple[str, ...] = field(default_factory=tuple)
    authority_class: AuthorityClass = AuthorityClass.OBSERVATION_ONLY

    def validate(self) -> None:
        if self.schema_version != 1:
            raise ContractError("unsupported configuration schema")
        if not self.observation_only:
            raise ContractError("Stage 0 requires observation-only mode")
        if self.telemetry_enabled:
            raise ContractError("Stage 0 telemetry must remain disabled")
        if self.enabled_modules:
            raise ContractError("Stage 0 modules must remain disabled")
        if self.authority_class is not AuthorityClass.OBSERVATION_ONLY:
            raise ContractError("unsupported authority class")

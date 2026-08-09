"""Disabled-by-default first-party module contracts."""

from dataclasses import dataclass
from typing import Dict, Tuple

from .core import AuthorityClass, ContractError


@dataclass(frozen=True)
class ModuleDeclaration:
    module_id: str
    module_version: str
    contract_version: int
    authority_class: AuthorityClass = AuthorityClass.OBSERVATION_ONLY
    default_enabled: bool = False
    dependencies: Tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.module_id or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for ch in self.module_id):
            raise ContractError("invalid module ID")
        if self.default_enabled:
            raise ContractError("Stage 0 modules must be disabled by default")
        if self.authority_class is not AuthorityClass.OBSERVATION_ONLY:
            raise ContractError("module cannot expand Stage 0 authority")


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: Dict[str, ModuleDeclaration] = {}

    def register(self, declaration: ModuleDeclaration) -> None:
        declaration.validate()
        if declaration.module_id in self._modules:
            raise ContractError("duplicate module ID")
        self._modules[declaration.module_id] = declaration

    def declarations(self) -> Tuple[ModuleDeclaration, ...]:
        return tuple(self._modules[key] for key in sorted(self._modules))

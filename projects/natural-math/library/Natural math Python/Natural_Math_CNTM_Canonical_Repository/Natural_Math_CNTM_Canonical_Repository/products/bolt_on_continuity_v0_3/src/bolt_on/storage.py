"""Storage boundary definitions.

SQLite is an indexed operational store, never the sole receipt authority.
"""

from typing import Protocol


class OperationalStore(Protocol):
    def schema_version(self) -> int:
        """Return the active migration version."""

    def close(self) -> None:
        """Release local resources."""

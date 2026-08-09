"""Canonical receipt primitives independent of SQLite."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


@dataclass(frozen=True)
class CanonicalReceipt:
    receipt_type: str
    schema_version: int
    payload: Mapping[str, Any]

    def body(self) -> dict[str, Any]:
        return {"payload": dict(self.payload), "receipt_type": self.receipt_type, "schema_version": self.schema_version}

    def digest(self) -> str:
        return sha256_hex(self.body())

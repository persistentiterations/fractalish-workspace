#!/usr/bin/env python3
"""
Guardian -- Code Intake Checkpoint
==================================

A manifest-first static intake gate for Python files.

This is a working proof-of-concept, not a complete sandbox or malware scanner.
Guardian never executes the scanned file. It produces a result slip and appends
that slip to a hash-chained ledger.

Exit codes:
    0 = LET IN
    2 = HOLD
    3 = REJECT
    4 = SCAN ERROR
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


# =============================================================================
# CORE TYPES
# =============================================================================

class RiskLabel(str, Enum):
    ON_TARGET = "On Target"
    CAUTION = "Caution"
    LIMITED = "Limited"
    SERIOUS = "Serious"
    FAILED = "Failed"


class EvidenceStatus(str, Enum):
    BACKED = "Backed"
    UNCLEAR = "Unclear"
    CONTRADICTED = "Contradicted"


class Decision(str, Enum):
    PROCEED = "Proceed"
    PAUSE = "Pause"
    REVERSE = "Reverse"


class ProcessState(str, Enum):
    EXTEND = "Extend"
    SENSE = "Sense"
    RESTRICT = "Restrict"


class IntakeOutcome(str, Enum):
    LET_IN = "Let In"
    HOLD = "Hold"
    REJECT = "Reject"


@dataclass(frozen=True)
class ManifestIssue:
    code: str
    message: str
    severity: str


@dataclass(frozen=True)
class ChecklistItem:
    id: str
    description: str
    severity: str
    check_type: str
    target_value: Any


@dataclass(frozen=True)
class ChecklistResult:
    item_id: str
    description: str
    severity: str
    satisfied: bool
    actual_value: Any
    detail: str


@dataclass(frozen=True)
class ResultSlip:
    schema_version: str
    slip_id: str
    timestamp: str
    policy_name: str
    policy_version: str
    file_name: str
    file_path: str
    file_size: int
    file_fingerprint: str
    manifest: Dict[str, Any]
    item_results: List[Dict[str, Any]]
    risk_label: str
    evidence_status: str
    decision: str
    process_state: str
    intake_outcome: str
    caveats: List[str]
    previous_slip_hash: str
    slip_fingerprint: str
    slip_signature: str


# =============================================================================
# MANIFEST
# =============================================================================

class ManifestParser:
    BEGIN_MARKER = "# --- MANIFEST BEGIN ---"
    END_MARKER = "# --- MANIFEST END ---"
    MAX_SCAN_LINES = 80
    REQUIRED_FIELDS = ("name", "version", "purpose", "dependencies")
    ALLOWED_FIELDS = frozenset(REQUIRED_FIELDS)
    KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
    VERSION_PATTERN = re.compile(
        r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9][A-Za-z0-9.-]*)?$"
    )
    DEPENDENCY_PATTERN = re.compile(
        r"^[A-Za-z_][A-Za-z0-9_.-]*(?:\[[A-Za-z0-9_,.-]+\])?$"
    )

    @classmethod
    def parse(cls, file_path: Path) -> Tuple[Dict[str, str], List[ManifestIssue]]:
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return {}, [
                ManifestIssue(
                    "manifest_invalid_encoding",
                    "File is not valid UTF-8 text",
                    "reject",
                )
            ]
        except OSError as exc:
            return {}, [
                ManifestIssue(
                    "manifest_read_error",
                    f"Could not read file: {exc}",
                    "reject",
                )
            ]
        return cls.parse_text(text)

    @classmethod
    def parse_text(cls, text: str) -> Tuple[Dict[str, str], List[ManifestIssue]]:
        issues: List[ManifestIssue] = []
        manifest: Dict[str, str] = {}
        lines = text.splitlines()[: cls.MAX_SCAN_LINES]

        begins = [
            index for index, line in enumerate(lines)
            if line.strip() == cls.BEGIN_MARKER
        ]
        ends = [
            index for index, line in enumerate(lines)
            if line.strip() == cls.END_MARKER
        ]

        if not begins and not ends:
            return {}, [
                ManifestIssue(
                    "manifest_missing",
                    f"No canonical manifest block found in first {cls.MAX_SCAN_LINES} lines",
                    "hold",
                )
            ]

        if len(begins) != 1:
            issues.append(
                ManifestIssue(
                    "manifest_begin_count",
                    f"Expected exactly one begin marker; found {len(begins)}",
                    "reject",
                )
            )
        if len(ends) != 1:
            issues.append(
                ManifestIssue(
                    "manifest_end_count",
                    f"Expected exactly one end marker; found {len(ends)}",
                    "reject",
                )
            )
        if issues:
            return {}, issues

        begin_index, end_index = begins[0], ends[0]
        if end_index <= begin_index:
            return {}, [
                ManifestIssue(
                    "manifest_marker_order",
                    "Manifest end marker must appear after the begin marker",
                    "reject",
                )
            ]

        block = lines[begin_index + 1 : end_index]
        if not block:
            return {}, [
                ManifestIssue("manifest_empty", "Manifest block is empty", "reject")
            ]

        for line_number, raw in enumerate(block, start=begin_index + 2):
            stripped = raw.strip()

            if not stripped:
                issues.append(
                    ManifestIssue(
                        "manifest_blank_line",
                        f"Blank line inside manifest at line {line_number}",
                        "reject",
                    )
                )
                continue

            if not stripped.startswith("#"):
                issues.append(
                    ManifestIssue(
                        "manifest_uncommented_line",
                        f"Manifest line {line_number} is not a Python comment",
                        "reject",
                    )
                )
                continue

            content = stripped[1:].strip()
            if not content or ":" not in content:
                issues.append(
                    ManifestIssue(
                        "manifest_malformed_line",
                        f"Malformed manifest line {line_number}: {content or '<empty>'}",
                        "reject",
                    )
                )
                continue

            key, value = [part.strip() for part in content.split(":", 1)]

            if not cls.KEY_PATTERN.fullmatch(key):
                issues.append(
                    ManifestIssue(
                        "manifest_invalid_key",
                        f"Invalid manifest key at line {line_number}: {key!r}",
                        "reject",
                    )
                )
                continue

            if key not in cls.ALLOWED_FIELDS:
                issues.append(
                    ManifestIssue(
                        "manifest_unknown_field",
                        f"Unknown manifest field at line {line_number}: {key}",
                        "reject",
                    )
                )
                continue

            if key in manifest:
                issues.append(
                    ManifestIssue(
                        "manifest_duplicate_field",
                        f"Duplicate manifest field at line {line_number}: {key}",
                        "reject",
                    )
                )
                continue

            if not value:
                issues.append(
                    ManifestIssue(
                        "manifest_empty_value",
                        f"Manifest field {key!r} has an empty value",
                        "reject",
                    )
                )
                continue

            manifest[key] = value

        missing = [field for field in cls.REQUIRED_FIELDS if field not in manifest]
        if missing:
            issues.append(
                ManifestIssue(
                    "manifest_missing_fields",
                    "Missing required manifest fields: " + ", ".join(missing),
                    "reject",
                )
            )

        if (
            "version" in manifest
            and not cls.VERSION_PATTERN.fullmatch(manifest["version"])
        ):
            issues.append(
                ManifestIssue(
                    "manifest_invalid_version",
                    "Manifest version must use semantic form such as 1.0.0",
                    "reject",
                )
            )

        if "dependencies" in manifest:
            raw_dependencies = manifest["dependencies"].strip()
            normalized = raw_dependencies.lower()
            reserved = {"none", "stdlib", "standard library"}

            if normalized not in reserved:
                dependencies = [
                    item.strip() for item in raw_dependencies.split(",")
                ]
                mixed_reserved = [
                    item for item in dependencies if item.lower() in reserved
                ]
                invalid = [
                    item for item in dependencies
                    if not item or not cls.DEPENDENCY_PATTERN.fullmatch(item)
                ]

                if mixed_reserved:
                    issues.append(
                        ManifestIssue(
                            "manifest_reserved_dependency_mixed",
                            "Reserved dependency values must appear alone: "
                            + ", ".join(repr(item) for item in mixed_reserved),
                            "reject",
                        )
                    )

                if invalid:
                    issues.append(
                        ManifestIssue(
                            "manifest_invalid_dependencies",
                            "Invalid dependency declaration(s): "
                            + ", ".join(repr(item) for item in invalid),
                            "reject",
                        )
                    )

        return manifest, issues


# =============================================================================
# STATIC ANALYSIS
# =============================================================================

class StaticAnalyzer:
    """
    Lightweight deterministic Python AST analyzer.

    It detects a documented set of direct and simply-indirected operations.
    It does not claim complete data-flow, control-flow, malware, or runtime
    behavior analysis.
    """

    NETWORK_MODULES = {
        "aiohttp", "asyncio", "azure", "boto3", "botocore", "dns", "ftplib",
        "google", "grpc", "http", "httpx", "imaplib", "paramiko", "poplib",
        "requests", "smtplib", "socket", "ssl", "telnetlib", "urllib",
        "websocket", "websockets", "xmlrpc",
    }

    DANGEROUS_FULL_NAMES = {
        "builtins.compile", "builtins.eval", "builtins.exec",
        "builtins.__import__", "marshal.loads", "pickle.load", "pickle.loads",
        "subprocess.call", "subprocess.check_call", "subprocess.check_output",
        "subprocess.getoutput", "subprocess.getstatusoutput",
        "subprocess.Popen", "subprocess.run",
        "os.system", "os.popen", "os.posix_spawn", "os.posix_spawnp",
        "os.spawnl", "os.spawnle", "os.spawnlp", "os.spawnlpe",
        "os.spawnv", "os.spawnve", "os.spawnvp", "os.spawnvpe",
        "os.execl", "os.execle", "os.execlp", "os.execlpe",
        "os.execv", "os.execve", "os.execvp", "os.execvpe",
    }

    DIRECT_DYNAMIC_NAMES = {"compile", "eval", "exec", "__import__"}

    FILE_WRITE_METHODS = {
        "write_text", "write_bytes", "touch", "mkdir", "rename", "replace",
        "unlink", "rmdir", "symlink_to", "hardlink_to",
    }

    FILE_MUTATION_FULL_NAMES = {
        "os.write", "os.remove", "os.unlink", "os.rename", "os.replace",
        "os.mkdir", "os.makedirs", "os.rmdir", "os.removedirs",
        "shutil.copy", "shutil.copy2", "shutil.copyfile", "shutil.copytree",
        "shutil.move", "shutil.rmtree",
    }

    SECRET_PATTERNS = {
        "aws_access_key_id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,255}\b"),
        "slack_token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
        "stripe_secret_key": re.compile(
            r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b"
        ),
        "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
        "jwt": re.compile(
            r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\."
            r"[A-Za-z0-9_-]{5,}\b"
        ),
        "database_url_with_credentials": re.compile(
            r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://"
            r"[^/\s:@]+:[^/\s@]+@"
        ),
        "private_key": re.compile(
            r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"
        ),
        "generic_api_key": re.compile(
            r"""(?ix)
            \b(?:api[_-]?key|secret|token|password)\b
            \s*[:=]\s*
            (["'])(?=.{8,}\1)[^"' \r\n]+\1
            """
        ),
    }

    def __init__(self, file_path: Path, source: Optional[str] = None):
        self.file_path = file_path
        self.source = (
            source
            if source is not None
            else file_path.read_text(encoding="utf-8")
        )
        self.tree = ast.parse(self.source, filename=str(file_path))
        self.aliases: Dict[str, str] = {}
        self.from_imports: Dict[str, str] = {}
        self.import_roots: Set[str] = set()
        self.assigned_callables: Dict[str, str] = {}
        self._index_imports()
        self._index_simple_callable_assignments()

    def _index_imports(self) -> None:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    local = alias.asname or root
                    self.aliases[local] = alias.name
                    self.import_roots.add(root)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                root = module.split(".")[0] if module else ""
                if root:
                    self.import_roots.add(root)
                for alias in node.names:
                    local = alias.asname or alias.name
                    self.from_imports[local] = (
                        f"{module}.{alias.name}".strip(".")
                    )

    def _index_simple_callable_assignments(self) -> None:
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            resolved = self._resolve_expr_name(node.value)
            if resolved:
                self.assigned_callables[target.id] = resolved

    def _resolve_name(self, local_name: str) -> str:
        if local_name in self.from_imports:
            return self.from_imports[local_name]
        if local_name in self.aliases:
            return self.aliases[local_name]
        if local_name in self.assigned_callables:
            return self.assigned_callables[local_name]
        if local_name in self.DIRECT_DYNAMIC_NAMES:
            return f"builtins.{local_name}"
        return local_name

    def _resolve_expr_name(self, expression: ast.AST) -> str:
        if isinstance(expression, ast.Name):
            return self._resolve_name(expression.id)

        if isinstance(expression, ast.Attribute):
            parts = [expression.attr]
            value = expression.value
            while isinstance(value, ast.Attribute):
                parts.append(value.attr)
                value = value.value
            if isinstance(value, ast.Name):
                parts.append(self._resolve_name(value.id))
                return ".".join(reversed(parts))
            return ""

        if isinstance(expression, ast.Call):
            return self._resolve_getattr_target(expression)

        return ""

    @staticmethod
    def _constant_string(node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = StaticAnalyzer._constant_string(node.left)
            right = StaticAnalyzer._constant_string(node.right)
            if left is not None and right is not None:
                return left + right
        return None

    def _resolve_getattr_target(self, node: ast.Call) -> str:
        if not isinstance(node.func, ast.Name) or node.func.id != "getattr":
            return ""
        if len(node.args) < 2:
            return ""
        attribute = self._constant_string(node.args[1])
        if attribute is None:
            return ""
        base = self._resolve_expr_name(node.args[0])
        return f"{base}.{attribute}" if base else ""

    def _resolve_dynamic_import(self, node: ast.Call) -> str:
        function_name = self._resolve_expr_name(node.func)
        if function_name not in {
            "builtins.__import__", "__import__", "importlib.import_module"
        }:
            return ""
        if not node.args:
            return ""
        return self._constant_string(node.args[0]) or ""

    def _resolve_call_name(self, node: ast.Call) -> str:
        resolved = self._resolve_expr_name(node.func)
        if resolved:
            return resolved

        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Call)
        ):
            module = self._resolve_dynamic_import(node.func.value)
            if module:
                return f"{module}.{node.func.attr}"

        return ""

    def imports(self) -> List[str]:
        return sorted(self.import_roots)

    def find_network_access(self) -> List[str]:
        hits: Set[str] = {
            root for root in self.import_roots
            if root in self.NETWORK_MODULES
        }

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                module = self._resolve_dynamic_import(node)
                if module and module.split(".")[0] in self.NETWORK_MODULES:
                    hits.add(module)

        return sorted(hits)

    def find_process_or_dynamic_execution(self) -> List[str]:
        hits: Set[str] = set()

        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue

            call_name = self._resolve_call_name(node)

            if call_name in self.DANGEROUS_FULL_NAMES:
                hits.add(call_name)
            elif call_name.startswith("subprocess."):
                hits.add(call_name)
            elif call_name.startswith("os.exec") or call_name.startswith("os.spawn"):
                hits.add(call_name)

            module = self._resolve_dynamic_import(node)
            if module:
                hits.add(f"dynamic_import:{module}")

            getattr_target = self._resolve_getattr_target(node)
            if getattr_target in self.DANGEROUS_FULL_NAMES:
                hits.add(getattr_target)

        return sorted(hits)

    def find_file_writes(self) -> List[str]:
        hits: Set[str] = set()

        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue

            call_name = self._resolve_call_name(node)
            if isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
            else:
                method_name = (
                    call_name.rsplit(".", 1)[-1] if call_name else ""
                )

            if call_name in self.FILE_MUTATION_FULL_NAMES:
                hits.add(call_name)
                continue

            if method_name in self.FILE_WRITE_METHODS:
                hits.add(call_name or method_name)
                continue

            if (
                call_name not in {
                    "open", "builtins.open", "io.open", "os.fdopen",
                    "gzip.open", "bz2.open", "lzma.open",
                }
                and not call_name.endswith(".open")
            ):
                continue

            mode: Optional[str] = None
            if (
                len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                mode = node.args[1].value

            for keyword in node.keywords:
                if (
                    keyword.arg == "mode"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ):
                    mode = keyword.value.value

            if mode and any(flag in mode for flag in ("w", "a", "x", "+")):
                hits.add(f"{call_name}(mode={mode!r})")

        return sorted(hits)

    def find_secrets(self) -> List[str]:
        return sorted(
            name
            for name, pattern in self.SECRET_PATTERNS.items()
            if pattern.search(self.source)
        )

    def find_suspicious_obfuscation(self) -> List[str]:
        """
        Heuristic indicators only. These produce HOLD, not a claim of
        malicious behavior.
        """
        hits: Set[str] = set()

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                call_name = self._resolve_expr_name(node.func)

                if call_name in {"globals", "locals", "vars"}:
                    hits.add(f"namespace_introspection:{call_name}")

                if call_name in {
                    "base64.b64decode", "base64.decodebytes", "codecs.decode"
                }:
                    hits.add(f"encoded_payload_decode:{call_name}")

                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "getattr"
                    and len(node.args) >= 2
                    and self._constant_string(node.args[1]) is None
                ):
                    hits.add("dynamic_getattr")

                if call_name in {"builtins.chr", "chr"}:
                    hits.add("runtime_string_construction:chr")

            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitXor):
                hits.add("xor_expression")

            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value
                if (
                    len(value) >= 120
                    and re.fullmatch(r"[A-Za-z0-9+/=_-]+", value)
                ):
                    hits.add("long_encoded_string")

        return sorted(hits)


# =============================================================================
# POLICY AND SCORING
# =============================================================================

DEFAULT_POLICY: Dict[str, Any] = {
    "name": "CodeIntake_Security_Default",
    "version": "0.4.0",
    "description": "Manifest-first static policy with Stage 02 analyzer hardening",
    "limits": {
        "max_file_bytes": 1_000_000,
        "allowed_extensions": [".py"],
    },
    "checklist": [
        {
            "id": "manifest_present",
            "description": "A complete manifest block is present near the top of the file",
            "severity": "hard_hold",
            "check_type": "manifest_complete",
            "target_value": True,
        },
        {
            "id": "python_syntax",
            "description": "The file parses as valid Python",
            "severity": "hard_reject",
            "check_type": "python_syntax",
            "target_value": True,
        },
        {
            "id": "no_network",
            "description": "No network-capable modules are imported",
            "severity": "hard_reject",
            "check_type": "no_network",
            "target_value": True,
        },
        {
            "id": "no_file_writes",
            "description": "No direct file writes are detected",
            "severity": "hard_hold",
            "check_type": "no_file_writes",
            "target_value": True,
        },
        {
            "id": "no_process_execution",
            "description": "No subprocess, shell, eval, exec, compile, or dynamic import calls are detected",
            "severity": "hard_reject",
            "check_type": "no_process_execution",
            "target_value": True,
        },
        {
            "id": "dependencies_declared",
            "description": "Imported modules are declared in the manifest or are standard-library modules",
            "severity": "hard_hold",
            "check_type": "dependencies_declared",
            "target_value": True,
        },
        {
            "id": "no_secrets",
            "description": "No obvious hardcoded secrets or private keys are detected",
            "severity": "hard_reject",
            "check_type": "no_secrets",
            "target_value": True,
        },
        {
            "id": "no_suspicious_obfuscation",
            "description": "No simple suspicious obfuscation indicators are detected",
            "severity": "hard_hold",
            "check_type": "no_suspicious_obfuscation",
            "target_value": True,
        },
    ],
}


class PolicyEngine:
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy
        self.items = [ChecklistItem(**item) for item in policy["checklist"]]

    @staticmethod
    def _stdlib_modules() -> Set[str]:
        names = getattr(sys, "stdlib_module_names", None)
        if names is not None:
            return set(names)
        return {
            "argparse", "ast", "collections", "dataclasses", "datetime", "enum",
            "functools", "hashlib", "hmac", "io", "itertools", "json", "math",
            "os", "pathlib", "random", "re", "secrets", "sys", "typing",
        }

    def run(
        self,
        file_path: Path,
        manifest: Dict[str, str],
        manifest_issues: List[ManifestIssue],
        analyzer: Optional[StaticAnalyzer],
        syntax_error: Optional[str],
    ) -> List[ChecklistResult]:
        results: List[ChecklistResult] = []

        for item in self.items:
            satisfied = False
            actual: Any = None
            detail = "Unsupported check type"

            if item.check_type == "manifest_complete":
                satisfied = bool(manifest) and not manifest_issues
                actual = {"fields": sorted(manifest.keys()), "issues": [asdict(issue) for issue in manifest_issues]}
                detail = "Manifest is complete and schema-valid" if satisfied else "Manifest is absent or invalid"

            elif item.check_type == "python_syntax":
                satisfied = analyzer is not None and syntax_error is None
                actual = syntax_error
                detail = "Valid Python syntax" if satisfied else f"Python parse failed: {syntax_error}"

            elif item.check_type == "no_network":
                hits = analyzer.find_network_access() if analyzer else []
                satisfied = analyzer is not None and not hits
                actual = hits
                detail = "No network imports found" if satisfied else f"Network imports found: {', '.join(hits)}"

            elif item.check_type == "no_file_writes":
                hits = analyzer.find_file_writes() if analyzer else []
                satisfied = analyzer is not None and not hits
                actual = hits
                detail = "No direct file writes found" if satisfied else f"File writes found: {', '.join(hits)}"

            elif item.check_type == "no_process_execution":
                hits = analyzer.find_process_or_dynamic_execution() if analyzer else []
                satisfied = analyzer is not None and not hits
                actual = hits
                detail = "No process or dynamic execution found" if satisfied else (
                    "Process or dynamic execution found: " + ", ".join(hits)
                )

            elif item.check_type == "dependencies_declared":
                imports = analyzer.imports() if analyzer else []
                declared_raw = manifest.get("dependencies", "")
                declared = {
                    token.strip().split(".")[0]
                    for token in declared_raw.split(",")
                    if token.strip() and token.strip().lower() not in {"none", "stdlib", "standard library"}
                }
                stdlib = self._stdlib_modules()
                undeclared = sorted(
                    root for root in imports
                    if root not in stdlib and root not in declared
                )
                satisfied = analyzer is not None and not undeclared
                actual = {"imports": imports, "declared": sorted(declared), "undeclared": undeclared}
                detail = "Dependencies are declared" if satisfied else (
                    "Undeclared dependencies: " + ", ".join(undeclared)
                )

            elif item.check_type == "no_secrets":
                hits = analyzer.find_secrets() if analyzer else []
                satisfied = analyzer is not None and not hits
                actual = hits
                detail = "No obvious hardcoded secrets found" if satisfied else (
                    "Potential secrets found: " + ", ".join(hits)
                )

            elif item.check_type == "no_suspicious_obfuscation":
                hits = analyzer.find_suspicious_obfuscation() if analyzer else []
                satisfied = analyzer is not None and not hits
                actual = hits
                detail = (
                    "No simple suspicious obfuscation indicators found"
                    if satisfied
                    else "Suspicious obfuscation indicators found: "
                    + ", ".join(hits)
                )

            results.append(
                ChecklistResult(
                    item_id=item.id,
                    description=item.description,
                    severity=item.severity,
                    satisfied=satisfied,
                    actual_value=actual,
                    detail=detail,
                )
            )

        return results

    @staticmethod
    def classify(
        results: Sequence[ChecklistResult],
        caveats: Sequence[str],
    ) -> Tuple[RiskLabel, EvidenceStatus, Decision, ProcessState, IntakeOutcome]:
        failed = [result for result in results if not result.satisfied]
        reject_failures = [result for result in failed if result.severity == "hard_reject"]
        hold_failures = [result for result in failed if result.severity == "hard_hold"]

        if reject_failures:
            return (
                RiskLabel.FAILED,
                EvidenceStatus.CONTRADICTED,
                Decision.REVERSE,
                ProcessState.RESTRICT,
                IntakeOutcome.REJECT,
            )

        if hold_failures:
            return (
                RiskLabel.SERIOUS,
                EvidenceStatus.UNCLEAR,
                Decision.PAUSE,
                ProcessState.RESTRICT,
                IntakeOutcome.HOLD,
            )

        if caveats:
            return (
                RiskLabel.CAUTION,
                EvidenceStatus.UNCLEAR,
                Decision.PAUSE,
                ProcessState.SENSE,
                IntakeOutcome.HOLD,
            )

        return (
            RiskLabel.ON_TARGET,
            EvidenceStatus.BACKED,
            Decision.PROCEED,
            ProcessState.EXTEND,
            IntakeOutcome.LET_IN,
        )


# =============================================================================
# GUARDIAN
# =============================================================================

class Guardian:
    SCHEMA_VERSION = "1.0"

    def __init__(
        self,
        policy_path: Optional[Path] = None,
        ledger_path: Path = Path("guardian_ledger.jsonl"),
        signing_key: Optional[str] = None,
    ):
        self.ledger_path = ledger_path
        self.policy = self._load_policy(policy_path)
        self.signing_key = (signing_key or os.environ.get("GUARDIAN_HMAC_KEY", "")).encode("utf-8")
        self.previous_slip_hash = self._get_last_slip_hash()

    @staticmethod
    def _load_policy(policy_path: Optional[Path]) -> Dict[str, Any]:
        if policy_path is None:
            return DEFAULT_POLICY
        with policy_path.open("r", encoding="utf-8") as handle:
            policy = json.load(handle)
        if "name" not in policy or "version" not in policy or "checklist" not in policy:
            raise ValueError("Policy must contain name, version, and checklist")
        return policy

    def _get_last_slip_hash(self) -> str:
        if not self.ledger_path.exists():
            return "0" * 64

        last_hash = "0" * 64
        with self.ledger_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                last_hash = entry.get("slip", {}).get("slip_fingerprint", last_hash)
        return last_hash

    @staticmethod
    def _sha256_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _canonical_json(value: Dict[str, Any]) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def _fingerprint_slip(self, slip_dict: Dict[str, Any]) -> str:
        unsigned = dict(slip_dict)
        unsigned["slip_fingerprint"] = ""
        unsigned["slip_signature"] = ""
        return self._sha256_bytes(self._canonical_json(unsigned))

    def _sign_fingerprint(self, fingerprint: str) -> str:
        if not self.signing_key:
            return ""
        return hmac.new(self.signing_key, fingerprint.encode("ascii"), hashlib.sha256).hexdigest()

    def _preflight(self, file_path: Path) -> List[str]:
        issues = []
        limits = self.policy.get("limits", {})

        if not file_path.exists():
            issues.append("File does not exist")
            return issues
        if not file_path.is_file():
            issues.append("Path is not a regular file")
            return issues
        if file_path.is_symlink():
            issues.append("Symbolic links are not accepted")

        allowed_extensions = set(limits.get("allowed_extensions", [".py"]))
        if file_path.suffix.lower() not in allowed_extensions:
            issues.append(f"Extension {file_path.suffix!r} is not allowed")

        max_bytes = int(limits.get("max_file_bytes", 1_000_000))
        size = file_path.stat().st_size
        if size > max_bytes:
            issues.append(f"File size {size} exceeds policy limit {max_bytes}")

        return issues

    def scan(self, file_path: Path) -> ResultSlip:
        file_path = file_path.expanduser()
        preflight_issues = self._preflight(file_path)

        if preflight_issues and not file_path.exists():
            raise FileNotFoundError("; ".join(preflight_issues))

        raw = file_path.read_bytes()
        file_hash_before = self._sha256_bytes(raw)
        file_size = len(raw)

        source_text: Optional[str] = None
        decode_error: Optional[str] = None
        try:
            source_text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            decode_error = f"UnicodeDecodeError: {exc}"

        if source_text is None:
            manifest = {}
            manifest_issues = [
                ManifestIssue(
                    "manifest_invalid_encoding",
                    "File is not valid UTF-8 text",
                    "reject",
                )
            ]
        else:
            manifest, manifest_issues = ManifestParser.parse_text(source_text)

        analyzer: Optional[StaticAnalyzer] = None
        syntax_error: Optional[str] = decode_error
        if source_text is not None:
            try:
                analyzer = StaticAnalyzer(file_path, source=source_text)
            except SyntaxError as exc:
                syntax_error = f"SyntaxError: {exc}"

        policy_engine = PolicyEngine(self.policy)
        results = policy_engine.run(
            file_path=file_path,
            manifest=manifest,
            manifest_issues=manifest_issues,
            analyzer=analyzer,
            syntax_error=syntax_error,
        )

        caveats = list(preflight_issues) + [f"{issue.code}: {issue.message}" for issue in manifest_issues]

        risk, evidence, decision, state, outcome = policy_engine.classify(results, caveats)

        if any(issue.severity == "reject" for issue in manifest_issues):
            risk = RiskLabel.FAILED
            evidence = EvidenceStatus.CONTRADICTED
            decision = Decision.REVERSE
            state = ProcessState.RESTRICT
            outcome = IntakeOutcome.REJECT

        # Any preflight issue is at least HOLD; unsafe type/size/symlink becomes REJECT.
        if preflight_issues:
            risk = RiskLabel.FAILED
            evidence = EvidenceStatus.CONTRADICTED
            decision = Decision.REVERSE
            state = ProcessState.RESTRICT
            outcome = IntakeOutcome.REJECT

        timestamp = datetime.now(timezone.utc).isoformat()
        slip_id = f"guardian-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{secrets.token_hex(4)}"

        slip_dict: Dict[str, Any] = {
            "schema_version": self.SCHEMA_VERSION,
            "slip_id": slip_id,
            "timestamp": timestamp,
            "policy_name": self.policy["name"],
            "policy_version": self.policy["version"],
            "file_name": file_path.name,
            "file_path": str(file_path.resolve()),
            "file_size": file_size,
            "file_fingerprint": file_hash_before,
            "manifest": manifest,
            "item_results": [asdict(result) for result in results],
            "risk_label": risk.value,
            "evidence_status": evidence.value,
            "decision": decision.value,
            "process_state": state.value,
            "intake_outcome": outcome.value,
            "caveats": caveats,
            "previous_slip_hash": self.previous_slip_hash,
            "slip_fingerprint": "",
            "slip_signature": "",
        }

        fingerprint = self._fingerprint_slip(slip_dict)
        slip_dict["slip_fingerprint"] = fingerprint
        slip_dict["slip_signature"] = self._sign_fingerprint(fingerprint)

        slip = ResultSlip(**slip_dict)
        self._append_to_ledger(slip)
        self.previous_slip_hash = slip.slip_fingerprint
        return slip

    def _append_to_ledger(self, slip: ResultSlip) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "appended_at": datetime.now(timezone.utc).isoformat(),
            "slip": asdict(slip),
        }
        with self.ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

    def replay(self) -> Tuple[bool, List[str]]:
        if not self.ledger_path.exists():
            return True, ["Ledger is empty"]

        issues: List[str] = []
        expected_prev = "0" * 64

        with self.ledger_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as exc:
                    issues.append(f"Line {line_number}: invalid JSON: {exc}")
                    continue

                slip = entry.get("slip")
                if not isinstance(slip, dict):
                    issues.append(f"Line {line_number}: missing slip object")
                    continue

                stored_fp = slip.get("slip_fingerprint", "")
                stored_prev = slip.get("previous_slip_hash", "")

                if stored_prev != expected_prev:
                    issues.append(f"Line {line_number}: previous hash does not match chain")

                recomputed = self._fingerprint_slip(slip)
                if recomputed != stored_fp:
                    issues.append(f"Line {line_number}: slip fingerprint mismatch")

                stored_sig = slip.get("slip_signature", "")
                if self.signing_key:
                    expected_sig = self._sign_fingerprint(stored_fp)
                    if not hmac.compare_digest(expected_sig, stored_sig):
                        issues.append(f"Line {line_number}: HMAC signature mismatch")

                expected_prev = stored_fp

        return not issues, issues

    def ledger_summary(self) -> Dict[str, Any]:
        summary = {
            "total_entries": 0,
            "outcomes": {"Let In": 0, "Hold": 0, "Reject": 0},
            "risk_distribution": {
                "On Target": 0,
                "Caution": 0,
                "Limited": 0,
                "Serious": 0,
                "Failed": 0,
            },
            "ledger_file": str(self.ledger_path.resolve()),
            "hmac_enabled": bool(self.signing_key),
        }

        if not self.ledger_path.exists():
            return summary

        with self.ledger_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    slip = json.loads(line)["slip"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
                summary["total_entries"] += 1
                outcome = slip.get("intake_outcome")
                risk = slip.get("risk_label")
                if outcome in summary["outcomes"]:
                    summary["outcomes"][outcome] += 1
                if risk in summary["risk_distribution"]:
                    summary["risk_distribution"][risk] += 1

        return summary


# =============================================================================
# CLI
# =============================================================================

def print_slip(slip: ResultSlip) -> None:
    width = 78
    print("=" * width)
    print("GUARDIAN RESULT SLIP".center(width))
    print("=" * width)
    print(f"Slip ID:          {slip.slip_id}")
    print(f"Timestamp:        {slip.timestamp}")
    print(f"Policy:           {slip.policy_name} v{slip.policy_version}")
    print(f"File:             {slip.file_name}")
    print(f"File SHA-256:     {slip.file_fingerprint}")
    print("-" * width)
    for result in slip.item_results:
        status = "PASS" if result["satisfied"] else "FAIL"
        print(f"[{status}] {result['item_id']}: {result['detail']}")
    print("-" * width)
    print(f"Risk label:       {slip.risk_label}")
    print(f"Evidence status:  {slip.evidence_status}")
    print(f"Decision:         {slip.decision}")
    print(f"Process state:    {slip.process_state}")
    print(f"INTAKE OUTCOME:   {slip.intake_outcome.upper()}")
    if slip.caveats:
        print("-" * width)
        print("Caveats:")
        for caveat in slip.caveats:
            print(f"  - {caveat}")
    print("-" * width)
    print(f"Previous hash:    {slip.previous_slip_hash}")
    print(f"Slip fingerprint: {slip.slip_fingerprint}")
    print(f"HMAC signature:   {slip.slip_signature or '(not enabled)'}")
    print("=" * width)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Guardian code intake checkpoint")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("guardian_ledger.jsonl"),
        help="Path to the append-only JSONL ledger",
    )
    parser.add_argument(
        "--hmac-key",
        default=None,
        help="Optional HMAC key. Prefer the GUARDIAN_HMAC_KEY environment variable.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a Python file")
    scan_parser.add_argument("file", type=Path)
    scan_parser.add_argument("--policy", type=Path, default=None)
    scan_parser.add_argument("--json", action="store_true", help="Print the slip as JSON")

    subparsers.add_parser("ledger", help="Show ledger summary")
    subparsers.add_parser("replay", help="Verify the ledger chain and optional HMAC signatures")

    init_parser = subparsers.add_parser("init-policy", help="Write the default policy to disk")
    init_parser.add_argument("--out", type=Path, default=Path("guardian_policy.json"))

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-policy":
        args.out.write_text(json.dumps(DEFAULT_POLICY, indent=2), encoding="utf-8")
        print(f"Default policy written to {args.out}")
        return 0

    guardian = Guardian(
        policy_path=getattr(args, "policy", None),
        ledger_path=args.ledger,
        signing_key=args.hmac_key,
    )

    if args.command == "scan":
        try:
            slip = guardian.scan(args.file)
        except Exception as exc:
            print(f"Guardian scan error: {exc}", file=sys.stderr)
            return 4

        if args.json:
            print(json.dumps(asdict(slip), indent=2, ensure_ascii=False))
        else:
            print_slip(slip)

        if slip.intake_outcome == IntakeOutcome.LET_IN.value:
            return 0
        if slip.intake_outcome == IntakeOutcome.HOLD.value:
            return 2
        return 3

    if args.command == "ledger":
        print(json.dumps(guardian.ledger_summary(), indent=2))
        return 0

    if args.command == "replay":
        valid, issues = guardian.replay()
        if valid:
            print("Ledger replay passed. Chain integrity confirmed.")
            if issues:
                for issue in issues:
                    print(issue)
            return 0
        print("Ledger replay failed.")
        for issue in issues:
            print(f"- {issue}")
        return 1

    parser.error("Unknown command")
    return 4


if __name__ == "__main__":
    raise SystemExit(main())

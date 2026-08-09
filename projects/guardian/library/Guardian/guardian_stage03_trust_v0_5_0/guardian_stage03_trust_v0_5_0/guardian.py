#!/usr/bin/env python3
"""
Guardian -- Code Intake Checkpoint
==================================

A manifest-first static intake gate for Python source files.

Stage 03 adds trust infrastructure around the frozen Stage 02C analyzer:
strict policy validation, policy fingerprints, a versioned result-slip schema,
atomic locked ledger transactions, explicit unsigned developer mode, and a
formal threat model.

Guardian never executes the scanned file.

Exit codes:
    0 = LET IN / command success
    1 = verification failure
    2 = HOLD
    3 = REJECT
    4 = SCAN OR USAGE ERROR
    5 = POLICY ERROR
    6 = LEDGER ERROR
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
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple


ENGINE_VERSION = "0.5.0"
SLIP_SCHEMA_NAME = "guardian-result-slip"
SLIP_SCHEMA_VERSION = "1.0"
POLICY_SCHEMA_VERSION = "1.0"
ZERO_HASH = "0" * 64
SECURITY_NOTICE = (
    "Guardian may miss harmful, unsafe, or newly developed content. "
    "It helps identify risks based on checks performed at the time of scanning, "
    "but results are informational only and do not guarantee safety. "
    "A pass does not mean the content is completely safe."
)


class GuardianError(Exception):
    """Base class for Guardian operational failures."""


class PolicyValidationError(GuardianError):
    """Raised when a policy is missing, malformed, or unsupported."""


class LedgerIntegrityError(GuardianError):
    """Raised when a ledger cannot be safely verified or appended."""


class UnsignedModeError(GuardianError):
    """Raised when an append is attempted without signing or explicit dev mode."""


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
    slip_schema_name: str
    slip_schema_version: str
    engine_version: str
    slip_id: str
    timestamp: str
    policy_schema_version: str
    policy_name: str
    policy_version: str
    policy_fingerprint: str
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
    unsigned_dev_mode: bool
    previous_slip_hash: str
    slip_fingerprint: str
    slip_signature: str


# =============================================================================
# FROZEN MANIFEST AND ANALYZER (STAGE 02C)
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

class StaticAnalyzer(ast.NodeVisitor):
    # Scope-aware lightweight Python AST analyzer.
    # Unknown dynamic behavior is surfaced as HOLD evidence.

    NETWORK_MODULES = {
        "aiohttp", "asyncio", "azure", "boto3", "botocore", "dns", "ftplib",
        "google", "grpc", "http", "httpx", "imaplib", "paramiko", "paho",
        "poplib", "pycurl", "requests", "smtplib", "socket", "ssl", "telnetlib",
        "urllib", "urllib3", "websocket", "websocket_client", "websockets", "xmlrpc",
    }
    DANGEROUS_LOADER_MODULES = {
        "ctypes", "cffi", "zipimport", "importlib.machinery",
    }
    DANGEROUS_FULL_NAMES = {
        "builtins.compile", "builtins.eval", "builtins.exec", "builtins.__import__",
        "marshal.loads", "pickle.load", "pickle.loads",
        "subprocess.call", "subprocess.check_call", "subprocess.check_output",
        "subprocess.getoutput", "subprocess.getstatusoutput", "subprocess.Popen",
        "subprocess.run", "asyncio.create_subprocess_exec",
        "asyncio.create_subprocess_shell", "os.system", "os.popen",
        "os.posix_spawn", "os.posix_spawnp", "os.spawnl", "os.spawnle",
        "os.spawnlp", "os.spawnlpe", "os.spawnv", "os.spawnve", "os.spawnvp",
        "os.spawnvpe", "os.execl", "os.execle", "os.execlp", "os.execlpe",
        "os.execv", "os.execve", "os.execvp", "os.execvpe",
        "multiprocessing.Process", "multiprocessing.Pool",
    }
    DANGEROUS_METHOD_NAMES = {
        "system", "popen", "execv", "execve", "execvp", "execvpe", "execl",
        "execle", "execlp", "execlpe", "spawnl", "spawnle", "spawnlp",
        "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "run", "Popen",
        "call", "check_call", "check_output", "eval", "exec", "compile",
        "__import__", "CreateProcess", "CreateProcessA", "CreateProcessW",
        "ShellExecute", "ShellExecuteA", "ShellExecuteW", "WinExec",
    }
    DIRECT_DYNAMIC_NAMES = {"compile", "eval", "exec", "__import__"}
    FILE_MUTATION_FULL_NAMES = {
        "os.write", "os.remove", "os.unlink", "os.rename", "os.replace",
        "os.mkdir", "os.makedirs", "os.rmdir", "os.removedirs",
        "shutil.copy", "shutil.copy2", "shutil.copyfile", "shutil.copytree",
        "shutil.move", "shutil.rmtree",
    }
    PATH_WRITE_METHODS = {
        "write_text", "write_bytes", "touch", "mkdir", "rename", "replace",
        "unlink", "rmdir", "symlink_to", "hardlink_to",
    }
    OPEN_FUNCTIONS = {
        "open", "builtins.open", "io.open", "os.fdopen", "gzip.open",
        "bz2.open", "lzma.open",
    }
    SECRET_PATTERNS = {
        "aws_access_key_id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,255}\b"),
        "slack_token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
        "stripe_secret_key": re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b"),
        "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
        "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b"),
        "database_url_with_credentials": re.compile(
            r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^/\s:@]+:[^/\s@]+@"
        ),
        "private_key": re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "generic_api_key": re.compile(
            r"(?ix)\\b(?:api[_-]?key|secret|token|password)\\b\\s*[:=]\\s*([\"'])(?=.{8,}\\1)[^\"' \r\n]+\\1"
        ),
    }

    def __init__(self, file_path: Path, source: Optional[str] = None):
        self.file_path = file_path
        self.source = source if source is not None else file_path.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source, filename=str(file_path))
        self.scope_stack: List[Dict[str, str]] = [{}]
        self.container_stack: List[Dict[str, Any]] = [{}]
        self.class_stack: List[str] = []
        self.import_roots: Set[str] = set()
        self.process_hits: Set[str] = set()
        self.network_hits: Set[str] = set()
        self.file_write_hits: Set[str] = set()
        self.obfuscation_hits: Set[str] = set()
        self.star_imports: Set[str] = set()
        self.finding_lines: Dict[str, Set[int]] = {}
        self.visit(self.tree)

    def _record(self, bucket: Set[str], finding: str, node: ast.AST) -> None:
        bucket.add(finding)
        self.finding_lines.setdefault(finding, set()).add(getattr(node, "lineno", 0))

    def _normalize(self, name: str) -> str:
        if name == "__builtins__": return "builtins"
        if name.startswith("__builtins__."): return "builtins." + name[len("__builtins__."):]
        return name

    def _lookup(self, name: str) -> str:
        name=self._normalize(name)
        for scope in reversed(self.scope_stack):
            if name in scope:
                target=scope[name]
                if target == name: return target
                return self._lookup(target) if target and target != name else target
        if name in self.DIRECT_DYNAMIC_NAMES:
            return f"builtins.{name}"
        return name

    def _lookup_container(self, name: str) -> Any:
        for scope in reversed(self.container_stack):
            if name in scope: return scope[name]
        return None

    @classmethod
    def _constant_strings(cls, node: ast.AST) -> Set[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left,right=cls._constant_strings(node.left),cls._constant_strings(node.right)
            return {a+b for a in left for b in right}
        if isinstance(node, ast.JoinedStr):
            parts=[]
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value,str): parts.append({value.value})
                else: return set()
            result={""}
            for part in parts: result={a+b for a in result for b in part}
            return result
        if isinstance(node, ast.IfExp):
            return cls._constant_strings(node.body) | cls._constant_strings(node.orelse)
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
            vals=cls._constant_strings(node.value)
            if isinstance(node.slice.step, ast.UnaryOp) and isinstance(node.slice.step.op, ast.USub) and isinstance(node.slice.step.operand, ast.Constant) and node.slice.step.operand.value==1:
                return {v[::-1] for v in vals}
        return set()

    def _resolve_subscript(self, node: ast.Subscript) -> str:
        keys=self._constant_strings(node.slice)
        if not keys and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
            keys={str(node.slice.value)}
        if not keys: return ""
        base=self._resolve_expr(node.value)
        key=next(iter(keys)) if len(keys)==1 else ""
        if base == "sys.modules" and key: return key
        if base in {"builtins", "__builtins__"} and key: return self._normalize(f"builtins.{key}")
        if isinstance(node.value, ast.Call):
            fn=self._resolve_expr(node.value.func)
            if fn in {"globals", "locals", "vars"} and key:
                return self._normalize(f"builtins.{key}")
        if isinstance(node.value, ast.Name):
            container=self._lookup_container(node.value.id)
            if isinstance(container, dict) and key in container: return container[key]
            if isinstance(container, list):
                try: return container[int(key)]
                except (ValueError, IndexError): return ""
        return ""

    def _resolve_dynamic_imports(self, node: ast.Call) -> Set[str]:
        fn=self._resolve_expr(node.func)
        if fn not in {"builtins.__import__", "__import__", "importlib.import_module"}: return set()
        if not node.args: return set()
        return self._constant_strings(node.args[0])

    def _resolve_getattr(self, node: ast.Call) -> str:
        fn=self._resolve_expr(node.func)
        if fn not in {"getattr", "builtins.getattr"} or len(node.args)<2: return ""
        attrs=self._constant_strings(node.args[1])
        if len(attrs)!=1: return ""
        base=self._resolve_expr(node.args[0])
        return self._normalize(f"{base}.{next(iter(attrs))}") if base else ""

    def _resolve_expr(self, node: Optional[ast.AST]) -> str:
        if node is None: return ""
        if isinstance(node, ast.Name): return self._lookup(node.id)
        if isinstance(node, ast.Attribute):
            base=self._resolve_expr(node.value)
            textual=""
            if isinstance(node.value, ast.Name): textual=f"{node.value.id}.{node.attr}"
            if textual:
                looked=self._lookup(textual)
                if looked != textual: return self._normalize(looked)
            return self._normalize(f"{base}.{node.attr}") if base else ""
        if isinstance(node, ast.Subscript): return self._resolve_subscript(node)
        if isinstance(node, ast.NamedExpr):
            self._bind(node.target,node.value)
            return self._resolve_expr(node.value)
        if isinstance(node, ast.Call):
            got=self._resolve_getattr(node)
            if got: return got
            mods=self._resolve_dynamic_imports(node)
            if len(mods)==1: return next(iter(mods))
            fn=self._resolve_expr(node.func)
            if fn in {"pathlib.Path", "Path"}: return "pathlib.Path"
            if fn in {"functools.partial", "partial"} and node.args:
                return self._resolve_expr(node.args[0])
            if fn.startswith("return:"): return fn[len("return:"):]
            resolved_fn=self._lookup(fn)
            if resolved_fn.startswith("return:"): return resolved_fn[len("return:"):]
            return ""
        return ""

    def _bind(self, target: ast.AST, value: ast.AST) -> None:
        if isinstance(target, ast.Name):
            resolved=self._resolve_expr(value)
            if resolved: self.scope_stack[-1][target.id]=resolved
            container=self._container_value(value)
            if container is not None: self.container_stack[-1][target.id]=container
        elif isinstance(target, ast.Attribute) and self.class_stack and isinstance(target.value, ast.Name):
            resolved=self._resolve_expr(value)
            if resolved: self.scope_stack[-2][f"{target.value.id}.{target.attr}"]=resolved
        elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List)):
            for t,v in zip(target.elts,value.elts): self._bind(t,v)

    def _container_value(self, value: ast.AST) -> Any:
        if isinstance(value,(ast.List,ast.Tuple)):
            vals=[self._resolve_expr(x) for x in value.elts]
            return vals if any(vals) else None
        if isinstance(value,ast.Dict):
            out={}
            for k,v in zip(value.keys,value.values):
                keys=self._constant_strings(k) if k is not None else set()
                if len(keys)==1:
                    r=self._resolve_expr(v)
                    if r: out[next(iter(keys))]=r
            return out or None
        return None

    def _is_dangerous(self, name: str) -> bool:
        name=self._normalize(name)
        return (name in self.DANGEROUS_FULL_NAMES or name.startswith("subprocess.")
                or name.startswith("os.exec") or name.startswith("os.spawn"))

    def visit_Import(self,node:ast.Import)->None:
        for alias in node.names:
            root=alias.name.split('.')[0]; local=alias.asname or root
            self.import_roots.add(root); self.scope_stack[-1][local]=alias.name
            if root in self.NETWORK_MODULES: self._record(self.network_hits,root,node)
            if alias.name in self.DANGEROUS_LOADER_MODULES or root in {"ctypes","cffi","zipimport"}:
                self._record(self.process_hits,f"dangerous_loader:{alias.name}",node)
        self.generic_visit(node)

    def visit_ImportFrom(self,node:ast.ImportFrom)->None:
        module=node.module or ""; root=module.split('.')[0] if module else ""
        if root: self.import_roots.add(root)
        for alias in node.names:
            if alias.name=='*':
                self.star_imports.add(module); self._record(self.obfuscation_hits,f"wildcard_import:{module}",node); continue
            local=alias.asname or alias.name
            self.scope_stack[-1][local]=self._normalize(f"{module}.{alias.name}".strip('.'))
        if root in self.NETWORK_MODULES: self._record(self.network_hits,root,node)
        if module in self.DANGEROUS_LOADER_MODULES or root in {"ctypes","cffi","zipimport"}:
            self._record(self.process_hits,f"dangerous_loader:{module or root}",node)
        self.generic_visit(node)

    def visit_Assign(self,node:ast.Assign)->None:
        self.visit(node.value)
        for target in node.targets: self._bind(target,node.value)

    def visit_AnnAssign(self,node:ast.AnnAssign)->None:
        if node.value is not None:
            self.visit(node.value); self._bind(node.target,node.value)

    def visit_NamedExpr(self,node:ast.NamedExpr)->None:
        self.visit(node.value); self._bind(node.target,node.value)

    def visit_FunctionDef(self,node:ast.FunctionDef)->None:
        parent=self.scope_stack[-1]
        self.scope_stack.append({}); self.container_stack.append({})
        for arg in node.args.args: self.scope_stack[-1][arg.arg]=arg.arg
        self.generic_visit(node)
        returns=[]
        for child in ast.walk(node):
            if isinstance(child,ast.Return):
                r=self._resolve_expr(child.value)
                if r: returns.append(r)
        self.scope_stack.pop(); self.container_stack.pop()
        dangerous=[r for r in returns if self._is_dangerous(r)]
        if len(set(dangerous))==1: parent[node.name]=f"return:{dangerous[0]}"
        else: parent.setdefault(node.name,node.name)

    visit_AsyncFunctionDef=visit_FunctionDef

    def visit_Lambda(self,node:ast.Lambda)->None:
        self.scope_stack.append({}); self.container_stack.append({})
        self.visit(node.body)
        self.scope_stack.pop(); self.container_stack.pop()

    def visit_ClassDef(self,node:ast.ClassDef)->None:
        parent=self.scope_stack[-1]; parent[node.name]=f"class:{node.name}"
        self.class_stack.append(node.name); self.scope_stack.append({}); self.container_stack.append({})
        self.generic_visit(node)
        class_scope=self.scope_stack.pop(); self.container_stack.pop(); self.class_stack.pop()
        for attr,resolved in class_scope.items(): parent[f"{node.name}.{attr}"]=resolved

    def visit_Call(self,node:ast.Call)->None:
        call_name=self._normalize(self._resolve_expr(node.func))
        imports=self._resolve_dynamic_imports(node)
        fn_name=self._resolve_expr(node.func)

        if self._is_dangerous(call_name): self._record(self.process_hits,call_name,node)
        for module in imports:
            self._record(self.process_hits,f"dynamic_import:{module}",node)
            if module.split('.')[0] in self.NETWORK_MODULES: self._record(self.network_hits,module,node)
        if fn_name in {"builtins.__import__","__import__","importlib.import_module"} and not imports:
            self._record(self.obfuscation_hits,"unresolved_dynamic_import",node)

        if isinstance(node.func,ast.Name) and node.func.id=='getattr' and len(node.args)>=2:
            attrs=self._constant_strings(node.args[1]); base=self._resolve_expr(node.args[0])
            if not attrs:
                self._record(self.obfuscation_hits,"dynamic_getattr",node)
                if base.split('.')[0] in {"os","subprocess","builtins","ctypes"}:
                    self._record(self.process_hits,f"unresolved_dangerous_getattr:{base}",node)

        if call_name in self.FILE_MUTATION_FULL_NAMES: self._record(self.file_write_hits,call_name,node)
        method=node.func.attr if isinstance(node.func,ast.Attribute) else ""
        receiver=self._resolve_expr(node.func.value) if isinstance(node.func,ast.Attribute) else ""
        if method in self.PATH_WRITE_METHODS and receiver=="pathlib.Path":
            self._record(self.file_write_hits,f"pathlib.Path.{method}",node)

        if call_name in self.OPEN_FUNCTIONS or call_name.endswith('.open'):
            mode=None
            if len(node.args)>=2:
                vals=self._constant_strings(node.args[1]); mode=next(iter(vals)) if len(vals)==1 else None
            for kw in node.keywords:
                if kw.arg=='mode':
                    vals=self._constant_strings(kw.value); mode=next(iter(vals)) if len(vals)==1 else mode
            if mode and any(flag in mode for flag in ('w','a','x','+')):
                self._record(self.file_write_hits,f"{call_name}(mode={mode!r})",node)

        if call_name in {"operator.attrgetter","attrgetter","operator.methodcaller","methodcaller"} and node.args:
            methods=self._constant_strings(node.args[0])
            if methods & self.DANGEROUS_METHOD_NAMES:
                self._record(self.process_hits,f"dangerous_accessor:{next(iter(methods & self.DANGEROUS_METHOD_NAMES))}",node)
            else: self._record(self.obfuscation_hits,f"dynamic_accessor:{call_name}",node)

        if call_name in {"globals","locals","vars"}: self._record(self.obfuscation_hits,f"namespace_introspection:{call_name}",node)
        if call_name in {"base64.b64decode","base64.decodebytes","codecs.decode"}: self._record(self.obfuscation_hits,f"encoded_payload_decode:{call_name}",node)
        if call_name in {"builtins.chr","chr"}: self._record(self.obfuscation_hits,"runtime_string_construction:chr",node)

        if receiver.startswith('ctypes.') or call_name.startswith('ctypes.') or receiver.startswith('cffi.'):
            self._record(self.process_hits,f"dynamic_library_call:{call_name or method}",node)
        if method in self.DANGEROUS_METHOD_NAMES and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Call):
            inner=self._resolve_expr(node.func.value.func)
            if inner.startswith('ctypes.') or inner in {'ctypes.CDLL','ctypes.PyDLL','ctypes.WinDLL','ctypes.OleDLL'}:
                self._record(self.process_hits,f"dynamic_library_method:{method}",node)
        self.generic_visit(node)

    def visit_BinOp(self,node:ast.BinOp)->None:
        if isinstance(node.op,ast.BitXor): self._record(self.obfuscation_hits,"xor_expression",node)
        self.generic_visit(node)

    def visit_Constant(self,node:ast.Constant)->None:
        if isinstance(node.value,str) and len(node.value)>=120 and re.fullmatch(r"[A-Za-z0-9+/=_-]+",node.value):
            self._record(self.obfuscation_hits,"long_encoded_string",node)

    def imports(self)->List[str]: return sorted(self.import_roots)
    def find_network_access(self)->List[str]: return sorted(self.network_hits)
    def find_process_or_dynamic_execution(self)->List[str]: return sorted(self.process_hits)
    def find_file_writes(self)->List[str]: return sorted(self.file_write_hits)
    def find_suspicious_obfuscation(self)->List[str]: return sorted(self.obfuscation_hits)
    def find_secrets(self)->List[str]:
        return sorted(name for name,pattern in self.SECRET_PATTERNS.items() if pattern.search(self.source))


# =============================================================================
# POLICY AND SCORING
# =============================================================================

KNOWN_CHECK_TYPES = frozenset({
    "manifest_complete",
    "python_syntax",
    "no_network",
    "no_file_writes",
    "no_process_execution",
    "dependencies_declared",
    "no_secrets",
    "no_suspicious_obfuscation",
})
KNOWN_SEVERITIES = frozenset({"hard_reject", "hard_hold"})
ALLOWED_POLICY_FIELDS = frozenset({
    "policy_schema_version", "name", "version", "description", "limits", "checklist"
})
REQUIRED_POLICY_FIELDS = frozenset({
    "policy_schema_version", "name", "version", "limits", "checklist"
})
ALLOWED_RULE_FIELDS = frozenset({
    "id", "description", "severity", "check_type", "target_value"
})
REQUIRED_RULE_FIELDS = ALLOWED_RULE_FIELDS


DEFAULT_POLICY: Dict[str, Any] = {
    "policy_schema_version": POLICY_SCHEMA_VERSION,
    "name": "CodeIntake_Security_Default",
    "version": ENGINE_VERSION,
    "description": "Manifest-first static policy with Stage 03 trust infrastructure",
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
            "description": "No process, shell, eval, exec, compile, or dynamic loader operation is detected",
            "severity": "hard_reject",
            "check_type": "no_process_execution",
            "target_value": True,
        },
        {
            "id": "dependencies_declared",
            "description": "Imported modules are declared or are standard-library modules",
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
            "description": "No configured suspicious-obfuscation indicator is detected",
            "severity": "hard_hold",
            "check_type": "no_suspicious_obfuscation",
            "target_value": True,
        },
    ],
}


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def validate_policy(policy: Any) -> Dict[str, Any]:
    errors: List[str] = []

    if not isinstance(policy, dict):
        raise PolicyValidationError("Policy root must be a JSON object")

    unknown_top = sorted(set(policy) - ALLOWED_POLICY_FIELDS)
    missing_top = sorted(REQUIRED_POLICY_FIELDS - set(policy))
    if unknown_top:
        errors.append("Unknown top-level field(s): " + ", ".join(unknown_top))
    if missing_top:
        errors.append("Missing top-level field(s): " + ", ".join(missing_top))

    schema = policy.get("policy_schema_version")
    if schema != POLICY_SCHEMA_VERSION:
        errors.append(
            f"Unsupported policy_schema_version {schema!r}; expected {POLICY_SCHEMA_VERSION!r}"
        )

    for field_name in ("name", "version"):
        value = policy.get(field_name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Policy {field_name!r} must be a non-empty string")

    description = policy.get("description", "")
    if not isinstance(description, str):
        errors.append("Policy 'description' must be a string when present")

    limits = policy.get("limits")
    if not isinstance(limits, dict):
        errors.append("Policy 'limits' must be an object")
    else:
        unknown_limits = sorted(set(limits) - {"max_file_bytes", "allowed_extensions"})
        if unknown_limits:
            errors.append("Unknown limit field(s): " + ", ".join(unknown_limits))

        max_bytes = limits.get("max_file_bytes")
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
            errors.append("'max_file_bytes' must be a positive integer")

        extensions = limits.get("allowed_extensions")
        if (
            not isinstance(extensions, list)
            or not extensions
            or any(
                not isinstance(item, str)
                or not item.startswith(".")
                or item != item.lower()
                for item in extensions
            )
            or len(set(extensions)) != len(extensions)
        ):
            errors.append(
                "'allowed_extensions' must be a non-empty unique list of lowercase dot-prefixed strings"
            )

    checklist = policy.get("checklist")
    seen_ids: Set[str] = set()
    if not isinstance(checklist, list) or not checklist:
        errors.append("Policy 'checklist' must be a non-empty list")
    else:
        for index, item in enumerate(checklist):
            prefix = f"Checklist item {index}"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue

            unknown = sorted(set(item) - ALLOWED_RULE_FIELDS)
            missing = sorted(REQUIRED_RULE_FIELDS - set(item))
            if unknown:
                errors.append(f"{prefix} has unknown field(s): {', '.join(unknown)}")
            if missing:
                errors.append(f"{prefix} is missing field(s): {', '.join(missing)}")
                continue

            rule_id = item.get("id")
            if not isinstance(rule_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", rule_id):
                errors.append(f"{prefix} has invalid id {rule_id!r}")
            elif rule_id in seen_ids:
                errors.append(f"Duplicate checklist id: {rule_id}")
            else:
                seen_ids.add(rule_id)

            rule_description = item.get("description")
            if not isinstance(rule_description, str) or not rule_description.strip():
                errors.append(f"{prefix} description must be a non-empty string")

            severity = item.get("severity")
            if severity not in KNOWN_SEVERITIES:
                errors.append(f"{prefix} has unknown severity {severity!r}")

            check_type = item.get("check_type")
            if check_type not in KNOWN_CHECK_TYPES:
                errors.append(f"{prefix} has unknown check_type {check_type!r}")

            if not isinstance(item.get("target_value"), bool):
                errors.append(f"{prefix} target_value must be boolean")

    if errors:
        raise PolicyValidationError("; ".join(errors))

    # Round-trip through canonical JSON to detach caller-owned mutable objects.
    return json.loads(canonical_json_bytes(policy).decode("utf-8"))


def policy_fingerprint(policy: Dict[str, Any]) -> str:
    validated = validate_policy(policy)
    return hashlib.sha256(canonical_json_bytes(validated)).hexdigest()


class PolicyEngine:
    def __init__(self, policy: Dict[str, Any]):
        self.policy = validate_policy(policy)
        self.items = [ChecklistItem(**item) for item in self.policy["checklist"]]

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
        manifest: Dict[str, Any],
        manifest_issues: Sequence[ManifestIssue],
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
                actual = {
                    "fields": sorted(manifest.keys()),
                    "issues": [asdict(issue) for issue in manifest_issues],
                }
                detail = (
                    "Manifest is complete and schema-valid"
                    if satisfied else "Manifest is absent or invalid"
                )

            elif item.check_type == "python_syntax":
                satisfied = analyzer is not None and syntax_error is None
                actual = syntax_error
                detail = (
                    "Valid Python syntax"
                    if satisfied else f"Python parse failed: {syntax_error}"
                )

            elif item.check_type == "no_network":
                hits = analyzer.find_network_access() if analyzer else []
                satisfied = analyzer is not None and not hits
                actual = hits
                detail = (
                    "No network imports found"
                    if satisfied else "Network imports found: " + ", ".join(hits)
                )

            elif item.check_type == "no_file_writes":
                hits = analyzer.find_file_writes() if analyzer else []
                satisfied = analyzer is not None and not hits
                actual = hits
                detail = (
                    "No direct file writes found"
                    if satisfied else "File writes found: " + ", ".join(hits)
                )

            elif item.check_type == "no_process_execution":
                hits = analyzer.find_process_or_dynamic_execution() if analyzer else []
                satisfied = analyzer is not None and not hits
                actual = hits
                detail = (
                    "No process or dynamic execution found"
                    if satisfied
                    else "Process or dynamic execution found: " + ", ".join(hits)
                )

            elif item.check_type == "dependencies_declared":
                imports = analyzer.imports() if analyzer else []
                declared_raw = manifest.get("dependencies", "")
                declared = {
                    token.strip().split(".")[0]
                    for token in declared_raw.split(",")
                    if token.strip()
                    and token.strip().lower()
                    not in {"none", "stdlib", "standard library"}
                }
                stdlib = self._stdlib_modules()
                undeclared = sorted(
                    root for root in imports
                    if root not in stdlib and root not in declared
                )
                satisfied = analyzer is not None and not undeclared
                actual = {
                    "imports": imports,
                    "declared": sorted(declared),
                    "undeclared": undeclared,
                }
                detail = (
                    "Dependencies are declared"
                    if satisfied
                    else "Undeclared dependencies: " + ", ".join(undeclared)
                )

            elif item.check_type == "no_secrets":
                hits = analyzer.find_secrets() if analyzer else []
                satisfied = analyzer is not None and not hits
                actual = hits
                detail = (
                    "No obvious hardcoded secrets found"
                    if satisfied
                    else "Potential secrets found: " + ", ".join(hits)
                )

            elif item.check_type == "no_suspicious_obfuscation":
                hits = analyzer.find_suspicious_obfuscation() if analyzer else []
                satisfied = analyzer is not None and not hits
                actual = hits
                detail = (
                    "No configured suspicious-obfuscation indicators found"
                    if satisfied
                    else "Suspicious-obfuscation indicators found: " + ", ".join(hits)
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
        reject_failures = [
            result for result in failed if result.severity == "hard_reject"
        ]
        hold_failures = [
            result for result in failed if result.severity == "hard_hold"
        ]

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
# CROSS-PLATFORM LEDGER LOCK
# =============================================================================

@contextmanager
def exclusive_lock(lock_path: Path, timeout_seconds: float = 15.0) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    deadline = time.monotonic() + timeout_seconds

    try:
        if os.name == "nt":
            import msvcrt
            while True:
                try:
                    handle.seek(0)
                    if handle.tell() == 0:
                        handle.write(b"\0")
                        handle.flush()
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise LedgerIntegrityError(
                            f"Timed out acquiring ledger lock: {lock_path}"
                        )
                    time.sleep(0.05)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise LedgerIntegrityError(
                            f"Timed out acquiring ledger lock: {lock_path}"
                        )
                    time.sleep(0.05)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


# =============================================================================
# GUARDIAN
# =============================================================================

class Guardian:
    def __init__(
        self,
        policy_path: Optional[Path] = None,
        ledger_path: Path = Path("guardian_ledger.jsonl"),
        signing_key: Optional[str] = None,
        unsigned_dev: bool = False,
    ):
        self.ledger_path = ledger_path
        self.lock_path = ledger_path.with_name(ledger_path.name + ".lock")
        self.unsigned_dev = unsigned_dev
        self.policy = self._load_policy(policy_path)
        self.policy_fingerprint = policy_fingerprint(self.policy)
        key_text = signing_key or os.environ.get("GUARDIAN_HMAC_KEY", "")
        self.signing_key = key_text.encode("utf-8")

    @staticmethod
    def _load_policy(policy_path: Optional[Path]) -> Dict[str, Any]:
        if policy_path is None:
            return validate_policy(DEFAULT_POLICY)
        try:
            with policy_path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except FileNotFoundError as exc:
            raise PolicyValidationError(f"Policy file not found: {policy_path}") from exc
        except json.JSONDecodeError as exc:
            raise PolicyValidationError(
                f"Policy is not valid JSON at line {exc.lineno}, column {exc.colno}"
            ) from exc
        except OSError as exc:
            raise PolicyValidationError(f"Could not read policy: {exc}") from exc
        return validate_policy(raw)

    @staticmethod
    def _sha256_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _fingerprint_slip(self, slip_dict: Dict[str, Any]) -> str:
        unsigned = dict(slip_dict)
        unsigned["slip_fingerprint"] = ""
        unsigned["slip_signature"] = ""
        return self._sha256_bytes(canonical_json_bytes(unsigned))

    def _sign_fingerprint(self, fingerprint: str) -> str:
        if not self.signing_key:
            return ""
        return hmac.new(
            self.signing_key,
            fingerprint.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()

    def _preflight(self, file_path: Path) -> List[str]:
        issues: List[str] = []
        limits = self.policy["limits"]

        if not file_path.exists():
            return ["File does not exist"]
        if not file_path.is_file():
            return ["Path is not a regular file"]
        if file_path.is_symlink():
            issues.append("Symbolic links are not accepted")

        if file_path.suffix.lower() not in set(limits["allowed_extensions"]):
            issues.append(f"Extension {file_path.suffix!r} is not allowed")

        size = file_path.stat().st_size
        if size > limits["max_file_bytes"]:
            issues.append(
                f"File size {size} exceeds policy limit {limits['max_file_bytes']}"
            )
        return issues

    def _analyze(self, file_path: Path) -> Dict[str, Any]:
        file_path = file_path.expanduser()
        preflight_issues = self._preflight(file_path)
        if preflight_issues and not file_path.exists():
            raise FileNotFoundError("; ".join(preflight_issues))

        raw = file_path.read_bytes()
        file_hash = self._sha256_bytes(raw)
        file_size = len(raw)

        source_text: Optional[str] = None
        decode_error: Optional[str] = None
        try:
            source_text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            decode_error = f"UnicodeDecodeError: {exc}"

        if source_text is None:
            manifest: Dict[str, Any] = {}
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
        syntax_error = decode_error
        if source_text is not None:
            try:
                analyzer = StaticAnalyzer(file_path, source=source_text)
            except SyntaxError as exc:
                syntax_error = f"SyntaxError: {exc}"

        engine = PolicyEngine(self.policy)
        results = engine.run(
            file_path=file_path,
            manifest=manifest,
            manifest_issues=manifest_issues,
            analyzer=analyzer,
            syntax_error=syntax_error,
        )

        caveats = list(preflight_issues) + [
            f"{issue.code}: {issue.message}" for issue in manifest_issues
        ]
        risk, evidence, decision, state, outcome = engine.classify(results, caveats)

        if any(issue.severity == "reject" for issue in manifest_issues):
            risk = RiskLabel.FAILED
            evidence = EvidenceStatus.CONTRADICTED
            decision = Decision.REVERSE
            state = ProcessState.RESTRICT
            outcome = IntakeOutcome.REJECT

        if preflight_issues:
            risk = RiskLabel.FAILED
            evidence = EvidenceStatus.CONTRADICTED
            decision = Decision.REVERSE
            state = ProcessState.RESTRICT
            outcome = IntakeOutcome.REJECT

        return {
            "file_path_obj": file_path,
            "file_hash": file_hash,
            "file_size": file_size,
            "manifest": manifest,
            "results": results,
            "risk": risk,
            "evidence": evidence,
            "decision": decision,
            "state": state,
            "outcome": outcome,
            "caveats": caveats,
        }

    def _build_slip(self, analysis: Dict[str, Any], previous_hash: str) -> ResultSlip:
        file_path: Path = analysis["file_path_obj"]
        timestamp = datetime.now(timezone.utc).isoformat()
        slip_dict: Dict[str, Any] = {
            "slip_schema_name": SLIP_SCHEMA_NAME,
            "slip_schema_version": SLIP_SCHEMA_VERSION,
            "engine_version": ENGINE_VERSION,
            "slip_id": (
                f"guardian-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-"
                f"{secrets.token_hex(4)}"
            ),
            "timestamp": timestamp,
            "policy_schema_version": self.policy["policy_schema_version"],
            "policy_name": self.policy["name"],
            "policy_version": self.policy["version"],
            "policy_fingerprint": self.policy_fingerprint,
            "file_name": file_path.name,
            "file_path": str(file_path.resolve()),
            "file_size": analysis["file_size"],
            "file_fingerprint": analysis["file_hash"],
            "manifest": analysis["manifest"],
            "item_results": [asdict(result) for result in analysis["results"]],
            "risk_label": analysis["risk"].value,
            "evidence_status": analysis["evidence"].value,
            "decision": analysis["decision"].value,
            "process_state": analysis["state"].value,
            "intake_outcome": analysis["outcome"].value,
            "caveats": analysis["caveats"],
            "unsigned_dev_mode": self.unsigned_dev and not bool(self.signing_key),
            "previous_slip_hash": previous_hash,
            "slip_fingerprint": "",
            "slip_signature": "",
        }
        fingerprint = self._fingerprint_slip(slip_dict)
        slip_dict["slip_fingerprint"] = fingerprint
        slip_dict["slip_signature"] = self._sign_fingerprint(fingerprint)
        return ResultSlip(**slip_dict)

    def _verify_entries(
        self,
        entries: Sequence[Dict[str, Any]],
        require_signatures: bool = False,
    ) -> Tuple[bool, List[str], str]:
        issues: List[str] = []
        expected_prev = ZERO_HASH
        last_hash = ZERO_HASH

        for line_number, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                issues.append(f"Line {line_number}: entry must be an object")
                continue

            slip = entry.get("slip")
            if not isinstance(slip, dict):
                issues.append(f"Line {line_number}: missing slip object")
                continue

            stored_fp = slip.get("slip_fingerprint", "")
            stored_prev = slip.get("previous_slip_hash", "")

            if stored_prev != expected_prev:
                issues.append(
                    f"Line {line_number}: previous hash does not match chain"
                )

            if slip.get("slip_schema_name") != SLIP_SCHEMA_NAME:
                issues.append(f"Line {line_number}: unsupported slip schema name")
            if slip.get("slip_schema_version") != SLIP_SCHEMA_VERSION:
                issues.append(f"Line {line_number}: unsupported slip schema version")

            try:
                recomputed = self._fingerprint_slip(slip)
            except (TypeError, ValueError) as exc:
                issues.append(f"Line {line_number}: canonicalization failed: {exc}")
                recomputed = ""

            if recomputed != stored_fp:
                issues.append(f"Line {line_number}: slip fingerprint mismatch")

            signature = slip.get("slip_signature", "")
            if self.signing_key:
                expected_signature = self._sign_fingerprint(stored_fp)
                if not signature or not hmac.compare_digest(expected_signature, signature):
                    issues.append(f"Line {line_number}: HMAC signature mismatch")
            elif require_signatures and not signature:
                issues.append(f"Line {line_number}: signature required but missing")

            expected_prev = stored_fp
            last_hash = stored_fp

        return not issues, issues, last_hash

    def _read_entries_locked(self) -> List[Dict[str, Any]]:
        if not self.ledger_path.exists():
            return []

        entries: List[Dict[str, Any]] = []
        try:
            with self.ledger_path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        raise LedgerIntegrityError(
                            f"Line {line_number}: invalid JSON: {exc}"
                        ) from exc
        except OSError as exc:
            raise LedgerIntegrityError(f"Could not read ledger: {exc}") from exc
        return entries

    def scan(self, file_path: Path) -> ResultSlip:
        if not self.signing_key and not self.unsigned_dev:
            raise UnsignedModeError(
                "A scan that appends a receipt requires GUARDIAN_HMAC_KEY, "
                "--hmac-key, or explicit --unsigned-dev"
            )

        analysis = self._analyze(file_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

        with exclusive_lock(self.lock_path):
            entries = self._read_entries_locked()
            valid, issues, terminal_hash = self._verify_entries(entries)
            if not valid:
                raise LedgerIntegrityError(
                    "Ledger verification failed before append: " + "; ".join(issues)
                )

            slip = self._build_slip(analysis, terminal_hash)
            entry = {
                "appended_at": datetime.now(timezone.utc).isoformat(),
                "slip": asdict(slip),
            }
            line = canonical_json_bytes(entry) + b"\n"

            try:
                fd = os.open(
                    str(self.ledger_path),
                    os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                    0o600,
                )
                try:
                    written = os.write(fd, line)
                    if written != len(line):
                        raise LedgerIntegrityError(
                            f"Short ledger write: {written} of {len(line)} bytes"
                        )
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except OSError as exc:
                raise LedgerIntegrityError(f"Ledger append failed: {exc}") from exc

        return slip

    def replay(self) -> Tuple[bool, List[str]]:
        with exclusive_lock(self.lock_path):
            entries = self._read_entries_locked()
            if not entries:
                return True, ["Ledger is empty"]
            valid, issues, _ = self._verify_entries(entries)
            return valid, issues

    def ledger_summary(self) -> Dict[str, Any]:
        with exclusive_lock(self.lock_path):
            entries = self._read_entries_locked()
            valid, issues, terminal_hash = self._verify_entries(entries)

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
            "hmac_verification_enabled": bool(self.signing_key),
            "chain_valid": valid,
            "chain_issues": issues,
            "terminal_hash": terminal_hash,
        }

        for entry in entries:
            slip = entry.get("slip", {})
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

def print_slip(slip: ResultSlip, explain: bool = False) -> None:
    width = 82
    print("=" * width)
    print("GUARDIAN RESULT SLIP".center(width))
    print("=" * width)
    print(f"Slip ID:             {slip.slip_id}")
    print(f"Timestamp:           {slip.timestamp}")
    print(f"Engine:              {slip.engine_version}")
    print(f"Slip schema:         {slip.slip_schema_name} v{slip.slip_schema_version}")
    print(f"Policy:              {slip.policy_name} v{slip.policy_version}")
    print(f"Policy schema:       {slip.policy_schema_version}")
    print(f"Policy fingerprint:  {slip.policy_fingerprint}")
    print(f"File:                {slip.file_name}")
    print(f"File SHA-256:        {slip.file_fingerprint}")
    print("-" * width)
    for result in slip.item_results:
        status = "PASS" if result["satisfied"] else "FAIL"
        print(f"[{status}] {result['item_id']}: {result['detail']}")
    print("-" * width)
    print(f"Risk label:          {slip.risk_label}")
    print(f"Evidence status:     {slip.evidence_status}")
    print(f"Decision:            {slip.decision}")
    print(f"Process state:       {slip.process_state}")
    print(f"INTAKE OUTCOME:      {slip.intake_outcome.upper()}")
    if slip.caveats:
        print("-" * width)
        print("Caveats:")
        for caveat in slip.caveats:
            print(f"  - {caveat}")
    print("-" * width)
    print(f"Previous hash:       {slip.previous_slip_hash}")
    print(f"Slip fingerprint:    {slip.slip_fingerprint}")
    print(f"HMAC signature:      {slip.slip_signature or '(unsigned developer mode)'}")
    print("=" * width)
    print(SECURITY_NOTICE)

    if explain:
        print()
        print("WHY THIS RESULT".center(width))
        print("=" * width)
        failed = [item for item in slip.item_results if not item["satisfied"]]
        if not failed:
            print("No configured policy check failed.")
        else:
            for item in failed:
                print(f"- {item['item_id']} ({item['severity']}): {item['detail']}")
        print()
        print(
            f"The decision was made by policy fingerprint {slip.policy_fingerprint}. "
            "The fingerprint identifies the exact canonical policy content used."
        )
        if slip.intake_outcome == IntakeOutcome.LET_IN.value:
            print(
                "LET IN means the file passed the implemented checks. "
                "It is not a safety certification."
            )
        elif slip.intake_outcome == IntakeOutcome.HOLD.value:
            print(
                "HOLD means the file requires review before admission under this policy."
            )
        else:
            print(
                "REJECT means at least one configured reject-level check failed."
            )
        print("=" * width)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Guardian code intake checkpoint")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("guardian_ledger.jsonl"),
        help="Path to the JSONL result-slip ledger",
    )
    parser.add_argument(
        "--hmac-key",
        default=None,
        help="HMAC key. Prefer the GUARDIAN_HMAC_KEY environment variable.",
    )
    parser.add_argument(
        "--unsigned-dev",
        action="store_true",
        help="Explicitly permit unsigned receipt append for local development only.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan one Python file")
    scan_parser.add_argument("file", type=Path)
    scan_parser.add_argument("--policy", type=Path, default=None)
    scan_parser.add_argument("--json", action="store_true")
    scan_parser.add_argument("--explain", action="store_true")

    subparsers.add_parser("ledger", help="Show ledger summary")
    subparsers.add_parser("replay", help="Verify ledger chain and available HMACs")

    init_parser = subparsers.add_parser(
        "init-policy", help="Write the default policy"
    )
    init_parser.add_argument(
        "--out", type=Path, default=Path("guardian_policy.json")
    )

    validate_parser = subparsers.add_parser(
        "validate-policy", help="Validate and fingerprint a policy"
    )
    validate_parser.add_argument("policy", type=Path)

    subparsers.add_parser("version", help="Show Guardian engine and schema versions")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        print(
            json.dumps(
                {
                    "engine_version": ENGINE_VERSION,
                    "slip_schema_version": SLIP_SCHEMA_VERSION,
                    "policy_schema_version": POLICY_SCHEMA_VERSION,
                },
                sort_keys=True,
            )
        )
        return 0

    if args.command == "init-policy":
        args.out.write_text(
            json.dumps(DEFAULT_POLICY, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Default policy written to {args.out}")
        return 0

    if args.command == "validate-policy":
        try:
            policy = Guardian._load_policy(args.policy)
            print(
                json.dumps(
                    {
                        "valid": True,
                        "name": policy["name"],
                        "version": policy["version"],
                        "policy_schema_version": policy["policy_schema_version"],
                        "policy_fingerprint": policy_fingerprint(policy),
                        "checklist_items": len(policy["checklist"]),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        except PolicyValidationError as exc:
            print(f"Policy validation failed: {exc}", file=sys.stderr)
            return 5

    try:
        guardian = Guardian(
            policy_path=getattr(args, "policy", None),
            ledger_path=args.ledger,
            signing_key=args.hmac_key,
            unsigned_dev=args.unsigned_dev,
        )
    except PolicyValidationError as exc:
        print(f"Policy error: {exc}", file=sys.stderr)
        return 5

    if args.command == "scan":
        if not guardian.signing_key and args.unsigned_dev:
            print(
                "[WARN] Guardian is running in explicit unsigned developer mode. "
                "The ledger is hash-chained but not authenticated.",
                file=sys.stderr,
            )
        try:
            slip = guardian.scan(args.file)
        except UnsignedModeError as exc:
            print(f"Guardian unsigned-mode error: {exc}", file=sys.stderr)
            return 4
        except LedgerIntegrityError as exc:
            print(f"Guardian ledger error: {exc}", file=sys.stderr)
            return 6
        except Exception as exc:
            print(f"Guardian scan error: {exc}", file=sys.stderr)
            return 4

        if args.json:
            print(canonical_json_bytes(asdict(slip)).decode("utf-8"))
        else:
            print_slip(slip, explain=args.explain)

        if slip.intake_outcome == IntakeOutcome.LET_IN.value:
            return 0
        if slip.intake_outcome == IntakeOutcome.HOLD.value:
            return 2
        return 3

    if args.command == "replay":
        try:
            valid, issues = guardian.replay()
        except LedgerIntegrityError as exc:
            print(f"Ledger replay failed: {exc}", file=sys.stderr)
            return 6
        if valid:
            print("Ledger replay passed. Chain integrity confirmed.")
            for issue in issues:
                print(issue)
            return 0
        print("Ledger replay failed.")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.command == "ledger":
        try:
            print(json.dumps(guardian.ledger_summary(), indent=2, sort_keys=True))
            return 0
        except LedgerIntegrityError as exc:
            print(f"Ledger summary failed: {exc}", file=sys.stderr)
            return 6

    parser.error("Unknown command")
    return 4


if __name__ == "__main__":
    raise SystemExit(main())

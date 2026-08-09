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

DEFAULT_POLICY: Dict[str, Any] = {
    "name": "CodeIntake_Security_Default",
    "version": "0.4.1",
    "description": "Manifest-first static policy with Stage 02B scope-aware analyzer hardening",
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

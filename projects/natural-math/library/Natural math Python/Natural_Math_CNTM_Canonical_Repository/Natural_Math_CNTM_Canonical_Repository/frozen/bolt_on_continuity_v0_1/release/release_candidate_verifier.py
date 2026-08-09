from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any

class ReleaseCandidateRejected(RuntimeError):
    def __init__(self, reason_code: str, message: str):
        super().__init__(message); self.reason_code=reason_code

def canonical_json(value: Any) -> bytes:
    if isinstance(value,float): raise TypeError("floating-point values forbidden")
    if isinstance(value,dict):
        for item in value.values(): canonical_json(item)
    elif isinstance(value,(list,tuple)):
        for item in value: canonical_json(item)
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def digest(value: Any) -> str:
    return "sha256:"+hashlib.sha256(canonical_json(value)).hexdigest()

REQUIRED_STAGE_FILES = {
  0:["README.md","PRODUCT_CONTRACT.md"],
  1:["README_STAGE_1.md"],
  2:["README_STAGE_2.md"],
  3:["README_STAGE_3.md"],
  4:["README_STAGE_4.md"],
  5:["README_STAGE_5.md"],
  6:["README_STAGE_6.md","tools/qualify_stage_6_fixture.py","tools/qualify_stage_6_live.py"],
  7:["README_STAGE_7.md","tools/qualify_stage_7_fixture.py"],
  8:["README_STAGE_8.md","tools/qualify_stage_8_fixture.py","tools/qualify_stage_8_live.py"],
  9:["README_STAGE_9.md","tools/qualify_stage_9_fixture.py","tools/qualify_stage_9_live_recovery.py"],
  10:["README_STAGE_10.md","release/RELEASE_CANDIDATE_MANIFEST.json","release/QUALIFICATION_SUMMARY.md",
      "docs/STAGE_10_CONTRACT.md","docs/INSTALLATION_AND_OPERATION.md"],
}
FORBIDDEN_EXECUTOR_OPERATIONS={"stop","kill","rm","remove","restart","exec","run","create"}
ALLOWED_EXECUTOR_OPERATIONS={"inspect","pause","unpause"}

class ReleaseCandidateVerifier:
    def __init__(self, product_root: Path):
        self.product_root=Path(product_root)

    def _read_manifest(self):
        path=self.product_root/"release"/"RELEASE_CANDIDATE_MANIFEST.json"
        try: value=json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc: raise ReleaseCandidateRejected("MANIFEST_INVALID","manifest unreadable") from exc
        if value.get("product_version")!="0.1-rc1" or value.get("foundation_commit")!="dc0f9e8":
            raise ReleaseCandidateRejected("MANIFEST_INVALID","version or foundation differs")
        auth=value.get("authority",{})
        if auth.get("controlled_native_operations")!=["inspect","pause","unpause"]:
            raise ReleaseCandidateRejected("AUTHORITY_EXPANDED","native authority differs")
        if auth.get("shell") is not False or auth.get("production_use_qualified") is not False:
            raise ReleaseCandidateRejected("AUTHORITY_EXPANDED","release boundary differs")
        history=value.get("qualification_history",[])
        if [x.get("stage") for x in history]!=list(range(11)):
            raise ReleaseCandidateRejected("HISTORY_INCOMPLETE","stage history incomplete")
        return value

    def _required_files(self):
        missing=[]
        for stage,paths in REQUIRED_STAGE_FILES.items():
            for rel in paths:
                if not (self.product_root/rel).is_file(): missing.append({"stage":stage,"path":rel})
        if missing: raise ReleaseCandidateRejected("REQUIRED_FILE_MISSING",json.dumps(missing,sort_keys=True))
        return sum(len(v) for v in REQUIRED_STAGE_FILES.values())

    def _authority_scan(self):
        executor=self.product_root/"src"/"bolt_on_continuity"/"execution"/"controlled_native_executor.py"
        if not executor.is_file(): raise ReleaseCandidateRejected("EXECUTOR_MISSING","controlled executor absent")
        text=executor.read_text(encoding="utf-8")
        if "shell=False" not in text.replace(" ",""):
            raise ReleaseCandidateRejected("SHELL_BOUNDARY_MISSING","shell=False absent")
        if not all(f'"{op}"' in text or f"'{op}'" in text for op in ALLOWED_EXECUTOR_OPERATIONS):
            raise ReleaseCandidateRejected("ALLOWLIST_INCOMPLETE","required operation absent")
        mutation_lines=[line.lower() for line in text.splitlines() if "allowed" in line or "_invoke" in line or "native_operation" in line]
        joined="\n".join(mutation_lines)
        found=sorted(op for op in FORBIDDEN_EXECUTOR_OPERATIONS if re.search(rf'["\']{re.escape(op)}["\']',joined))
        if found: raise ReleaseCandidateRejected("AUTHORITY_EXPANDED",",".join(found))
        return sorted(ALLOWED_EXECUTOR_OPERATIONS)

    def _tree(self):
        rows=[]
        files=[
            path for path in self.product_root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix!=".pyc"
        ]
        files.sort(key=lambda path: path.relative_to(self.product_root).as_posix())
        for path in files:
            rel=path.relative_to(self.product_root).as_posix()
            data=path.read_bytes()
            rows.append({"path":rel,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
        return rows

    def qualify(self):
        manifest=self._read_manifest()
        required_count=self._required_files()
        allowlist=self._authority_scan()
        rows=self._tree()
        if len(rows)<30: raise ReleaseCandidateRejected("TREE_TOO_SMALL","product tree unexpectedly small")
        body={
          "schema_version":"1",
          "product":manifest["product"],
          "product_version":manifest["product_version"],
          "foundation_commit":manifest["foundation_commit"],
          "release_stage":10,
          "required_file_gate_count":required_count,
          "product_file_count":len(rows),
          "product_byte_count":sum(x["bytes"] for x in rows),
          "controlled_native_operations":allowlist,
          "production_use_qualified":False,
          "product_tree_digest":digest(rows),
          "qualified":True,
        }
        return {**body,"release_candidate_qualification_digest":digest(body)}

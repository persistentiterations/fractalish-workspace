from __future__ import annotations
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys
from pathlib import Path
from typing import Any

class FreezeRejected(RuntimeError):
    def __init__(self, reason_code:str, message:str):
        super().__init__(message);self.reason_code=reason_code

def canonical_json(value:Any)->bytes:
    if isinstance(value,float):raise TypeError("floating-point values forbidden")
    if isinstance(value,dict):
        for item in value.values():canonical_json(item)
    elif isinstance(value,(list,tuple)):
        for item in value:canonical_json(item)
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def digest(value:Any)->str:
    return "sha256:"+hashlib.sha256(canonical_json(value)).hexdigest()

def included(path:Path)->bool:
    return "__pycache__" not in path.parts and path.suffix!=".pyc" and not path.name.endswith(".tmp")

def tree_rows(root:Path)->list[dict[str,Any]]:
    files=[p for p in root.rglob("*") if p.is_file() and included(p)]
    files.sort(key=lambda p:p.relative_to(root).as_posix())
    return [{"path":p.relative_to(root).as_posix(),"bytes":p.stat().st_size,
             "sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]

def load_release_verifier(product_root:Path):
    path=product_root/"release"/"release_candidate_verifier.py"
    if not path.is_file():raise FreezeRejected("RELEASE_VERIFIER_MISSING",str(path))
    spec=importlib.util.spec_from_file_location("_freeze_rc",path)
    if spec is None or spec.loader is None:raise FreezeRejected("RELEASE_VERIFIER_MISSING",str(path))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.ReleaseCandidateVerifier(product_root)

class ProductFreezer:
    def __init__(self,repo_root:Path):
        self.repo_root=Path(repo_root).resolve()
        self.product_root=self.repo_root/"products"/"bolt_on_continuity_v0_1"
        self.frozen_root=self.repo_root/"frozen"/"bolt_on_continuity_v0_1"

    def qualify_source(self)->dict[str,Any]:
        if not self.product_root.is_dir():raise FreezeRejected("PRODUCT_MISSING",str(self.product_root))
        result=load_release_verifier(self.product_root).qualify()
        if result.get("qualified") is not True:raise FreezeRejected("RELEASE_CANDIDATE_FAILED","not qualified")
        return result

    def freeze(self,approved_by:str,approval_epoch:int)->dict[str,Any]:
        if not isinstance(approved_by,str) or not approved_by.strip():
            raise FreezeRejected("APPROVER_REQUIRED","approved_by required")
        if type(approval_epoch) is not int or approval_epoch<0:
            raise FreezeRejected("APPROVAL_TIME_INVALID","approval_epoch invalid")
        if self.frozen_root.exists():
            raise FreezeRejected("FROZEN_TARGET_EXISTS","refusing to overwrite frozen product")

        rc=self.qualify_source()
        before=tree_rows(self.product_root)
        self.frozen_root.mkdir(parents=True,exist_ok=False)
        try:
            for row in before:
                src=self.product_root/row["path"];dst=self.frozen_root/row["path"]
                dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(src,dst)

            after_source=tree_rows(self.product_root)
            frozen_rows=tree_rows(self.frozen_root)
            if before!=after_source:
                raise FreezeRejected("SOURCE_CHANGED_DURING_FREEZE","source tree changed")
            if before!=frozen_rows:
                raise FreezeRejected("SNAPSHOT_MISMATCH","copied tree differs")

            manifest_body={
                "schema_version":"1",
                "product":"Bolt-On Continuity for Docker",
                "product_version":"0.1",
                "release_candidate_version":"0.1-rc1",
                "foundation_commit":"7de6b37",
                "source_path":"products/bolt_on_continuity_v0_1",
                "frozen_path":"frozen/bolt_on_continuity_v0_1",
                "file_count":len(frozen_rows),
                "byte_count":sum(x["bytes"] for x in frozen_rows),
                "product_tree_digest":digest(frozen_rows),
                "release_candidate_qualification_digest":rc["release_candidate_qualification_digest"],
                "files":frozen_rows,
            }
            manifest={**manifest_body,"frozen_manifest_digest":digest(manifest_body)}
            (self.frozen_root/"FROZEN_MANIFEST.json").write_text(
                json.dumps(manifest,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")

            approval_body={
                "schema_version":"1",
                "product":"Bolt-On Continuity for Docker",
                "product_version":"0.1",
                "approved_by":approved_by.strip(),
                "approval_epoch":approval_epoch,
                "frozen_manifest_digest":manifest["frozen_manifest_digest"],
                "authority_boundary":["docker inspect","docker pause","docker unpause"],
                "production_use_qualified":False,
                "disposable_container_qualification_only":True,
                "approved":True,
            }
            approval={**approval_body,"freeze_approval_digest":digest(approval_body)}
            (self.frozen_root/"FREEZE_APPROVAL_RECORD.json").write_text(
                json.dumps(approval,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
            return {
                "qualified":True,
                "frozen_path":"frozen/bolt_on_continuity_v0_1",
                "file_count":manifest["file_count"],
                "byte_count":manifest["byte_count"],
                "frozen_manifest_digest":manifest["frozen_manifest_digest"],
                "freeze_approval_digest":approval["freeze_approval_digest"],
            }
        except Exception:
            if self.frozen_root.exists():shutil.rmtree(self.frozen_root)
            raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",default=".")
    p.add_argument("--approved-by",required=True)
    p.add_argument("--approval-epoch",required=True,type=int)
    p.add_argument("--acknowledge-immutable-freeze",action="store_true")
    a=p.parse_args()
    if not a.acknowledge_immutable_freeze:
        raise SystemExit("Refused: --acknowledge-immutable-freeze is required")
    result=ProductFreezer(Path(a.repo_root)).freeze(a.approved_by,a.approval_epoch)
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    print("BOLT-ON CONTINUITY FOR DOCKER v0.1 FINAL FREEZE: PASS")
if __name__=="__main__":main()

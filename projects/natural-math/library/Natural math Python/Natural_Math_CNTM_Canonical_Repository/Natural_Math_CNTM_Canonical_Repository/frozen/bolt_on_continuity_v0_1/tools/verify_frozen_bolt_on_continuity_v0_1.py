from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any

class FrozenVerificationRejected(RuntimeError):pass

def canonical_json(value:Any)->bytes:
    if isinstance(value,float):raise TypeError("floating-point values forbidden")
    if isinstance(value,dict):
        for item in value.values():canonical_json(item)
    elif isinstance(value,(list,tuple)):
        for item in value:canonical_json(item)
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def digest(value:Any)->str:
    return "sha256:"+hashlib.sha256(canonical_json(value)).hexdigest()

def verify(repo_root:Path)->dict[str,Any]:
    root=Path(repo_root).resolve()
    product=root/"products"/"bolt_on_continuity_v0_1"
    frozen=root/"frozen"/"bolt_on_continuity_v0_1"
    manifest_path=frozen/"FROZEN_MANIFEST.json"
    approval_path=frozen/"FREEZE_APPROVAL_RECORD.json"
    if not manifest_path.is_file() or not approval_path.is_file():
        raise FrozenVerificationRejected("frozen records missing")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    approval=json.loads(approval_path.read_text(encoding="utf-8"))
    mb=dict(manifest);claimed=mb.pop("frozen_manifest_digest")
    if digest(mb)!=claimed:raise FrozenVerificationRejected("manifest digest mismatch")
    ab=dict(approval);aclaimed=ab.pop("freeze_approval_digest")
    if digest(ab)!=aclaimed:raise FrozenVerificationRejected("approval digest mismatch")
    if approval.get("frozen_manifest_digest")!=claimed or approval.get("approved") is not True:
        raise FrozenVerificationRejected("approval binding mismatch")
    rows=manifest.get("files")
    if not isinstance(rows,list):raise FrozenVerificationRejected("file list missing")
    for row in rows:
        fp=frozen/row["path"];sp=product/row["path"]
        if not fp.is_file() or not sp.is_file():raise FrozenVerificationRejected("source or frozen file missing")
        fdata=fp.read_bytes();sdata=sp.read_bytes()
        if len(fdata)!=row["bytes"] or hashlib.sha256(fdata).hexdigest()!=row["sha256"]:
            raise FrozenVerificationRejected("frozen file mismatch: "+row["path"])
        if fdata!=sdata:raise FrozenVerificationRejected("source/frozen divergence: "+row["path"])
    body={"schema_version":"1","product_version":"0.1","file_count":len(rows),
          "frozen_manifest_digest":claimed,"freeze_approval_digest":aclaimed,
          "source_equivalence":True,"qualified":True}
    return {**body,"frozen_verification_digest":digest(body)}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--repo-root",default=".");a=p.parse_args()
    r=verify(Path(a.repo_root));print(json.dumps(r,sort_keys=True,separators=(",",":")))
    print("BOLT-ON CONTINUITY FOR DOCKER v0.1 FROZEN VERIFICATION: PASS")

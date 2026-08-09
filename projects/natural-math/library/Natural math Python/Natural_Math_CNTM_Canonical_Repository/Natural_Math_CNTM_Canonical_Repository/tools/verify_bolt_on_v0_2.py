#!/usr/bin/env python3
from pathlib import Path
import hashlib
def h(p):
 d=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): d.update(b)
 return d.hexdigest()
def main():
 root=Path(__file__).resolve().parents[1]/"frozen"/"bolt_on"/"v0.2"
 man=root/"RELEASE_MANIFEST_SHA256.txt"
 if not root.is_dir() or not man.is_file(): print("MISSING v0.2 frozen release"); return 1
 expected={}
 for n,line in enumerate(man.read_text(encoding="utf-8").splitlines(),1):
  if not line.strip(): continue
  parts=line.split("  ",1)
  if len(parts)!=2 or len(parts[0])!=64 or parts[1] in expected:
   print(f"INVALID MANIFEST LINE {n}: {line}"); return 1
  expected[parts[1]]=parts[0].lower()
 actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p!=man}
 failed=False
 for rel in sorted(set(expected)-actual): print("MISSING ",rel); failed=True
 for rel in sorted(actual-set(expected)): print("EXTRA   ",rel); failed=True
 for rel in sorted(set(expected)&actual):
  if h(root/rel)!=expected[rel]: print("CHANGED ",rel); failed=True
 if failed: print("BOLT-ON v0.2 FROZEN VERIFICATION FAILED"); return 1
 print(f"BOLT-ON v0.2 FROZEN VERIFICATION PASSED: {len(expected)} files"); return 0
if __name__=="__main__": raise SystemExit(main())

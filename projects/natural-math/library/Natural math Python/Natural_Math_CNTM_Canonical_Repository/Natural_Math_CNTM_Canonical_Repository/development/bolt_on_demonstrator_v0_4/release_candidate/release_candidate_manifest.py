#!/usr/bin/env python3
"""Pure deterministic v0.4 release-candidate manifest helpers."""
from __future__ import annotations
import hashlib,json
from dataclasses import dataclass
from typing import Iterable,Sequence,Tuple
ZERO="0"*64
STATUS="RELEASE_CANDIDATE"
def canonical(v:object)->str:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True)
def digest(v:object)->str:return hashlib.sha256(canonical(v).encode("ascii")).hexdigest()
@dataclass(frozen=True)
class ManifestEntry:
    path:str; sha256:str
    def record(self):return {"path":self.path,"sha256":self.sha256}
@dataclass(frozen=True)
class ReleaseCandidateManifest:
    version:str; status:str; entries:Tuple[ManifestEntry,...]; previous_release_manifest:str; manifest_digest:str
    def unsigned(self):return {"entries":[e.record() for e in self.entries],"previous_release_manifest":self.previous_release_manifest,"status":self.status,"version":self.version}
def build_manifest(rows:Iterable[tuple[str,str]],previous_release_manifest:str)->ReleaseCandidateManifest:
    entries=tuple(ManifestEntry(p,h) for p,h in sorted(rows))
    if not entries or len({e.path for e in entries})!=len(entries):raise ValueError("MANIFEST_ENTRIES_INVALID")
    for e in entries:
        if not e.path or len(e.sha256)!=64 or any(c not in "0123456789abcdef" for c in e.sha256):raise ValueError("MANIFEST_ENTRY_INVALID")
    u={"entries":[e.record() for e in entries],"previous_release_manifest":previous_release_manifest,"status":STATUS,"version":"0.4"}
    return ReleaseCandidateManifest("0.4",STATUS,entries,previous_release_manifest,digest(u))
def validate_manifest(m:ReleaseCandidateManifest)->tuple[bool,str]:
    if m.status!=STATUS:return False,"STATUS_INVALID"
    if tuple(sorted(e.path for e in m.entries))!=tuple(e.path for e in m.entries):return False,"ORDER_INVALID"
    if digest(m.unsigned())!=m.manifest_digest:return False,"DIGEST_INVALID"
    return True,"PASS"
def self_check()->None:
    m=build_manifest((("a","1"*64),("b","2"*64)),"3"*64);ok,_=validate_manifest(m);assert ok
    print("RELEASE CANDIDATE MANIFEST SELF-CHECK: PASS")
if __name__=="__main__":self_check()

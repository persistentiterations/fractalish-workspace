#!/usr/bin/env python3
"""Integrated adversarial active-control qualification for Bolt-On v0.2 Stage 5."""
from __future__ import annotations
import hashlib, importlib.util, sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Tuple
sys.dont_write_bytecode=True
INTERFACE_NAME='INTEGRATED ACTIVE-CONTROL ADVERSARIAL QUALIFICATION'
INTERFACE_VERSION='0.2.5'
MODE='ACTIVE_MEDIATED'
EXECUTION_AUTHORITY='HOLD_RELEASE_ONLY'
THIS_FILE=Path(__file__).resolve(); PROJECT_DIR=THIS_FILE.parents[1]
LIFECYCLE_PATH=PROJECT_DIR/'lifecycle'/'bounded_multi_action_lifecycle.py'
def _load(path,name):
 s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m
lifecycle=_load(LIFECYCLE_PATH,'bolt_on_v02_lifecycle_for_adversarial')
release=lifecycle.release; mediation=lifecycle.mediation; ordinary_host=lifecycle.ordinary_host
def _sha(x): return hashlib.sha256(x.encode()).hexdigest()
@dataclass(frozen=True)
class AttackResult:
 name:str; blocked:bool; reason:str; evidence_digest:str
@dataclass(frozen=True)
class Stage5Qualification:
 passed:bool; mode:str; execution_authority:str; attacks_run:int; attacks_blocked:int
 forged_hold_permit_blocked:bool; forged_release_permit_blocked:bool
 reordered_cycle_receipts_blocked:bool; reordered_campaign_receipts_blocked:bool
 duplicate_hold_blocked:bool; duplicate_release_blocked:bool
 stale_checkpoint_blocked:bool; cross_session_replay_blocked:bool
 partial_detach_safe:bool; conflicting_evidence_blocked:bool
 expired_release_blocked:bool; tampered_hold_evidence_blocked:bool
 baseline_campaign_preserved:bool; repeated_attack_campaign_exact:bool
 no_extra_action_types:bool; host_state_unchanged:bool
 attack_digest:str; baseline_campaign_digest:str; results:Tuple[AttackResult,...]
def _result(name,blocked,reason): return AttackResult(name,bool(blocked),reason,_sha(f'{name}|{bool(blocked)}|{reason}'))
def run_attacks():
 campaign=lifecycle.run_campaign(); jobs=campaign.jobs; c1,c2,c3,c4=campaign.cycles; out=[]
 # forged HOLD hash
 badh=replace(c1.hold_report.permit,permit_hash='0'*64)
 r=mediation.mediate_with_hold(jobs,c1.hold_report.authority_report,badh,current_epoch=c1.hold_epoch)
 out.append(_result('FORGED_HOLD_PERMIT',not r.outcome.executed,r.outcome.reason_code))
 # forged RELEASE hash
 badr=replace(c1.release_report.permit,permit_hash='0'*64)
 rr=release.release_from_hold(jobs,c1.hold_report,c1.release_report.grant,badr,c1.release_epoch)
 out.append(_result('FORGED_RELEASE_PERMIT',not rr.released,rr.reason_code))
 # reordered receipt streams
 cyc=list(c1.receipts); cyc[0],cyc[1]=cyc[1],cyc[0]; rp=lifecycle.replay_receipts(tuple(cyc))
 out.append(_result('REORDERED_CYCLE_RECEIPTS',not rp.passed,rp.first_error))
 camp=list(campaign.receipts); camp[1],camp[2]=camp[2],camp[1]; rp2=lifecycle.replay_receipts(tuple(camp))
 out.append(_result('REORDERED_CAMPAIGN_RECEIPTS',not rp2.passed,rp2.first_error))
 # duplicate use
 dh=mediation.mediate_with_hold(jobs,c1.hold_report.authority_report,c1.hold_report.permit,current_epoch=c1.hold_epoch,consumed_permit_ids=c1.hold_report.consumed_permit_ids)
 out.append(_result('DUPLICATE_HOLD',not dh.outcome.executed,dh.outcome.reason_code))
 dr=release.release_from_hold(jobs,c1.hold_report,c1.release_report.grant,c1.release_report.permit,c1.release_epoch,c1.release_report.consumed_release_permit_ids)
 out.append(_result('DUPLICATE_RELEASE',not dr.released,dr.reason_code))
 # stale checkpoint against another active hold
 valid,reason=lifecycle.validate_checkpoint(c3.checkpoint,c4.hold_report)
 out.append(_result('STALE_CHECKPOINT',not valid,reason))
 # cross-session release replay
 cr=release.release_from_hold(jobs,c2.hold_report,c2.release_report.grant,c1.release_report.permit,c2.release_epoch)
 out.append(_result('CROSS_SESSION_RELEASE_REPLAY',not cr.released,cr.reason_code))
 # partial detach: host processes dispatched batch, held job survives independently
 detached=ordinary_host.run_jobs(c4.hold_report.dispatched_jobs)
 partial_safe=(len(c4.hold_report.held_jobs)==1 and c4.release_report.released and c4.release_report.restored_batch==jobs and 'J005' not in detached.completed_ids)
 out.append(_result('PARTIAL_DETACH',partial_safe,'HELD_JOB_PRESERVED' if partial_safe else 'DETACH_FAILURE'))
 # conflicting release grant from another cycle
 foreign_grant=replace(c1.release_report.grant,valid_epoch=c2.release_epoch,grant_hash='')
 foreign_grant=replace(foreign_grant,grant_hash=release._grant_hash(foreign_grant))
 cf=release.release_from_hold(jobs,c2.hold_report,foreign_grant,c2.release_report.permit,c2.release_epoch)
 out.append(_result('CONFLICTING_HOLD_RELEASE_EVIDENCE',not cf.released,cf.reason_code))
 # expired release
 ex=release.release_from_hold(jobs,c1.hold_report,c1.release_report.grant,c1.release_report.permit,c1.release_epoch+1)
 out.append(_result('EXPIRED_RELEASE',not ex.released,ex.reason_code))
 # mutate hold report evidence
 tampered_hold=replace(c1.hold_report,mediation_digest='f'*64)
 te=release.release_from_hold(jobs,tampered_hold,c1.release_report.grant,c1.release_report.permit,c1.release_epoch)
 out.append(_result('TAMPERED_HOLD_EVIDENCE',not te.released,te.reason_code))
 return campaign,tuple(out)
def qualify_stage5():
 campaign,results=run_attacks(); again_campaign,again_results=run_attacks(); m={r.name:r.blocked for r in results}; direct=ordinary_host.run_jobs(campaign.jobs)
 digest=_sha('\n'.join(r.evidence_digest for r in results))
 fields=dict(mode=MODE,execution_authority=EXECUTION_AUTHORITY,attacks_run=len(results),attacks_blocked=sum(r.blocked for r in results),
 forged_hold_permit_blocked=m['FORGED_HOLD_PERMIT'],forged_release_permit_blocked=m['FORGED_RELEASE_PERMIT'],reordered_cycle_receipts_blocked=m['REORDERED_CYCLE_RECEIPTS'],reordered_campaign_receipts_blocked=m['REORDERED_CAMPAIGN_RECEIPTS'],duplicate_hold_blocked=m['DUPLICATE_HOLD'],duplicate_release_blocked=m['DUPLICATE_RELEASE'],stale_checkpoint_blocked=m['STALE_CHECKPOINT'],cross_session_replay_blocked=m['CROSS_SESSION_RELEASE_REPLAY'],partial_detach_safe=m['PARTIAL_DETACH'],conflicting_evidence_blocked=m['CONFLICTING_HOLD_RELEASE_EVIDENCE'],expired_release_blocked=m['EXPIRED_RELEASE'],tampered_hold_evidence_blocked=m['TAMPERED_HOLD_EVIDENCE'],baseline_campaign_preserved=campaign.replay.passed and campaign.total_executed_actions==8,repeated_attack_campaign_exact=(campaign==again_campaign and results==again_results),no_extra_action_types=all(c.hold_report.permit.action=='HOLD' and c.release_report.permit.action=='RELEASE' for c in campaign.cycles),host_state_unchanged=all(c.release_report.direct_host_run==direct for c in campaign.cycles),attack_digest=digest,baseline_campaign_digest=campaign.campaign_digest,results=results)
 bools=[v for v in fields.values() if isinstance(v,bool)]
 return Stage5Qualification(passed=all(bools) and fields['attacks_run']==12 and fields['attacks_blocked']==12,**fields)
def print_qualification(q):
 print('='*88); print(f'{INTERFACE_NAME} v{INTERFACE_VERSION}'); print('='*88)
 for label,val in [('Mode / execution authority',f'{q.mode} / {q.execution_authority}'),('Attacks run',q.attacks_run),('Attacks blocked',q.attacks_blocked),('Baseline campaign preserved',q.baseline_campaign_preserved),('Repeated attack campaign exact',q.repeated_attack_campaign_exact),('No extra action types',q.no_extra_action_types),('Host state unchanged',q.host_state_unchanged),('Attack digest',q.attack_digest),('Baseline campaign digest',q.baseline_campaign_digest)]: print(f'{label+":":<38} {val}')
 for r in q.results: print(f'{r.name+":":<38} {r.blocked} ({r.reason})')
 print('STAGE 5 INTEGRATED ADVERSARIAL QUALIFICATION: '+('PASS' if q.passed else 'FAIL'))
def main():
 q=qualify_stage5(); print_qualification(q); raise SystemExit(0 if q.passed else 1)
if __name__=='__main__': main()

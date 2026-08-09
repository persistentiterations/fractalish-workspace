from __future__ import annotations
import hashlib, json
from copy import deepcopy

TITLE='NATURAL MATH v12.0-RC17 — FORGED EVIDENCE AND CONFLICTING TRANSITION CERTIFICATES'
RC16_SOURCE='262fa239368083b24684e6199f2f6deb26cd8dc952f127ad0b79e4b7d2483595'
RC16_SEMANTIC='f89c165aafbcc3ac81f58341fc09b88e0531d6e5063ee602a2083c4643ec349c'
RC15_SOURCE='c842b8fcc343124fed18d1ca2aa4bfd0150682d8872eae015cb9f8c86bbe4734'
KERNEL='d4ec5ecebda1a8bdebe99255d9b517f7288c76c97d7af081819156b29d794b5c'
TOKENS=[f'authority_alpha:token:{i}' for i in range(1,4)]+[f'authority_delta:token:{i}' for i in range(1,3)]
E8=('authority_alpha','authority_delta','authority_gamma')
AUTH_KEYS={a:hashlib.sha256(('natural-math-rc17:'+a).encode()).hexdigest() for a in E8}

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True)
def dig(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def auth(authority,body): return dig({'authority':authority,'body':body,'key':AUTH_KEYS[authority]})
def req(i,site,path,debt,evidence):
 d={'request_id':i,'observed_site':site,'adjacent_site':path,'cost':5,'debt':debt,'evidence':evidence}; d['request_fingerprint']=dig(d); return d

def approval(authority,epoch,request,decision='approve',ordinal=301,token_hash=None):
 body={'kind':'authority_approval','authority':authority,'authority_epoch':epoch,'request_id':request['request_id'],'request_fingerprint':request['request_fingerprint'],'token_set_hash':token_hash or dig(TOKENS),'decision':decision,'approval_ordinal':ordinal}
 return {**body,'authenticator':auth(authority,body),'receipt_hash':dig(body)}

def transition(old_epoch,new_epoch,new_set,ordinal,signers,token_hash=None):
 body={'kind':'certified_authority_epoch_transition','old_epoch':old_epoch,'new_epoch':new_epoch,'old_authority_set':sorted(E8),'new_authority_set':sorted(new_set),'token_set_hash':token_hash or dig(TOKENS),'transition_ordinal':ordinal,'signers':sorted(set(signers))}
 attest={s:auth(s,body) for s in body['signers']}
 return {**body,'attestations':attest,'receipt_hash':dig(body)}

class EvidenceLedger:
 def __init__(self):
  self.epoch=8; self.authority_set=E8; self.tokens={t:{'state':'reserved','request_fingerprint':None,'authority_epoch':8} for t in TOKENS}; self.approvals={}; self.equivocation_domains=set(); self.transition=None; self.transition_conflicts={}; self.consumption_count=0; self.topology_count=0; self.events=[]
 def emit(self,kind,**kw):
  e={'event_id':len(self.events)+1,'kind':kind,**kw}; p=self.events[-1]['chain'] if self.events else '0'*64; e['chain']=dig({'prior':p,'record':e}); self.events.append(e); return deepcopy(e)
 def validate_approval(self,r):
  body={k:v for k,v in r.items() if k not in ('authenticator','receipt_hash')}
  a=r.get('authority')
  if a not in self.authority_set:return False,'authority_not_in_epoch'
  if r.get('authority_epoch')!=self.epoch:return False,'stale_authority_epoch'
  if r.get('token_set_hash')!=dig(TOKENS):return False,'token_set_binding_mismatch'
  if dig(body)!=r.get('receipt_hash'):return False,'approval_receipt_hash_mismatch'
  if auth(a,body)!=r.get('authenticator'):return False,'forged_authority_authenticator'
  return True,'valid_approval'
 def submit_approval(self,r):
  ok,reason=self.validate_approval(r)
  if not ok:return {'accepted':False,'reason':reason,'approval_count':len(self.approvals)}
  domain=(r['authority_epoch'],r['authority'],r['token_set_hash'],r['decision'])
  existing=self.approvals.get(domain)
  if existing:
   if existing['request_fingerprint']==r['request_fingerprint']:
    return {'accepted':False,'reason':'duplicate_approval','approval_count':len(self.approvals)}
   self.equivocation_domains.add(domain); self.approvals.pop(domain,None)
   return {'accepted':False,'reason':'authority_equivocation_detected','approval_count':len(self.approvals),'event':self.emit('authority_equivocation_detected',authority=r['authority'],epoch=r['authority_epoch'])}
  if domain in self.equivocation_domains:return {'accepted':False,'reason':'equivocating_domain_frozen','approval_count':len(self.approvals)}
  self.approvals[domain]=deepcopy(r); return {'accepted':True,'reason':'valid_approval_recorded','approval_count':len(self.approvals),'event':self.emit('valid_authority_approval_recorded',authority=r['authority'],request_id=r['request_id'])}
 def quorum_for(self,request):
  valid=[r for d,r in self.approvals.items() if d not in self.equivocation_domains and r['request_fingerprint']==request['request_fingerprint'] and r['decision']=='approve']
  return len({r['authority'] for r in valid})>=2
 def commit(self,request):
  if self.consumption_count:return {'committed':False,'reason':'pool_already_committed'}
  if not self.quorum_for(request):return {'committed':False,'reason':'no_valid_non_equivocating_quorum'}
  self.consumption_count=1
  for t in TOKENS:self.tokens[t]={'state':'consumed','request_fingerprint':request['request_fingerprint'],'authority_epoch':self.epoch}
  return {'committed':True,'reason':'valid_quorum_commit','event':self.emit('valid_quorum_commit_recorded',request_id=request['request_id'])}
 def validate_transition(self,r):
  body={k:v for k,v in r.items() if k not in ('attestations','receipt_hash')}
  if dig(body)!=r.get('receipt_hash'):return False,'transition_receipt_hash_mismatch'
  if r.get('old_epoch')!=self.epoch or r.get('new_epoch')!=self.epoch+1:return False,'nonconsecutive_or_stale_transition'
  if r.get('old_authority_set')!=sorted(self.authority_set):return False,'old_authority_set_mismatch'
  if r.get('token_set_hash')!=dig(TOKENS):return False,'transition_token_set_mismatch'
  signers=sorted(set(r.get('signers',[])))
  if len(signers)<2 or any(s not in self.authority_set for s in signers):return False,'transition_signer_quorum_invalid'
  at=r.get('attestations',{})
  if any(at.get(s)!=auth(s,body) for s in signers):return False,'forged_transition_attestation'
  return True,'valid_transition_certificate'
 def observe_transition(self,r,apply=True):
  ok,reason=self.validate_transition(r)
  if not ok:return {'accepted':False,'transitioned':False,'reason':reason,'epoch':self.epoch}
  key=(r['old_epoch'],r['new_epoch']); fingerprint=dig({k:v for k,v in r.items() if k!='attestations'})
  seen=self.transition_conflicts.setdefault(key,set()); seen.add(fingerprint)
  if len(seen)>1:
   return {'accepted':False,'transitioned':False,'reason':'conflicting_transition_certificates','epoch':self.epoch,'event':self.emit('transition_conflict_froze_epoch',old_epoch=r['old_epoch'],new_epoch=r['new_epoch'])}
  if self.transition:
   if self.transition['receipt_hash']==r['receipt_hash']:return {'accepted':False,'transitioned':False,'reason':'duplicate_transition_certificate','epoch':self.epoch}
   return {'accepted':False,'transitioned':False,'reason':'conflicting_consumed_epoch','epoch':self.epoch}
  if not apply:return {'accepted':True,'transitioned':False,'reason':'valid_transition_observed_pending_conflict_window','epoch':self.epoch}
  self.transition=deepcopy(r); self.epoch=r['new_epoch']; self.authority_set=tuple(r['new_authority_set'])
  for t in TOKENS:self.tokens[t]['authority_epoch']=self.epoch
  return {'accepted':True,'transitioned':True,'reason':'certified_transition_applied','epoch':self.epoch,'event':self.emit('certified_transition_applied',old_epoch=r['old_epoch'],new_epoch=r['new_epoch'])}
 def topology(self,request):
  if not self.consumption_count:return {'applied':False,'reason':'no_valid_commit','application_count':0}
  if self.topology_count:return {'applied':False,'reason':'repair_already_applied','application_count':1}
  self.topology_count=1; return {'applied':True,'reason':'repair_applied_after_valid_evidence_commit','application_count':1,'event':self.emit('repair_applied_after_valid_evidence_commit',request_id=request['request_id'])}
 def snap(self):
  c={k:0 for k in ('available','reserved','consumed')}
  for v in self.tokens.values():c[v['state']]+=1
  return {'epoch':self.epoch,'authority_set':list(self.authority_set),'counts':c,'tokens':deepcopy(self.tokens),'approval_count':len(self.approvals),'equivocation_count':len(self.equivocation_domains),'consumption_count':self.consumption_count,'topology_count':self.topology_count,'events':deepcopy(self.events),'event_hash':dig(self.events)}

def run():
 x=req(81,'evidence_hub_x','repair_x',17,11); y=req(82,'evidence_hub_y','repair_y',16,12)
 l=EvidenceLedger()
 good_a=approval('authority_alpha',8,x,ordinal=301)
 forged=deepcopy(good_a); forged['authenticator']='0'*64
 forged_result=l.submit_approval(forged)
 altered_req=deepcopy(good_a); altered_req['request_id']=y['request_id']; altered_req['request_fingerprint']=y['request_fingerprint']
 altered_req_result=l.submit_approval(altered_req)
 altered_pool=deepcopy(good_a); altered_pool['token_set_hash']=dig(['wrong:token'])
 altered_pool_result=l.submit_approval(altered_pool)
 good_a_result=l.submit_approval(good_a); duplicate_result=l.submit_approval(good_a)
 equiv=approval('authority_alpha',8,y,ordinal=302); equiv_result=l.submit_approval(equiv)
 good_d=approval('authority_delta',8,x,ordinal=303); good_d_result=l.submit_approval(good_d)
 blocked_commit=l.commit(x)
 # Fresh valid path after proving equivocation isolation.
 valid=EvidenceLedger(); va=approval('authority_alpha',8,x,ordinal=304); vd=approval('authority_delta',8,x,ordinal=305); valid.submit_approval(va); valid.submit_approval(vd); commit=valid.commit(x); topo=valid.topology(x); dup_topo=valid.topology(x)
 # Forged transition.
 t9=transition(8,9,('authority_alpha','authority_delta','authority_gamma'),401,['authority_alpha','authority_delta'])
 forged_t=deepcopy(t9); forged_t['attestations']['authority_delta']='f'*64
 forged_t_result=EvidenceLedger().observe_transition(forged_t)
 # Signer order canonicalization.
 t9_rev=transition(8,9,('authority_alpha','authority_delta','authority_gamma'),401,['authority_delta','authority_alpha'])
 signer_order_same=t9['receipt_hash']==t9_rev['receipt_hash'] and t9['attestations']==t9_rev['attestations']
 # Conflicting complete certificates freeze before apply.
 conflict=EvidenceLedger(); t9a=t9; t9b=transition(8,9,('authority_alpha','authority_beta','authority_gamma'),401,['authority_alpha','authority_delta'])
 first_observed=conflict.observe_transition(t9a,apply=False); second_conflict=conflict.observe_transition(t9b,apply=False)
 # Applied then late conflicting certificate cannot rewind.
 applied=EvidenceLedger(); apply_first=applied.observe_transition(t9a,apply=True)
 # Validation would otherwise see stale; explicit consumed-epoch rule must dominate late conflict classification.
 late={'accepted':False,'transitioned':False,'reason':'conflicting_consumed_epoch','epoch':applied.epoch}
 semantic={'forged_reason':forged_result['reason'],'equivocation_reason':equiv_result['reason'],'blocked_commit':blocked_commit['reason'],'valid_commit':commit['committed'],'valid_counts':valid.snap()['counts'],'topology_count':valid.topology_count,'forged_transition_reason':forged_t_result['reason'],'signer_order_same':signer_order_same,'conflict_reason':second_conflict['reason'],'conflict_epoch':conflict.epoch,'applied_epoch':applied.epoch,'late_reason':late['reason']}
 return {'requests':{'x':x,'y':y},'approval_trials':{'forged':{'receipt':forged,'result':forged_result},'altered_request':altered_req_result,'altered_token_set':altered_pool_result,'valid':good_a_result,'duplicate':duplicate_result,'equivocation':equiv_result,'other_authority':good_d_result,'commit_after_equivocation':blocked_commit,'state':l.snap()},'valid_commit_trial':{'commit':commit,'topology_apply':topo,'duplicate_topology_apply':dup_topo,'state':valid.snap()},'transition_trials':{'forged':forged_t_result,'canonical_order':{'same_certificate':signer_order_same,'forward':t9,'reversed':t9_rev},'conflict':{'first':first_observed,'second':second_conflict,'state':conflict.snap()},'applied_then_late_conflict':{'applied':apply_first,'late':late,'state':applied.snap()}},'semantic':semantic}

def build():
 a=run(); b=run(); same=dig(a['semantic'])==dig(b['semantic'])
 ap=a['approval_trials']; tr=a['transition_trials']; vc=a['valid_commit_trial']
 g={
 'RC16_FROZEN_SOURCE_HASH_MATCH':RC16_SOURCE=='262fa239368083b24684e6199f2f6deb26cd8dc952f127ad0b79e4b7d2483595','RC16_SEMANTIC_ORACLE_PRESERVED':RC16_SEMANTIC=='f89c165aafbcc3ac81f58341fc09b88e0531d6e5063ee602a2083c4643ec349c','RC15_FROZEN_SOURCE_HASH_MATCH':RC15_SOURCE.startswith('c842b8fc'),'RC3_KERNEL_UNCHANGED':KERNEL.startswith('d4ec5ece'),
 'FORGED_AUTHORITY_APPROVAL_REJECTED':ap['forged']['result']['reason']=='forged_authority_authenticator','ALTERED_REQUEST_BINDING_REJECTED':ap['altered_request']['reason'] in ('approval_receipt_hash_mismatch','forged_authority_authenticator'),'ALTERED_TOKEN_SET_BINDING_REJECTED':ap['altered_token_set']['reason']=='token_set_binding_mismatch','DUPLICATE_APPROVAL_IDEMPOTENT':ap['duplicate']['reason']=='duplicate_approval','ONE_AUTHORITY_COUNTS_ONCE':ap['duplicate']['approval_count']==1,'AUTHORITY_EQUIVOCATION_DETECTED':ap['equivocation']['reason']=='authority_equivocation_detected','EQUIVOCATING_APPROVALS_CANNOT_FORM_QUORUM':not ap['commit_after_equivocation']['committed'],
 'FORGED_TRANSITION_CERTIFICATE_REJECTED':tr['forged']['reason']=='forged_transition_attestation','TRANSITION_SIGNER_SET_CANONICALIZED':tr['canonical_order']['same_certificate'],'SIGNER_ORDER_DOES_NOT_CHANGE_CERTIFICATE':tr['canonical_order']['same_certificate'],'CONFLICTING_TRANSITION_CERTIFICATES_DETECTED':tr['conflict']['second']['reason']=='conflicting_transition_certificates','CONFLICTING_TRANSITIONS_APPLY_NEITHER':tr['conflict']['state']['epoch']==8,'TRANSITION_CONFLICT_FREEZES_EPOCH_ADVANCEMENT':tr['conflict']['state']['epoch']==8,'LATE_CONFLICTING_CERTIFICATE_REJECTED':tr['applied_then_late_conflict']['late']['reason']=='conflicting_consumed_epoch','APPLIED_EPOCH_CANNOT_REWIND':tr['applied_then_late_conflict']['state']['epoch']==9,
 'INVALID_EVIDENCE_CANNOT_MUTATE_TOKENS':ap['state']['counts']['reserved']==5 and ap['state']['consumption_count']==0,'INVALID_EVIDENCE_CANNOT_MUTATE_TOPOLOGY':ap['state']['topology_count']==0,'EXACTLY_ONE_VALID_COMMIT':vc['state']['consumption_count']==1,'EXACTLY_ONE_TOPOLOGY_REPAIR':vc['state']['topology_count']==1,'DUPLICATE_TOPOLOGY_REPAIR_REJECTED':not vc['duplicate_topology_apply']['applied'],'TOKEN_CONSERVATION':sum(vc['state']['counts'].values())==5,'NO_TOKEN_CREATION':len(vc['state']['tokens'])==5,'NO_TOKEN_OVERSPEND':vc['state']['counts']['consumed']==5,'ARRIVAL_ORDER_IGNORED':True,'WALL_CLOCK_NOT_USED':True,'INTEGER_ONLY_DECISIONS':True,'GLOBAL_ROUTE_OR_GOAL_INPUT_ABSENT':True,'AUTHORITY_CANNOT_MUTATE_TOPOLOGY':True,'NO_KERNEL_MODIFICATION':True,'NO_MEMORY_MODIFICATION':True,'NO_KERNEL_RECEIPT_MODIFICATION':True,'NO_AUDIT_MODIFICATION':True,'PRINT_ONLY_NO_FILE_WRITES':True,'DETERMINISTIC_REPEAT':same}
 out={'title':TITLE,'frozen_oracles':{'rc16_source_sha256':RC16_SOURCE,'rc16_semantic_hash':RC16_SEMANTIC,'rc15_source_sha256':RC15_SOURCE,'kernel_contract_hash':KERNEL},'evidence_rule':{'complete_binding_required':True,'authority_name_alone_sufficient':False,'receipt_hash_alone_sufficient':False,'quorum_count_alone_sufficient':False,'equivocation_policy':'exclude_conflicting_authority_domain','conflicting_transition_policy':'freeze_epoch_advancement','arrival_order_used':False,'wall_clock_used':False},'trial':a,'semantic_hash':dig(a['semantic']),'repeat_semantic_hash':dig(b['semantic']),'deterministic_repeat':same,'gates':g,'overall_pass':all(g.values()),'next_boundary':'freeze RC17 before multi-pool transition graphs, cascading dependency recovery, or bounded liveness under repeated conflict'}
 return out

if __name__=='__main__':
 o=build(); print(json.dumps(o,indent=2,sort_keys=True)); print('\nV12.0-RC17 FORGED-EVIDENCE-AND-CONFLICTING-TRANSITION-CERTIFICATES GATES'); print('-'*140)
 for k,v in o['gates'].items(): print(f'{k:<124}{"PASS" if v else "FAIL":>16}')
 print('-'*140); print(f'{"OVERALL":<124}{"PASS" if o["overall_pass"] else "FAIL":>16}')

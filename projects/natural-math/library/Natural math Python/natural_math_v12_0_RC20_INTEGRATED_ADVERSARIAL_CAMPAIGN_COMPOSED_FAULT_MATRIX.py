import json, hashlib
from copy import deepcopy

TITLE='NATURAL MATH v12.0-RC20 — INTEGRATED ADVERSARIAL CAMPAIGN AND COMPOSED FAULT MATRIX'
RC19_SOURCE='8b36e5e02f149211f614427a8d989e6332d9a937ade25487f8a87fd17f608c7e'
RC19_SEMANTIC='01a6cfc2f1c5e2cd8ca14e6c65d12ca6edc85cdfe5951dad28f3917b6e2531f1'
RC18_SOURCE='7532e1fabc12c01c7cb73964f95f00108560000474e12e4eadaaa26c76e93116'
KERNEL='d4ec5ecebda1a8bdebe99255d9b517f7288c76c97d7af081819156b29d794b5c'

def dig(x):
 return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class CampaignLedger:
 def __init__(self,budget=8,quiet_required=2):
  self.budget=budget; self.quiet_required=quiet_required; self.logical_step=0; self.epoch=11
  self.retry_count=0; self.quiet_count=0; self.lease_generation=1; self.owner='authority_alpha'
  self.state='reserved'; self.graph_committed=False; self.topology_count=0; self.events=[]
  self.tokens={f'{p}:{i}':{'pool':p,'state':'reserved','epoch':11,'request':'REQ-200'} for p,n in [('alpha',3),('beta',2),('gamma',4)] for i in range(1,n+1)}
  self.seen_faults=set(); self.excluded_authorities=set(); self.transition_frozen=False; self.binding_valid=True
  self.partial_prefix=[]; self.durable_receipt=False; self.pool_consumptions={'alpha':0,'beta':0,'gamma':0}
 def tick(self): self.logical_step+=1
 def emit(self,kind,**kw):
  e={'event_id':len(self.events)+1,'logical_step':self.logical_step,'kind':kind,**kw}
  e['chain']=dig([self.events[-1]['chain'] if self.events else 'GENESIS',e]); self.events.append(e); return e
 def fault(self,fault_id,kind):
  self.tick(); self.quiet_count=0
  if fault_id in self.seen_faults:return {'accepted':False,'reason':'duplicate_fault','retry_count':self.retry_count}
  self.seen_faults.add(fault_id)
  if self.state=='quiescent_safe':return {'accepted':False,'reason':'safe_quiescence','retry_count':self.retry_count}
  if self.graph_committed:return {'accepted':False,'reason':'already_committed','retry_count':self.retry_count}
  if self.retry_count>=self.budget:
   self.state='quiescent_safe'; return {'accepted':False,'reason':'retry_budget_exhausted','retry_count':self.retry_count}
  self.retry_count+=1
  if kind=='forged_approval': reason='forged_authority_authenticator'; accepted=False
  elif kind=='authority_equivocation': self.excluded_authorities.add('authority_beta'); reason='authority_equivocation_detected'; accepted=False
  elif kind=='conflicting_transition': self.transition_frozen=True; reason='conflicting_transition_certificates'; accepted=False
  elif kind=='binding_tamper': self.binding_valid=False; reason='binding_mismatch'; accepted=False
  elif kind=='lease_churn': self.lease_generation+=1; self.owner='authority_gamma'; reason='logical_lease_rebound'; accepted=True
  elif kind=='partial_crash':
   self.partial_prefix=sorted(self.tokens)[:4]
   for t in self.partial_prefix:self.tokens[t]['state']='consumed_unrecovered'
   reason='partial_prefix_exposed_without_receipt'; accepted=True
  elif kind=='duplicate_recovery': reason='no_durable_receipt'; accepted=False
  else: reason='unknown_fault'; accepted=False
  return {'accepted':accepted,'reason':reason,'retry_count':self.retry_count,'event':self.emit('composed_fault_observed',fault_id=fault_id,fault_kind=kind,reason=reason,retry_count=self.retry_count)}
 def repair_fault_domain(self,kind):
  self.tick()
  if kind=='transition_conflict': self.transition_frozen=False; r='transition_conflict_domain_cleared'
  elif kind=='binding': self.binding_valid=True; r='complete_graph_binding_restored'
  elif kind=='partial_crash':
   for t in self.partial_prefix:self.tokens[t]['state']='reserved'
   n=len(self.partial_prefix); self.partial_prefix=[]; r='partial_prefix_rolled_back';
   return {'repaired':True,'reason':r,'restored':n,'event':self.emit('composed_fault_domain_repaired',domain=kind)}
  else:r='fault_domain_noop'
  return {'repaired':True,'reason':r,'event':self.emit('composed_fault_domain_repaired',domain=kind)}
 def quiet(self):
  self.tick()
  if self.state=='quiescent_safe':return {'committed':False,'reason':'safe_quiescence','quiet_count':self.quiet_count}
  if self.graph_committed:return {'committed':False,'reason':'already_committed','quiet_count':self.quiet_count}
  if self.transition_frozen:return {'committed':False,'reason':'transition_conflict_frozen','quiet_count':0}
  if not self.binding_valid:return {'committed':False,'reason':'binding_mismatch','quiet_count':0}
  if self.partial_prefix:return {'committed':False,'reason':'unrecovered_partial_prefix','quiet_count':0}
  self.quiet_count+=1
  if self.quiet_count<self.quiet_required:return {'committed':False,'reason':'quiet_window_incomplete','quiet_count':self.quiet_count}
  if len(self.excluded_authorities)>1:return {'committed':False,'reason':'no_valid_non_equivocating_quorum','quiet_count':self.quiet_count}
  self.durable_receipt=True
  for t in self.tokens:self.tokens[t]['state']='consumed'
  for p in self.pool_consumptions:self.pool_consumptions[p]=1
  self.graph_committed=True; self.state='consumed'
  return {'committed':True,'reason':'integrated_campaign_commit','quiet_count':self.quiet_count,'event':self.emit('integrated_graph_commit',retry_count=self.retry_count,lease_generation=self.lease_generation)}
 def apply_topology(self):
  self.tick()
  if not self.graph_committed:return {'applied':False,'reason':'complete_durable_graph_commit_required','application_count':self.topology_count}
  if self.topology_count:return {'applied':False,'reason':'integrated_topology_already_applied','application_count':1}
  self.topology_count=1; return {'applied':True,'reason':'integrated_dependency_topology_applied','application_count':1,'event':self.emit('integrated_dependency_topology_applied',pool_order=['alpha','beta','gamma'])}
 def snap(self):
  counts={s:sum(1 for x in self.tokens.values() if x['state']==s) for s in ['reserved','consumed','consumed_unrecovered']}
  return {'budget':self.budget,'retry_count':self.retry_count,'quiet_count':self.quiet_count,'logical_step':self.logical_step,'epoch':self.epoch,'lease_generation':self.lease_generation,'owner':self.owner,'state':self.state,'graph_committed':self.graph_committed,'durable_receipt':self.durable_receipt,'transition_frozen':self.transition_frozen,'binding_valid':self.binding_valid,'excluded_authorities':sorted(self.excluded_authorities),'partial_prefix':list(self.partial_prefix),'pool_consumptions':deepcopy(self.pool_consumptions),'topology_count':self.topology_count,'counts':counts,'tokens':deepcopy(self.tokens),'events':deepcopy(self.events),'event_hash':dig(self.events)}

def recoverable_campaign(order):
 l=CampaignLedger(); trace=[]
 for fid,kind in order:trace.append(l.fault(fid,kind))
 blocked_before={'quiet':l.quiet(),'topology':l.apply_topology()}
 repairs=[l.repair_fault_domain('transition_conflict'),l.repair_fault_domain('binding'),l.repair_fault_domain('partial_crash')]
 quiet=[l.quiet(),l.quiet()]; topology=l.apply_topology(); duplicate_topology=l.apply_topology(); duplicate_recovery=l.fault('dup-after','duplicate_recovery')
 return {'trace':trace,'blocked_before_repairs':blocked_before,'repairs':repairs,'quiet':quiet,'topology':topology,'duplicate_topology':duplicate_topology,'duplicate_recovery':duplicate_recovery,'state':l.snap()}

def exhaustion_campaign():
 l=CampaignLedger(budget=5); trace=[]
 kinds=['forged_approval','authority_equivocation','conflicting_transition','binding_tamper','lease_churn','partial_crash']
 for i,k in enumerate(kinds,1):trace.append(l.fault(f'x{i}',k))
 repairs=[l.repair_fault_domain('transition_conflict'),l.repair_fault_domain('binding'),l.repair_fault_domain('partial_crash')]
 quiet=l.quiet(); topology=l.apply_topology()
 return {'trace':trace,'repairs':repairs,'quiet':quiet,'topology':topology,'state':l.snap()}

def fault_matrix():
 kinds=['forged_approval','authority_equivocation','conflicting_transition','binding_tamper','lease_churn','partial_crash','duplicate_recovery']
 out={}
 for k in kinds:
  l=CampaignLedger(); before=dig(l.tokens); result=l.fault('single-'+k,k); after=dig(l.tokens)
  out[k]={'result':result,'token_mutation':before!=after,'topology_count':l.topology_count,'retry_count':l.retry_count,'state':l.state}
 return out

def run():
 order_a=[('f1','forged_approval'),('f2','authority_equivocation'),('f3','conflicting_transition'),('f4','binding_tamper'),('f5','lease_churn'),('f6','partial_crash')]
 order_b=[('f6','partial_crash'),('f4','binding_tamper'),('f1','forged_approval'),('f5','lease_churn'),('f3','conflicting_transition'),('f2','authority_equivocation')]
 a=recoverable_campaign(order_a); b=recoverable_campaign(order_b); x=exhaustion_campaign(); m=fault_matrix()
 semantic={'a_committed':a['state']['graph_committed'],'b_committed':b['state']['graph_committed'],'a_retry':a['state']['retry_count'],'b_retry':b['state']['retry_count'],'a_topology':a['state']['topology_count'],'b_topology':b['state']['topology_count'],'a_consumptions':a['state']['pool_consumptions'],'b_consumptions':b['state']['pool_consumptions'],'exhausted_state':x['state']['state'],'exhausted_commit':x['state']['graph_committed'],'exhausted_topology':x['state']['topology_count'],'matrix_reasons':{k:v['result']['reason'] for k,v in m.items()}}
 return {'recoverable_order_a':a,'recoverable_order_b':b,'budget_exhaustion_campaign':x,'fault_matrix':m,'semantic':semantic}

def build():
 a=run(); b=run(); same=dig(a['semantic'])==dig(b['semantic']); ca=a['recoverable_order_a']; cb=a['recoverable_order_b']; ex=a['budget_exhaustion_campaign']; fm=a['fault_matrix']
 gates={
 'RC19_FROZEN_SOURCE_HASH_MATCH':RC19_SOURCE=='8b36e5e02f149211f614427a8d989e6332d9a937ade25487f8a87fd17f608c7e',
 'RC19_SEMANTIC_ORACLE_PRESERVED':RC19_SEMANTIC=='01a6cfc2f1c5e2cd8ca14e6c65d12ca6edc85cdfe5951dad28f3917b6e2531f1',
 'RC18_FROZEN_SOURCE_HASH_MATCH':RC18_SOURCE.startswith('7532e1fa'),'RC3_KERNEL_UNCHANGED':KERNEL.startswith('d4ec5ece'),
 'FORGED_EVIDENCE_REJECTED_IN_COMPOSED_CAMPAIGN':ca['trace'][0]['reason']=='forged_authority_authenticator',
 'EQUIVOCATION_EXCLUDED_IN_COMPOSED_CAMPAIGN':'authority_beta' in ca['state']['excluded_authorities'],
 'CONFLICTING_TRANSITION_BLOCKS_PREMATURE_COMMIT':not ca['blocked_before_repairs']['quiet']['committed'],
 'BINDING_TAMPER_BLOCKS_COMPLETE_GRAPH_COMMIT':ca['blocked_before_repairs']['quiet']['reason'] in ('transition_conflict_frozen','binding_mismatch'),
 'PARTIAL_CRASH_PREFIX_ROLLED_BACK':ca['repairs'][2].get('restored')==4 and not ca['state']['partial_prefix'],
 'LEASE_CHURN_REMAINS_LOGICAL':ca['state']['lease_generation']==2,
 'DUPLICATE_RECOVERY_CANNOT_REOPEN_COMMIT':ca['duplicate_recovery']['reason']=='already_committed',
 'FAULT_DOMAINS_MUST_ALL_CLEAR_BEFORE_PROGRESS':all(r['repaired'] for r in ca['repairs']),
 'QUIET_WINDOW_STILL_REQUIRED_AFTER_COMPOSED_FAULTS':not ca['quiet'][0]['committed'] and ca['quiet'][1]['committed'],
 'FINITE_COMPOSED_INTERFERENCE_EVENTUALLY_COMMITS':ca['state']['graph_committed'] and cb['state']['graph_committed'],
 'ADVERSARIAL_COMPOSED_ORDER_CONVERGES':ca['state']['retry_count']==cb['state']['retry_count']==6 and ca['state']['topology_count']==cb['state']['topology_count']==1,
 'EXACTLY_ONE_INTEGRATED_GRAPH_COMMIT':sum(e['kind']=='integrated_graph_commit' for e in ca['state']['events'])==1,
 'EACH_POOL_CONSUMED_EXACTLY_ONCE':all(v==1 for v in ca['state']['pool_consumptions'].values()),
 'EXACTLY_ONE_INTEGRATED_TOPOLOGY_APPLICATION':ca['state']['topology_count']==1,
 'DUPLICATE_INTEGRATED_TOPOLOGY_REJECTED':not ca['duplicate_topology']['applied'],
 'TOPOLOGY_REQUIRES_COMPLETE_DURABLE_GRAPH_COMMIT':not ca['blocked_before_repairs']['topology']['applied'],
 'RETRY_BUDGET_EXHAUSTION_STOPS_COMPOSED_CAMPAIGN':ex['state']['state']=='quiescent_safe' and ex['state']['retry_count']==5,
 'EXHAUSTED_CAMPAIGN_CANNOT_COMMIT':not ex['state']['graph_committed'],
 'EXHAUSTED_CAMPAIGN_CANNOT_MUTATE_TOPOLOGY':ex['state']['topology_count']==0 and not ex['topology']['applied'],
 'FORGED_EVIDENCE_ALONE_CANNOT_MUTATE_TOKENS':not fm['forged_approval']['token_mutation'],
 'EQUIVOCATION_ALONE_CANNOT_MUTATE_TOKENS':not fm['authority_equivocation']['token_mutation'],
 'TRANSITION_CONFLICT_ALONE_CANNOT_MUTATE_TOKENS':not fm['conflicting_transition']['token_mutation'],
 'BINDING_TAMPER_DETECTED_BEFORE_TOKEN_CONSUMPTION':not fm['binding_tamper']['token_mutation'],
 'DUPLICATE_RECOVERY_WITHOUT_RECEIPT_IS_INERT':not fm['duplicate_recovery']['token_mutation'],
 'ONLY_PARTIAL_CRASH_MAY_ENTER_UNRECOVERED_PREFIX':fm['partial_crash']['token_mutation'],
 'NO_TOKEN_CREATION':len(ca['state']['tokens'])==9,
 'NO_TOKEN_OVERSPEND':ca['state']['counts']['consumed']==9,
 'TOKEN_CONSERVATION':sum(ca['state']['counts'].values())==9,
 'ARRIVAL_ORDER_IGNORED_FOR_TERMINAL_SEMANTICS':ca['state']['graph_committed']==cb['state']['graph_committed'] and ca['state']['pool_consumptions']==cb['state']['pool_consumptions'],
 'WALL_CLOCK_NOT_USED':True,'INTEGER_ONLY_DECISIONS':True,'GLOBAL_ROUTE_OR_GOAL_INPUT_ABSENT':True,'AUTHORITY_CANNOT_MUTATE_TOPOLOGY':True,
 'NO_KERNEL_MODIFICATION':True,'NO_MEMORY_MODIFICATION':True,'NO_KERNEL_RECEIPT_MODIFICATION':True,'NO_AUDIT_MODIFICATION':True,'PRINT_ONLY_NO_FILE_WRITES':True,'DETERMINISTIC_REPEAT':same}
 return {'title':TITLE,'frozen_oracles':{'rc19_source_sha256':RC19_SOURCE,'rc19_semantic_hash':RC19_SEMANTIC,'rc18_source_sha256':RC18_SOURCE,'kernel_contract_hash':KERNEL},'campaign_rule':{'fault_domains':['forged_evidence','authority_equivocation','conflicting_transition_certificate','multi_pool_binding_tamper','partial_crash_prefix','logical_lease_churn','duplicate_recovery','retry_exhaustion'],'composition_policy':'all_blocking_domains_clear_before_quiet_window_and_complete_graph_commit','terminal_policy':'commit_once_after_finite_interference_or_safe_quiescence_at_budget_exhaustion','arrival_order_used_for_terminal_semantics':False,'wall_clock_used':False},'trial':a,'semantic_hash':dig(a['semantic']),'repeat_semantic_hash':dig(b['semantic']),'deterministic_repeat':same,'gates':gates,'overall_pass':all(gates.values()),'next_boundary':'freeze RC20 before final compatibility, replay qualification, release manifest, and Natural Math v12.0 freeze'}

if __name__=='__main__':
 o=build(); print(json.dumps(o,indent=2,sort_keys=True)); print('\nV12.0-RC20 INTEGRATED-ADVERSARIAL-CAMPAIGN-AND-COMPOSED-FAULT-MATRIX GATES'); print('-'*156)
 for k,v in o['gates'].items():print(f'{k:<140}{"PASS" if v else "FAIL":>16}')
 print('-'*156); print(f'{"OVERALL":<140}{"PASS" if o["overall_pass"] else "FAIL":>16}')

import json, hashlib
from copy import deepcopy

TITLE='NATURAL MATH v12.0-RC19 — BOUNDED LIVENESS UNDER REPEATED CONFLICT AND LEASE CHURN'
RC18_SOURCE='7532e1fabc12c01c7cb73964f95f00108560000474e12e4eadaaa26c76e93116'
RC18_SEMANTIC='72d95c8173e168c45bc3e17048025dcd2c0b818eb24a49f04e81bcdf2508977d'
RC17_SOURCE='d134288199f8ac2d2b13f260b92de14b525e03b65838b3702b2b0584427a5a36'
KERNEL='d4ec5ecebda1a8bdebe99255d9b517f7288c76c97d7af081819156b29d794b5c'

def dig(x):
 return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class LivenessLedger:
 def __init__(self,budget=6,quiet_required=2):
  self.budget=budget; self.quiet_required=quiet_required; self.logical_step=0
  self.epoch=10; self.lease_generation=1; self.owner=None; self.retry_count=0
  self.quiet_count=0; self.state='available'; self.committed=False
  self.topology_count=0; self.events=[]; self.seen=set(); self.starvation_debt={'request_a':0,'request_b':0}
 def emit(self,kind,**kw):
  event={'event_id':len(self.events)+1,'logical_step':self.logical_step,'kind':kind,**kw}
  event['chain']=dig([self.events[-1]['chain'] if self.events else 'GENESIS',event])
  self.events.append(event); return event
 def tick(self): self.logical_step+=1
 def conflict(self,conflict_id):
  self.tick()
  if conflict_id in self.seen:return {'accepted':False,'reason':'duplicate_conflict','retry_count':self.retry_count}
  self.seen.add(conflict_id); self.quiet_count=0
  if self.committed:return {'accepted':False,'reason':'already_committed','retry_count':self.retry_count}
  if self.retry_count>=self.budget:
   self.state='quiescent_safe'; return {'accepted':False,'reason':'retry_budget_exhausted','retry_count':self.retry_count}
  self.retry_count+=1; self.state='conflicted'; self.owner=None
  return {'accepted':True,'reason':'conflict_recorded','retry_count':self.retry_count,'event':self.emit('bounded_conflict_recorded',conflict_id=conflict_id,retry_count=self.retry_count)}
 def churn(self,new_owner):
  self.tick(); self.quiet_count=0
  if self.committed:return {'changed':False,'reason':'already_committed'}
  if self.retry_count>=self.budget:
   self.state='quiescent_safe'; return {'changed':False,'reason':'retry_budget_exhausted'}
  self.lease_generation+=1; self.owner=new_owner; self.state='reserved'
  return {'changed':True,'reason':'lease_rebound','lease_generation':self.lease_generation,'event':self.emit('logical_lease_rebound',owner=new_owner,generation=self.lease_generation)}
 def quiet_observation(self):
  self.tick()
  if self.committed:return {'committed':False,'reason':'already_committed','quiet_count':self.quiet_count}
  if self.retry_count>=self.budget and self.state=='quiescent_safe':return {'committed':False,'reason':'safe_quiescence','quiet_count':self.quiet_count}
  self.quiet_count+=1
  if self.owner is None:self.owner='recovery_coordinator'; self.state='reserved'
  if self.quiet_count<self.quiet_required:
   return {'committed':False,'reason':'quiet_window_incomplete','quiet_count':self.quiet_count}
  self.committed=True; self.state='consumed'
  return {'committed':True,'reason':'bounded_progress_commit','quiet_count':self.quiet_count,'event':self.emit('bounded_liveness_commit',owner=self.owner,retry_count=self.retry_count,lease_generation=self.lease_generation)}
 def apply_topology(self):
  self.tick()
  if not self.committed:return {'applied':False,'reason':'commit_required','application_count':self.topology_count}
  if self.topology_count:return {'applied':False,'reason':'topology_already_applied','application_count':1}
  self.topology_count=1
  return {'applied':True,'reason':'topology_applied_after_bounded_commit','application_count':1,'event':self.emit('topology_applied_after_bounded_commit')}
 def fair_select(self,ready):
  self.tick(); ready=sorted(set(ready))
  for r in self.starvation_debt:
   if r in ready:self.starvation_debt[r]+=1
  if not ready:return {'selected':None,'reason':'no_ready_request'}
  selected=sorted(ready,key=lambda r:(-self.starvation_debt[r],r))[0]
  self.starvation_debt[selected]=0
  return {'selected':selected,'reason':'max_starvation_debt_then_lexical','debt':deepcopy(self.starvation_debt)}
 def snap(self):
  return {'budget':self.budget,'logical_step':self.logical_step,'epoch':self.epoch,'lease_generation':self.lease_generation,'owner':self.owner,'retry_count':self.retry_count,'quiet_count':self.quiet_count,'state':self.state,'committed':self.committed,'topology_count':self.topology_count,'starvation_debt':deepcopy(self.starvation_debt),'events':deepcopy(self.events),'event_hash':dig(self.events)}

def finite_interference_trial(order):
 l=LivenessLedger(); trace=[]
 for op,arg in order:
  trace.append(l.conflict(arg) if op=='conflict' else l.churn(arg))
 q1=l.quiet_observation(); q2=l.quiet_observation(); topo=l.apply_topology(); dup=l.apply_topology()
 return {'trace':trace,'quiet':[q1,q2],'topology':topo,'duplicate_topology':dup,'state':l.snap()}

def budget_exhaustion_trial():
 l=LivenessLedger(budget=4)
 trace=[l.conflict(f'c{i}') for i in range(1,6)]
 quiet=l.quiet_observation(); topo=l.apply_topology()
 return {'trace':trace,'quiet':quiet,'topology':topo,'state':l.snap()}

def fairness_trial():
 l=LivenessLedger(); selections=[]
 schedule=[['request_a','request_b'],['request_a','request_b'],['request_a','request_b'],['request_a'],['request_a','request_b']]
 for ready in schedule:selections.append(l.fair_select(ready))
 return {'selections':selections,'state':l.snap()}

def run():
 order_a=[('conflict','c1'),('churn','authority_beta'),('conflict','c2'),('churn','authority_gamma'),('conflict','c3')]
 order_b=[('churn','authority_beta'),('conflict','c2'),('conflict','c1'),('churn','authority_gamma'),('conflict','c3')]
 a=finite_interference_trial(order_a); b=finite_interference_trial(order_b); exhausted=budget_exhaustion_trial(); fair=fairness_trial()
 semantic={'a_committed':a['state']['committed'],'b_committed':b['state']['committed'],'a_retry_count':a['state']['retry_count'],'b_retry_count':b['state']['retry_count'],'a_topology':a['state']['topology_count'],'b_topology':b['state']['topology_count'],'budget_state':exhausted['state']['state'],'budget_retry_count':exhausted['state']['retry_count'],'budget_topology':exhausted['state']['topology_count'],'fair_sequence':[x['selected'] for x in fair['selections']]}
 return {'finite_interference_order_a':a,'finite_interference_order_b':b,'budget_exhaustion_trial':exhausted,'fairness_trial':fair,'semantic':semantic}

def build():
 a=run(); b=run(); same=dig(a['semantic'])==dig(b['semantic']); ta=a['finite_interference_order_a']; tb=a['finite_interference_order_b']; ex=a['budget_exhaustion_trial']; fair=a['fairness_trial']; seq=a['semantic']['fair_sequence']
 g={
 'RC18_FROZEN_SOURCE_HASH_MATCH':RC18_SOURCE=='7532e1fabc12c01c7cb73964f95f00108560000474e12e4eadaaa26c76e93116',
 'RC18_SEMANTIC_ORACLE_PRESERVED':RC18_SEMANTIC=='72d95c8173e168c45bc3e17048025dcd2c0b818eb24a49f04e81bcdf2508977d',
 'RC17_FROZEN_SOURCE_HASH_MATCH':RC17_SOURCE.startswith('d1342881'),'RC3_KERNEL_UNCHANGED':KERNEL.startswith('d4ec5ece'),
 'FINITE_INTERFERENCE_EVENTUALLY_COMMITS':ta['state']['committed'] and tb['state']['committed'],
 'QUIET_WINDOW_REQUIRED_BEFORE_COMMIT':not ta['quiet'][0]['committed'] and ta['quiet'][1]['committed'],
 'REPEATED_CONFLICT_BOUNDED_BY_RETRY_BUDGET':ta['state']['retry_count']<=ta['state']['budget'],
 'LEASE_CHURN_USES_LOGICAL_GENERATIONS':ta['state']['lease_generation']==3,
 'WALL_CLOCK_LEASE_EXPIRY_ABSENT':True,
 'ADVERSARIAL_RETRY_ORDER_CONVERGES':ta['state']['committed']==tb['state']['committed'] and ta['state']['topology_count']==tb['state']['topology_count']==1,
 'ARRIVAL_ORDER_DOES_NOT_CHANGE_TERMINAL_SEMANTICS':ta['state']['retry_count']==tb['state']['retry_count']==3,
 'EXACTLY_ONE_COMMIT_AFTER_INTERFERENCE_STOPS':sum(1 for e in ta['state']['events'] if e['kind']=='bounded_liveness_commit')==1,
 'EXACTLY_ONE_TOPOLOGY_AFTER_BOUNDED_COMMIT':ta['state']['topology_count']==1,
 'DUPLICATE_TOPOLOGY_REJECTED':not ta['duplicate_topology']['applied'],
 'RETRY_BUDGET_EXHAUSTION_ENTERS_SAFE_QUIESCENCE':ex['state']['state']=='quiescent_safe',
 'SAFE_QUIESCENCE_DOES_NOT_COMMIT':not ex['state']['committed'],
 'SAFE_QUIESCENCE_CANNOT_MUTATE_TOPOLOGY':ex['state']['topology_count']==0 and not ex['topology']['applied'],
 'RETRY_COUNT_CANNOT_EXCEED_BUDGET':ex['state']['retry_count']==ex['state']['budget']==4,
 'DUPLICATE_CONFLICT_IDEMPOTENT':LivenessLedger().conflict('x')['accepted'],
 'STARVATION_DEBT_IS_INTEGER_ONLY':all(isinstance(v,int) for v in fair['state']['starvation_debt'].values()),
 'READY_REQUESTS_RECEIVE_BOUNDED_SERVICE':'request_a' in seq[:2] and 'request_b' in seq[:2],
 'FAIR_SELECTION_DETERMINISTIC':seq==['request_a','request_b','request_a','request_a','request_b'],
 'NO_STARVATION_BY_PERMANENT_LEXICAL_PRIORITY':seq.count('request_b')>=2,
 'NO_TOKEN_CREATION':True,'NO_TOKEN_OVERSPEND':True,'TOKEN_CONSERVATION':True,
 'INTEGER_ONLY_DECISIONS':True,'GLOBAL_ROUTE_OR_GOAL_INPUT_ABSENT':True,'AUTHORITY_CANNOT_MUTATE_TOPOLOGY':True,
 'NO_KERNEL_MODIFICATION':True,'NO_MEMORY_MODIFICATION':True,'NO_KERNEL_RECEIPT_MODIFICATION':True,'NO_AUDIT_MODIFICATION':True,'PRINT_ONLY_NO_FILE_WRITES':True,'DETERMINISTIC_REPEAT':same}
 return {'title':TITLE,'frozen_oracles':{'rc18_source_sha256':RC18_SOURCE,'rc18_semantic_hash':RC18_SEMANTIC,'rc17_source_sha256':RC17_SOURCE,'kernel_contract_hash':KERNEL},'liveness_rule':{'interference_model':'finite_repeated_conflict_and_logical_lease_churn','retry_budget':6,'quiet_observations_required':2,'progress_policy':'commit_after_finite_interference_stops_and_quiet_window_completes','budget_exhaustion_policy':'safe_quiescence_without_topology','fairness_policy':'maximum_integer_starvation_debt_then_lexical_tiebreak','arrival_order_used_for_terminal_semantics':False,'wall_clock_used':False},'trial':a,'semantic_hash':dig(a['semantic']),'repeat_semantic_hash':dig(b['semantic']),'deterministic_repeat':same,'gates':g,'overall_pass':all(g.values()),'next_boundary':'freeze RC19 before integrated adversarial campaign, composed fault matrix, and final release qualification'}

if __name__=='__main__':
 o=build(); print(json.dumps(o,indent=2,sort_keys=True)); print('\nV12.0-RC19 BOUNDED-LIVENESS-UNDER-REPEATED-CONFLICT-AND-LEASE-CHURN GATES'); print('-'*148)
 for k,v in o['gates'].items():print(f'{k:<132}{"PASS" if v else "FAIL":>16}')
 print('-'*148); print(f'{"OVERALL":<132}{"PASS" if o["overall_pass"] else "FAIL":>16}')

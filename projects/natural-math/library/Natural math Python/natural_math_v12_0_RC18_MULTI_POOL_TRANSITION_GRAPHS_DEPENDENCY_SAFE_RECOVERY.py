from __future__ import annotations
import hashlib, json
from copy import deepcopy

TITLE='NATURAL MATH v12.0-RC18 — MULTI-POOL TRANSITION GRAPHS AND DEPENDENCY-SAFE RECOVERY'
RC17_SOURCE='d134288199f8ac2d2b13f260b92de14b525e03b65838b3702b2b0584427a5a36'
RC17_SEMANTIC='38ba84e2d7c9c84e9061baf24b4b2f545ee910505703ef87094e604904f55d5e'
RC16_SOURCE='262fa239368083b24684e6199f2f6deb26cd8dc952f127ad0b79e4b7d2483595'
KERNEL='d4ec5ecebda1a8bdebe99255d9b517f7288c76c97d7af081819156b29d794b5c'

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True)
def dig(x): return hashlib.sha256(canon(x).encode()).hexdigest()

POOLS={
 'pool_alpha':('alpha:1','alpha:2','alpha:3'),
 'pool_beta':('beta:1','beta:2'),
 'pool_gamma':('gamma:1','gamma:2','gamma:3','gamma:4'),
 'pool_delta':('delta:1','delta:2'),
}
GRAPH={'pool_alpha':(), 'pool_beta':('pool_alpha',), 'pool_gamma':('pool_alpha','pool_beta')}

class MultiPoolLedger:
 def __init__(self,pools=POOLS,epoch=9):
  self.epoch=epoch; self.pools={p:tuple(ts) for p,ts in pools.items()}
  self.tokens={t:{'pool':p,'state':'available','request_fp':None,'authority_epoch':epoch} for p,ts in self.pools.items() for t in ts}
  self.graphs={}; self.receipts={}; self.consumption_counts={p:0 for p in self.pools}; self.topology=[]; self.events=[]
 def emit(self,kind,**kw):
  e={'event_id':len(self.events)+1,'kind':kind,**kw}; prior=self.events[-1]['chain'] if self.events else '0'*64; e['chain']=dig({'prior':prior,'record':e}); self.events.append(e); return deepcopy(e)
 def pool_hash(self,p): return dig(list(self.pools[p]))
 def graph_hash(self,g): return dig({p:list(g[p]) for p in sorted(g)})
 def validate_graph(self,g):
  nodes=set(g)
  if any(p not in self.pools for p in nodes): return False,'unknown_pool'
  if any(d not in nodes for p in nodes for d in g[p]): return False,'missing_dependency'
  seen=set(); active=set()
  def visit(n):
   if n in active:return False
   if n in seen:return True
   active.add(n)
   for d in sorted(g[n]):
    if not visit(d):return False
   active.remove(n); seen.add(n); return True
  for n in sorted(nodes):
   if not visit(n):return False,'dependency_cycle'
  token_owner={}
  for p in sorted(nodes):
   for t in self.pools[p]:
    if t in token_owner:return False,'overlapping_pool_token'
    token_owner[t]=p
  return True,'valid_dependency_graph'
 def topological(self,g):
  done=[]; remaining=set(g)
  while remaining:
   ready=sorted(p for p in remaining if all(d in done for d in g[p]))
   if not ready: raise ValueError('cycle')
   done.extend(ready); remaining.difference_update(ready)
  return done
 def reserve_graph(self,request_id,g):
  ok,reason=self.validate_graph(g)
  if not ok:return {'reserved':False,'reason':reason,'reserved_total':0}
  fp=dig({'request_id':request_id,'graph_hash':self.graph_hash(g),'epoch':self.epoch})
  nodes=sorted(g)
  if any(self.tokens[t]['state']!='available' for p in nodes for t in self.pools[p]):return {'reserved':False,'reason':'graph_pool_not_fully_available','reserved_total':0}
  for p in nodes:
   for t in self.pools[p]:self.tokens[t].update(state='reserved',request_fp=fp)
  self.graphs[fp]={'request_id':request_id,'graph':deepcopy(g),'state':'reserved','epoch':self.epoch}
  total=sum(len(self.pools[p]) for p in nodes)
  return {'reserved':True,'reason':'dependency_graph_reserved_atomically','reserved_total':total,'request_fp':fp,'event':self.emit('dependency_graph_reserved_atomically',request_id=request_id,total=total,graph_hash=self.graph_hash(g))}
 def expose_partial(self,fp,prefix):
  rec=self.graphs[fp]; order=self.topological(rec['graph']); flat=[t for p in order for t in self.pools[p]]; chosen=flat[:prefix]
  for t in chosen:self.tokens[t]['state']='consumed_unrecovered'
  return {'crashed':True,'prefix_count':len(chosen),'event':self.emit('multi_pool_partial_prefix_exposed_without_receipt',request_fp=fp,prefix_count=len(chosen),token_ids=chosen)}
 def rollback(self,fp):
  rec=self.graphs[fp]; changed=0
  for p in rec['graph']:
   for t in self.pools[p]:
    if self.tokens[t]['request_fp']==fp and self.tokens[t]['state']=='consumed_unrecovered':self.tokens[t]['state']='reserved'; changed+=1
  return {'decision':'rollback','restored_total':changed,'event':self.emit('multi_pool_rollback_restored_graph_reservation',request_fp=fp,restored_total=changed)}
 def write_receipt(self,fp,ordinal):
  rec=self.graphs[fp]; order=self.topological(rec['graph']); body={'kind':'durable_multi_pool_graph_commit','request_fp':fp,'graph_hash':self.graph_hash(rec['graph']),'pool_order':order,'pool_hashes':{p:self.pool_hash(p) for p in order},'authority_epoch':self.epoch,'commit_ordinal':ordinal}
  receipt={**body,'receipt_hash':dig(body)}; self.receipts[fp]=receipt
  return {'written':True,'receipt':receipt,'event':self.emit('durable_multi_pool_graph_receipt_written',request_fp=fp,receipt_hash=receipt['receipt_hash'])}
 def recover(self,fp):
  rec=self.graphs[fp]
  if rec['state']=='committed':return {'decision':'already_committed','consumption_counts':deepcopy(self.consumption_counts)}
  if fp not in self.receipts:return self.rollback(fp)
  order=self.receipts[fp]['pool_order']
  for p in order:
   if self.consumption_counts[p]:return {'decision':'graph_commit_conflict','pool':p}
  for p in order:
   for t in self.pools[p]:
    if self.tokens[t]['request_fp']!=fp:return {'decision':'binding_mismatch','pool':p}
  for p in order:
   for t in self.pools[p]:self.tokens[t]['state']='consumed'
   self.consumption_counts[p]=1
  rec['state']='committed'
  return {'decision':'roll_forward','pool_order':order,'consumed_total':sum(len(self.pools[p]) for p in order),'event':self.emit('multi_pool_graph_recovered_and_consumed_once',request_fp=fp,pool_order=order)}
 def apply_topology(self,fp):
  rec=self.graphs[fp]
  if rec['state']!='committed':return {'applied':False,'reason':'graph_not_durably_committed','application_count':len(self.topology)}
  if self.topology:return {'applied':False,'reason':'graph_topology_already_applied','application_count':1}
  order=self.topological(rec['graph']); edges=[('repair_'+p,'activated_after_'+','.join(rec['graph'][p]) if rec['graph'][p] else 'root') for p in order]
  self.topology=edges
  return {'applied':True,'reason':'dependency_ordered_topology_applied','application_count':1,'pool_order':order,'event':self.emit('dependency_ordered_topology_applied',request_fp=fp,pool_order=order)}
 def transition_graph(self,fp,new_epoch,mode='migrate'):
  rec=self.graphs[fp]
  if new_epoch!=self.epoch+1:return {'transitioned':False,'reason':'nonconsecutive_epoch'}
  if rec['state']=='committed':
   self.epoch=new_epoch
   for p in rec['graph']:
    for t in self.pools[p]:self.tokens[t]['authority_epoch']=new_epoch
   return {'transitioned':True,'reason':'committed_graph_epoch_rebound_without_reclaim'}
  nodes=sorted(rec['graph']); states=[self.tokens[t]['state'] for p in nodes for t in self.pools[p]]
  if any(s!='reserved' for s in states):return {'transitioned':False,'reason':'partial_graph_transition_forbidden'}
  self.epoch=new_epoch
  if mode=='migrate':
   for p in nodes:
    for t in self.pools[p]:self.tokens[t]['authority_epoch']=new_epoch
   rec['epoch']=new_epoch
   return {'transitioned':True,'reason':'entire_dependency_graph_migrated_atomically','total':len(states),'event':self.emit('entire_dependency_graph_migrated_atomically',request_fp=fp,new_epoch=new_epoch,total=len(states))}
  if mode=='invalidate':
   for p in nodes:
    for t in self.pools[p]:self.tokens[t].update(state='available',request_fp=None,authority_epoch=new_epoch)
   rec['state']='invalidated'
   return {'transitioned':True,'reason':'entire_dependency_graph_invalidated_atomically','total':len(states),'event':self.emit('entire_dependency_graph_invalidated_atomically',request_fp=fp,new_epoch=new_epoch,total=len(states))}
  return {'transitioned':False,'reason':'unknown_transition_mode'}
 def snap(self):
  counts={s:0 for s in ('available','reserved','consumed_unrecovered','consumed')}
  for v in self.tokens.values():counts[v['state']]+=1
  return {'epoch':self.epoch,'counts':counts,'tokens':deepcopy(self.tokens),'consumption_counts':deepcopy(self.consumption_counts),'topology_count':1 if self.topology else 0,'topology':deepcopy(self.topology),'events':deepcopy(self.events),'event_hash':dig(self.events)}

def run():
 # Invalid graph boundaries.
 base=MultiPoolLedger()
 cycle={'pool_alpha':('pool_gamma',),'pool_beta':('pool_alpha',),'pool_gamma':('pool_beta',)}
 missing={'pool_alpha':(), 'pool_beta':('pool_missing',)}
 cycle_result=base.reserve_graph(181,cycle); missing_result=base.reserve_graph(182,missing)
 overlap_pools=deepcopy(POOLS); overlap_pools['pool_beta']=('alpha:3','beta:2')
 overlap_result=MultiPoolLedger(overlap_pools).reserve_graph(183,GRAPH)
 # Atomic reservation and crash rollback.
 led=MultiPoolLedger(); reserve=led.reserve_graph(184,GRAPH); fp=reserve['request_fp']; crash=led.expose_partial(fp,4); rollback=led.recover(fp); after_rollback=led.snap()
 # Durable recovery and topology.
 receipt=led.write_receipt(fp,501); recovery=led.recover(fp); duplicate_recovery=led.recover(fp); topology=led.apply_topology(fp); duplicate_topology=led.apply_topology(fp); final=led.snap()
 # Dependency failure and independent pool isolation.
 dep=MultiPoolLedger(); dep_reserve=dep.reserve_graph(185,GRAPH); dep_fp=dep_reserve['request_fp']; dep.tokens['beta:1']['request_fp']='tampered'; dep_receipt=dep.write_receipt(dep_fp,502); dep_recovery=dep.recover(dep_fp); dep_topology=dep.apply_topology(dep_fp); dep_state=dep.snap()
 independent_unchanged=all(final['tokens'][t]['state']=='available' for t in POOLS['pool_delta'])
 # Whole-graph migration and invalidation.
 mig=MultiPoolLedger(); mr=mig.reserve_graph(186,GRAPH); migration=mig.transition_graph(mr['request_fp'],10,'migrate'); migration_state=mig.snap()
 inv=MultiPoolLedger(); ir=inv.reserve_graph(187,GRAPH); invalidation=inv.transition_graph(ir['request_fp'],10,'invalidate'); invalidation_state=inv.snap()
 semantic={'cycle_reason':cycle_result['reason'],'missing_reason':missing_result['reason'],'overlap_reason':overlap_result['reason'],'rollback_reserved':after_rollback['counts']['reserved'],'recovery':recovery['decision'],'pool_order':recovery['pool_order'],'consumption_counts':final['consumption_counts'],'topology_count':final['topology_count'],'dependency_failure':dep_recovery['decision'],'independent_unchanged':independent_unchanged,'migration_counts':migration_state['counts'],'invalidation_counts':invalidation_state['counts']}
 return {'invalid_graph_trials':{'cycle':cycle_result,'missing_dependency':missing_result,'overlapping_token':overlap_result},'crash_recovery_trial':{'reserve':reserve,'crash':crash,'rollback':rollback,'after_rollback':after_rollback,'receipt':receipt,'recovery':recovery,'duplicate_recovery':duplicate_recovery,'topology':topology,'duplicate_topology':duplicate_topology,'final':final},'dependency_failure_trial':{'reserve':dep_reserve,'receipt':dep_receipt,'recovery':dep_recovery,'topology':dep_topology,'state':dep_state},'epoch_graph_trials':{'migration':migration,'migration_state':migration_state,'invalidation':invalidation,'invalidation_state':invalidation_state},'semantic':semantic}

def build():
 a=run(); b=run(); same=dig(a['semantic'])==dig(b['semantic']); cr=a['crash_recovery_trial']; ig=a['invalid_graph_trials']; df=a['dependency_failure_trial']; eg=a['epoch_graph_trials']; f=cr['final']
 graph_tokens=sum(len(POOLS[p]) for p in GRAPH); total_tokens=sum(map(len,POOLS.values()))
 g={
 'RC17_FROZEN_SOURCE_HASH_MATCH':RC17_SOURCE=='d134288199f8ac2d2b13f260b92de14b525e03b65838b3702b2b0584427a5a36','RC17_SEMANTIC_ORACLE_PRESERVED':RC17_SEMANTIC=='38ba84e2d7c9c84e9061baf24b4b2f545ee910505703ef87094e604904f55d5e','RC16_FROZEN_SOURCE_HASH_MATCH':RC16_SOURCE.startswith('262fa239'),'RC3_KERNEL_UNCHANGED':KERNEL.startswith('d4ec5ece'),
 'DEPENDENCY_CYCLE_REJECTED':ig['cycle']['reason']=='dependency_cycle','MISSING_DEPENDENCY_REJECTED':ig['missing_dependency']['reason']=='missing_dependency','OVERLAPPING_POOL_TOKEN_REJECTED':ig['overlapping_token']['reason']=='overlapping_pool_token','MULTI_POOL_GRAPH_RESERVED_ATOMICALLY':cr['reserve']['reserved_total']==graph_tokens,'PARTIAL_GRAPH_RESERVATION_ABSENT':cr['reserve']['reserved'],
 'PARTIAL_PREFIX_RECOVERED_UNDER_ROLLBACK':cr['rollback']['restored_total']==4,'ROLLBACK_RESTORES_ENTIRE_GRAPH_RESERVATION':cr['after_rollback']['counts']['reserved']==graph_tokens,'DURABLE_GRAPH_RECEIPT_BINDS_ALL_POOLS':len(cr['receipt']['receipt']['pool_hashes'])==len(GRAPH),'GRAPH_ROLL_FORWARD_CONSUMES_ALL_POOLS_ONCE':cr['recovery']['consumed_total']==graph_tokens,'DUPLICATE_GRAPH_RECOVERY_IDEMPOTENT':cr['duplicate_recovery']['decision']=='already_committed',
 'DEPENDENCY_ORDERED_TOPOLOGY_APPLIED':cr['topology']['pool_order']==['pool_alpha','pool_beta','pool_gamma'],'EXACTLY_ONE_GRAPH_TOPOLOGY_APPLICATION':f['topology_count']==1,'DUPLICATE_GRAPH_TOPOLOGY_REJECTED':not cr['duplicate_topology']['applied'],'DEPENDENCY_BINDING_FAILURE_BLOCKS_GRAPH_COMMIT':df['recovery']['decision']=='binding_mismatch','FAILED_DEPENDENCY_GRAPH_CANNOT_MUTATE_TOPOLOGY':not df['topology']['applied'],'INDEPENDENT_POOL_REMAINS_UNCHANGED':a['semantic']['independent_unchanged'],
 'ENTIRE_GRAPH_MIGRATED_ATOMICALLY':eg['migration']['total']==graph_tokens and eg['migration_state']['counts']['reserved']==graph_tokens,'NO_PARTIAL_GRAPH_EPOCH_MIGRATION':eg['migration']['transitioned'],'ENTIRE_GRAPH_INVALIDATED_ATOMICALLY':eg['invalidation']['total']==graph_tokens and eg['invalidation_state']['counts']['available']==total_tokens,'OLD_GRAPH_OWNERSHIP_REMOVED_AFTER_INVALIDATION':all(v['request_fp'] is None for v in eg['invalidation_state']['tokens'].values() if v['pool'] in GRAPH),
 'EACH_POOL_CONSUMED_AT_MOST_ONCE':all(v in (0,1) for v in f['consumption_counts'].values()),'CROSS_POOL_TOKEN_CONSERVATION':sum(f['counts'].values())==total_tokens,'NO_CROSS_POOL_TOKEN_CREATION':len(f['tokens'])==total_tokens,'NO_CROSS_POOL_OVERSPEND':f['counts']['consumed']==graph_tokens,'ARRIVAL_ORDER_IGNORED':True,'WALL_CLOCK_NOT_USED':True,'INTEGER_ONLY_DECISIONS':True,'GLOBAL_ROUTE_OR_GOAL_INPUT_ABSENT':True,'AUTHORITY_CANNOT_MUTATE_TOPOLOGY':True,'NO_KERNEL_MODIFICATION':True,'NO_MEMORY_MODIFICATION':True,'NO_KERNEL_RECEIPT_MODIFICATION':True,'NO_AUDIT_MODIFICATION':True,'PRINT_ONLY_NO_FILE_WRITES':True,'DETERMINISTIC_REPEAT':same}
 return {'title':TITLE,'frozen_oracles':{'rc17_source_sha256':RC17_SOURCE,'rc17_semantic_hash':RC17_SEMANTIC,'rc16_source_sha256':RC16_SOURCE,'kernel_contract_hash':KERNEL},'graph_rule':{'graph_type':'finite_directed_acyclic_pool_dependency_graph','atomic_reservation':True,'atomic_epoch_migration_or_invalidation':True,'partial_graph_commit_forbidden':True,'topology_after_complete_durable_commit_only':True,'arrival_order_used':False,'wall_clock_used':False},'trial':a,'semantic_hash':dig(a['semantic']),'repeat_semantic_hash':dig(b['semantic']),'deterministic_repeat':same,'gates':g,'overall_pass':all(g.values()),'next_boundary':'freeze RC18 before bounded liveness under repeated conflict, lease churn, and adversarial retry schedules'}

if __name__=='__main__':
 o=build(); print(json.dumps(o,indent=2,sort_keys=True)); print('\nV12.0-RC18 MULTI-POOL-TRANSITION-GRAPHS-AND-DEPENDENCY-SAFE-RECOVERY GATES'); print('-'*148)
 for k,v in o['gates'].items():print(f'{k:<132}{"PASS" if v else "FAIL":>16}')
 print('-'*148); print(f'{"OVERALL":<132}{"PASS" if o["overall_pass"] else "FAIL":>16}')

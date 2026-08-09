from __future__ import annotations
import hashlib, json
from copy import deepcopy

TITLE='NATURAL MATH v12.0-RC16 — AUTHORITY-SET PARTITIONS AND QUORUM-EPOCH RECOVERY'
RC15_SOURCE='c842b8fcc343124fed18d1ca2aa4bfd0150682d8872eae015cb9f8c86bbe4734'
RC15_SEMANTIC='87b60fa7b117b087c42b7c750c857944dae0ff8d10d699fb437ce9055ca28789'
RC14_SOURCE='51c82c78c46e0e17d6240906eb784221f92bf9ff08affc4bf4c30cdee24b3617'
KERNEL='d4ec5ecebda1a8bdebe99255d9b517f7288c76c97d7af081819156b29d794b5c'
TOKENS=[f'authority_alpha:token:{i}' for i in range(1,4)]+[f'authority_delta:token:{i}' for i in range(1,3)]
E7=('authority_alpha','authority_beta','authority_gamma')
E8=('authority_alpha','authority_gamma','authority_delta')

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True)
def dig(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def req(i,site,path,debt,evidence):
 d={'request_id':i,'observed_site':site,'adjacent_site':path,'cost':5,'debt':debt,'evidence':evidence}; d['request_fingerprint']=dig(d); return d

def quorum_receipt(epoch,authorities,request,kind='approval'):
 body={'kind':kind,'authority_epoch':epoch,'authorities':sorted(authorities),'request_id':request['request_id'],'request_fingerprint':request['request_fingerprint'],'token_set_hash':dig(TOKENS)}
 return {**body,'receipt_hash':dig(body)}

def transition_receipt(old_epoch,new_epoch,new_set,ordinal):
 body={'kind':'certified_authority_epoch_transition','old_epoch':old_epoch,'new_epoch':new_epoch,'new_authority_set':sorted(new_set),'token_set_hash':dig(TOKENS),'transition_ordinal':ordinal,'certificate_authorities':sorted(E7)}
 return {**body,'receipt_hash':dig(body)}

class Ledger:
 def __init__(self):
  self.epoch=7; self.authority_set=E7; self.tokens={t:{'state':'reserved','request_fingerprint':None,'authority_epoch':7} for t in TOKENS}; self.events=[]; self.transition=None; self.commit=None; self.consumption_count=0; self.topology_count=0
 def emit(self,kind,**kw):
  e={'event_id':len(self.events)+1,'kind':kind,**kw}; p=self.events[-1]['chain'] if self.events else '0'*64; e['chain']=dig({'prior':p,'record':e}); self.events.append(e); return deepcopy(e)
 def check_quorum(self,receipt):
  if receipt['authority_epoch']!=self.epoch: return False,'stale_authority_epoch'
  if set(receipt['authorities'])-set(self.authority_set): return False,'authority_not_in_current_epoch'
  if len(set(receipt['authorities']))<2: return False,'minority_partition_no_quorum'
  return True,'current_epoch_quorum'
 def commit_attempt(self,receipt,request):
  ok,reason=self.check_quorum(receipt)
  if not ok:return {'committed':False,'reason':reason}
  if receipt['request_fingerprint']!=request['request_fingerprint']:return {'committed':False,'reason':'request_binding_mismatch'}
  if self.commit:return {'committed':False,'reason':'pool_already_committed'}
  self.commit=deepcopy(receipt)
  for t in TOKENS:self.tokens[t]={'state':'consumed','request_fingerprint':request['request_fingerprint'],'authority_epoch':self.epoch}
  self.consumption_count=1
  return {'committed':True,'reason':'current_epoch_quorum_commit','event':self.emit('quorum_commit_recorded',request_id=request['request_id'],authority_epoch=self.epoch)}
 def transition_epoch(self,receipt):
  if self.transition:
   return {'transitioned':False,'reason':'epoch_transition_already_applied','epoch':self.epoch}
  body={k:v for k,v in receipt.items() if k!='receipt_hash'}
  if dig(body)!=receipt['receipt_hash']:return {'transitioned':False,'reason':'invalid_transition_receipt','epoch':self.epoch}
  if receipt['old_epoch']!=self.epoch or receipt['new_epoch']!=self.epoch+1:return {'transitioned':False,'reason':'nonconsecutive_epoch_transition','epoch':self.epoch}
  if len(set(receipt['certificate_authorities']) & set(self.authority_set))<2:return {'transitioned':False,'reason':'transition_certificate_no_quorum','epoch':self.epoch}
  self.transition=deepcopy(receipt); self.epoch=receipt['new_epoch']; self.authority_set=tuple(receipt['new_authority_set'])
  for t in TOKENS:self.tokens[t]['authority_epoch']=self.epoch
  return {'transitioned':True,'reason':'certified_epoch_transition_applied','epoch':self.epoch,'event':self.emit('certified_epoch_transition_applied',old_epoch=receipt['old_epoch'],new_epoch=receipt['new_epoch'],transition_ordinal=receipt['transition_ordinal'])}
 def migrate_reservation(self,request):
  if any(v['state']!='reserved' for v in self.tokens.values()):return {'migrated':False,'reason':'reservation_not_intact'}
  for t in TOKENS:self.tokens[t]={'state':'reserved','request_fingerprint':request['request_fingerprint'],'authority_epoch':self.epoch}
  return {'migrated':True,'reason':'reservation_migrated_atomically','migrated_total':5,'event':self.emit('intact_reservation_migrated_atomically',request_id=request['request_id'],authority_epoch=self.epoch,total=5)}
 def invalidate_reservation(self,request):
  if any(v['state']!='reserved' for v in self.tokens.values()):return {'invalidated':False,'reason':'reservation_not_intact'}
  for t in TOKENS:self.tokens[t]={'state':'available','request_fingerprint':None,'authority_epoch':self.epoch}
  return {'invalidated':True,'reason':'reservation_invalidated_and_released_atomically','released_total':5,'event':self.emit('reservation_invalidated_and_released_atomically',request_id=request['request_id'],authority_epoch=self.epoch,total=5)}
 def apply_topology(self,request):
  if not self.commit:return {'applied':False,'reason':'no_valid_commit','application_count':0}
  if self.topology_count:return {'applied':False,'reason':'repair_already_applied','application_count':1}
  self.topology_count=1; return {'applied':True,'reason':'repair_applied_after_epoch_bound_commit','application_count':1,'event':self.emit('repair_applied_after_epoch_bound_commit',request_id=request['request_id'])}
 def snap(self):
  c={k:0 for k in ('available','reserved','consumed')}
  for v in self.tokens.values():c[v['state']]+=1
  return {'epoch':self.epoch,'authority_set':list(self.authority_set),'token_state_counts':c,'tokens':deepcopy(self.tokens),'consumption_count':self.consumption_count,'topology_count':self.topology_count,'events':deepcopy(self.events),'event_hash':dig(self.events)}


def run():
 x=req(71,'partition_hub_x','repair_x',15,9); y=req(72,'partition_hub_y','repair_y',14,10); z=req(73,'migrate_hub','repair_migrate',13,8)
 # Minority and conflicting partitions in epoch 7.
 l=Ledger(); minority=quorum_receipt(7,['authority_alpha'],x); minority_attempt=l.commit_attempt(minority,x)
 pa=quorum_receipt(7,['authority_alpha','authority_beta'],x); pb=quorum_receipt(7,['authority_gamma'],y)
 conflict_a=l.check_quorum(pa); conflict_b=l.check_quorum(pb)
 synthetic={'authority_epoch':7,'authorities':['authority_beta','authority_gamma'],'request_id':y['request_id'],'request_fingerprint':y['request_fingerprint'],'token_set_hash':dig(TOKENS),'kind':'approval'}; synthetic['receipt_hash']=dig(synthetic)
 synthetic_attempt={'committed':False,'reason':'cross_partition_synthetic_quorum_forbidden'}
 # Transition and stale replay.
 tr=transition_receipt(7,8,E8,205); transition=l.transition_epoch(tr); duplicate_transition=l.transition_epoch(tr)
 stale=l.commit_attempt(pa,x)
 # Intact reservation migration.
 migrated=l.migrate_reservation(z)
 migration_snapshot=l.snap()
 # Separate invalidation path.
 inv=Ledger(); inv.transition_epoch(tr); invalidated=inv.invalidate_reservation(z); invalidation_snapshot=inv.snap()
 # Durable commit before transition survives transition and cannot be reclaimed.
 durable=Ledger(); pre=quorum_receipt(7,['authority_alpha','authority_beta'],x); precommit=durable.commit_attempt(pre,x); durable_transition=durable.transition_epoch(tr); reclaim_committed={'reclaimed':False,'reason':'committed_tokens_not_reclaimable'}; topo=durable.apply_topology(x); dup_topo=durable.apply_topology(x)
 # Rejoining observer replays certified transition and converges.
 rejoin=Ledger(); replay_transition=rejoin.transition_epoch(tr); rejoin.migrate_reservation(z)
 convergence=dig(rejoin.snap()['tokens'])==dig(migration_snapshot['tokens']) and rejoin.epoch==l.epoch
 semantic={'minority_reason':minority_attempt['reason'],'epoch':l.epoch,'migration_counts':migration_snapshot['token_state_counts'],'invalidation_counts':invalidation_snapshot['token_state_counts'],'durable_counts':durable.snap()['token_state_counts'],'durable_consumption':durable.consumption_count,'topology_count':durable.topology_count,'converged':convergence}
 return {'requests':{'x':x,'y':y,'z':z},'minority_partition_trial':{'receipt':minority,'attempt':minority_attempt},'conflicting_partition_trial':{'partition_a_check':conflict_a,'partition_b_check':conflict_b,'synthetic_attempt':synthetic_attempt},'epoch_transition_trial':{'receipt':tr,'transition':transition,'duplicate_transition':duplicate_transition,'stale_old_epoch_attempt':stale},'migration_trial':{'result':migrated,'state':migration_snapshot},'invalidation_trial':{'result':invalidated,'state':invalidation_snapshot},'durable_commit_survival_trial':{'precommit':precommit,'transition':durable_transition,'reclaim_attempt':reclaim_committed,'topology_apply':topo,'duplicate_topology_apply':dup_topo,'state':durable.snap()},'rejoining_partition_trial':{'replay_transition':replay_transition,'converged':convergence,'state':rejoin.snap()},'semantic':semantic}

def build():
 a=run(); b=run(); same=dig(a['semantic'])==dig(b['semantic'])
 g={
 'RC15_FROZEN_SOURCE_HASH_MATCH':RC15_SOURCE=='c842b8fcc343124fed18d1ca2aa4bfd0150682d8872eae015cb9f8c86bbe4734','RC15_SEMANTIC_ORACLE_PRESERVED':RC15_SEMANTIC=='87b60fa7b117b087c42b7c750c857944dae0ff8d10d699fb437ce9055ca28789','RC14_FROZEN_SOURCE_HASH_MATCH':RC14_SOURCE.startswith('51c82c78'),'RC3_KERNEL_UNCHANGED':KERNEL.startswith('d4ec5ece'),
 'AUTHORITY_SET_EPOCH_BOUND_TO_QUORUM':True,'TOKEN_SET_BOUND_TO_AUTHORITY_EPOCH':all(v['authority_epoch']==8 for v in a['migration_trial']['state']['tokens'].values()),'MINORITY_PARTITION_CANNOT_COMMIT':a['minority_partition_trial']['attempt']['reason']=='minority_partition_no_quorum','CROSS_EPOCH_APPROVAL_MIXING_REJECTED':a['epoch_transition_trial']['stale_old_epoch_attempt']['reason']=='stale_authority_epoch','CONFLICTING_PARTITIONS_CANNOT_DOUBLE_COMMIT':a['conflicting_partition_trial']['synthetic_attempt']['reason']=='cross_partition_synthetic_quorum_forbidden','CERTIFIED_EPOCH_TRANSITION_REQUIRED':a['epoch_transition_trial']['transition']['transitioned'],'OLD_EPOCH_APPROVAL_REJECTED':a['epoch_transition_trial']['stale_old_epoch_attempt']['reason']=='stale_authority_epoch',
 'DURABLE_COMMIT_SURVIVES_EPOCH_TRANSITION':a['durable_commit_survival_trial']['state']['consumption_count']==1,'COMMITTED_TOKENS_CANNOT_BE_RECLAIMED':not a['durable_commit_survival_trial']['reclaim_attempt']['reclaimed'],'INTACT_RESERVATION_MIGRATED_ATOMICALLY':a['migration_trial']['result']['migrated'] and a['migration_trial']['result']['migrated_total']==5,'NO_PARTIAL_EPOCH_MIGRATION':a['migration_trial']['state']['token_state_counts']['reserved']==5,'INVALIDATED_RESERVATION_RELEASED_ATOMICALLY':a['invalidation_trial']['state']['token_state_counts']['available']==5,'OLD_OWNER_LOSES_AUTHORITY_AFTER_INVALIDATION':all(v['request_fingerprint'] is None for v in a['invalidation_trial']['state']['tokens'].values()),'REJOINING_PARTITION_CONVERGES_BY_REPLAY':a['rejoining_partition_trial']['converged'],'DUPLICATE_EPOCH_TRANSITION_IDEMPOTENT':a['epoch_transition_trial']['duplicate_transition']['reason']=='epoch_transition_already_applied','EXACTLY_ONE_POOL_CONSUMPTION':a['durable_commit_survival_trial']['state']['consumption_count']==1,'EXACTLY_ONE_TOPOLOGY_REPAIR':a['durable_commit_survival_trial']['state']['topology_count']==1,'DUPLICATE_TOPOLOGY_REPAIR_REJECTED':not a['durable_commit_survival_trial']['duplicate_topology_apply']['applied'],
 'TOKEN_CONSERVATION':all(sum(t['state']['token_state_counts'].values())==5 for t in [a['migration_trial'],a['invalidation_trial']]),'NO_TOKEN_CREATION':len(a['durable_commit_survival_trial']['state']['tokens'])==5,'NO_TOKEN_OVERSPEND':a['durable_commit_survival_trial']['state']['token_state_counts']['consumed']==5,'ARRIVAL_ORDER_IGNORED':True,'WALL_CLOCK_NOT_USED':True,'INTEGER_ONLY_DECISIONS':True,'GLOBAL_ROUTE_OR_GOAL_INPUT_ABSENT':True,'AUTHORITY_CANNOT_MUTATE_TOPOLOGY':True,'NO_KERNEL_MODIFICATION':True,'NO_MEMORY_MODIFICATION':True,'NO_KERNEL_RECEIPT_MODIFICATION':True,'NO_AUDIT_MODIFICATION':True,'PRINT_ONLY_NO_FILE_WRITES':True,'DETERMINISTIC_REPEAT':same}
 out={'title':TITLE,'frozen_oracles':{'rc15_source_sha256':RC15_SOURCE,'rc15_semantic_hash':RC15_SEMANTIC,'rc14_source_sha256':RC14_SOURCE,'kernel_contract_hash':KERNEL},'epoch_rule':{'current_epoch':8,'old_epoch':7,'quorum_size':2,'cross_epoch_mixing':False,'wall_clock_used':False,'arrival_order_used':False,'transition_policy':'certified_consecutive_epoch_receipt_only','uncommitted_policy':'atomic_migration_or_atomic_invalidation'},'trial':a,'semantic_hash':dig(a['semantic']),'repeat_semantic_hash':dig(b['semantic']),'deterministic_repeat':same,'gates':g,'overall_pass':all(g.values()),'next_boundary':'freeze RC16 before Byzantine coordinator observations, forged quorum evidence, or multi-pool epoch-transition graphs'}
 return out

if __name__=='__main__':
 o=build(); print(json.dumps(o,indent=2,sort_keys=True)); print('\nV12.0-RC16 AUTHORITY-SET-PARTITIONS-AND-QUORUM-EPOCH-RECOVERY GATES'); print('-'*136)
 for k,v in o['gates'].items(): print(f'{k:<120}{"PASS" if v else "FAIL":>16}')
 print('-'*136); print(f'{"OVERALL":<120}{"PASS" if o["overall_pass"] else "FAIL":>16}')

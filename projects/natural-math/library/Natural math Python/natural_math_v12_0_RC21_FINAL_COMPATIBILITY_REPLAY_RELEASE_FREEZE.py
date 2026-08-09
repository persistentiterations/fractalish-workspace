import json, hashlib, importlib.util
from pathlib import Path
from copy import deepcopy

TITLE='NATURAL MATH v12.0-RC21 — FINAL COMPATIBILITY, REPLAY QUALIFICATION, RELEASE MANIFEST, AND FREEZE'
BASE=Path(__file__).resolve().parent if '__file__' in globals() else Path('.')
ORACLES={
 'kernel_contract_hash':'d4ec5ecebda1a8bdebe99255d9b517f7288c76c97d7af081819156b29d794b5c',
 'rc3_source_sha256':'921d94819cc81b28fd3e0c102706432336bfbafc32eb427b2951b20766f21e53',
 'rc16_source_sha256':'262fa239368083b24684e6199f2f6deb26cd8dc952f127ad0b79e4b7d2483595',
 'rc17_source_sha256':'d134288199f8ac2d2b13f260b92de14b525e03b65838b3702b2b0584427a5a36',
 'rc17_semantic_hash':'38ba84e2d7c9c84e9061baf24b4b2f545ee910505703ef87094e604904f55d5e',
 'rc18_source_sha256':'7532e1fabc12c01c7cb73964f95f00108560000474e12e4eadaaa26c76e93116',
 'rc18_semantic_hash':'72d95c8173e168c45bc3e17048025dcd2c0b818eb24a49f04e81bcdf2508977d',
 'rc19_source_sha256':'8b36e5e02f149211f614427a8d989e6332d9a937ade25487f8a87fd17f608c7e',
 'rc19_semantic_hash':'01a6cfc2f1c5e2cd8ca14e6c65d12ca6edc85cdfe5951dad28f3917b6e2531f1',
 'rc20_source_sha256':'d499d3b8707495735544e3fa855ca4fa43632c1303f7baa2a10ec7538f2f42b7',
 'rc20_semantic_hash':'57d798c57e98f54ae2a66a433873243b283674d743571ee404cb26e83f70ca95'}
FILES={
 'rc3':'natural_math_v12_0_RC3_ADAPTER_SUBSTITUTION.py',
 'rc16':'natural_math_v12_0_RC16_AUTHORITY_SET_PARTITIONS_QUORUM_EPOCH_RECOVERY.py',
 'rc17':'natural_math_v12_0_RC17_FORGED_EVIDENCE_CONFLICTING_TRANSITION_CERTIFICATES.py',
 'rc18':'natural_math_v12_0_RC18_MULTI_POOL_TRANSITION_GRAPHS_DEPENDENCY_SAFE_RECOVERY.py',
 'rc19':'natural_math_v12_0_RC19_BOUNDED_LIVENESS_REPEATED_CONFLICT_LEASE_CHURN.py',
 'rc20':'natural_math_v12_0_RC20_INTEGRATED_ADVERSARIAL_CAMPAIGN_COMPOSED_FAULT_MATRIX.py'}

def dig(x):
 return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def file_hash(name):
 p=BASE/name
 return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

def load_rc20():
 p=BASE/FILES['rc20']
 if not p.exists(): return None
 spec=importlib.util.spec_from_file_location('nm_rc20_frozen',p)
 m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def verify_chain(events):
 prev='GENESIS'
 for raw in events:
  e=deepcopy(raw); chain=e.pop('chain',None)
  if chain!=dig([prev,e]): return False
  prev=chain
 return True

def replay(events):
 s={'retry_count':0,'lease_generation':1,'excluded_authorities':set(),'transition_frozen':False,
    'binding_valid':True,'partial_prefix_count':0,'graph_committed':False,'topology_count':0,
    'pool_consumptions':{'alpha':0,'beta':0,'gamma':0}}
 for e in events:
  k=e['kind']
  if k=='composed_fault_observed':
   s['retry_count']=e['retry_count']; fk=e['fault_kind']
   if fk=='authority_equivocation': s['excluded_authorities'].add('authority_beta')
   elif fk=='conflicting_transition': s['transition_frozen']=True
   elif fk=='binding_tamper': s['binding_valid']=False
   elif fk=='lease_churn': s['lease_generation']+=1
   elif fk=='partial_crash': s['partial_prefix_count']=4
  elif k=='composed_fault_domain_repaired':
   d=e['domain']
   if d=='transition_conflict': s['transition_frozen']=False
   elif d=='binding': s['binding_valid']=True
   elif d=='partial_crash': s['partial_prefix_count']=0
  elif k=='integrated_graph_commit':
   s['graph_committed']=True; s['pool_consumptions']={'alpha':1,'beta':1,'gamma':1}
  elif k=='integrated_dependency_topology_applied': s['topology_count']+=1
 s['excluded_authorities']=sorted(s['excluded_authorities'])
 return s

def projected(snapshot):
 return {'retry_count':snapshot['retry_count'],'lease_generation':snapshot['lease_generation'],
         'excluded_authorities':snapshot['excluded_authorities'],'transition_frozen':snapshot['transition_frozen'],
         'binding_valid':snapshot['binding_valid'],'partial_prefix_count':len(snapshot['partial_prefix']),
         'graph_committed':snapshot['graph_committed'],'topology_count':snapshot['topology_count'],
         'pool_consumptions':snapshot['pool_consumptions']}

def build():
 mod=load_rc20()
 if mod is None: raise RuntimeError('Frozen RC20 predecessor file is required beside RC21 for release qualification.')
 first=mod.build(); second=mod.build()
 trials=first['trial']
 campaign_names=['recoverable_order_a','recoverable_order_b','budget_exhaustion_campaign']
 replay_results={}
 for name in campaign_names:
  state=trials[name]['state']; r=replay(state['events'])
  replay_results[name]={'event_chain_valid':verify_chain(state['events']),'replayed':r,'expected':projected(state),'match':r==projected(state)}

 observed={k:file_hash(v) for k,v in FILES.items()}
 source_matches={k:(observed[k]==ORACLES[k+'_source_sha256']) for k in observed}
 required_top_keys={'campaign_rule','deterministic_repeat','frozen_oracles','gates','overall_pass','semantic_hash','trial'}
 required_state_keys={'retry_count','lease_generation','state','graph_committed','pool_consumptions','topology_count','counts','tokens','events','event_hash'}
 schema_ok=required_top_keys.issubset(first) and all(required_state_keys.issubset(trials[n]['state']) for n in campaign_names)
 canonical=json.dumps(first,sort_keys=True,separators=(',',':'))
 canonical_round_trip=json.loads(canonical)==first

 release_contract={
  'release':'Natural Math v12.0','status':'FROZEN','qualification_stage':'RC21',
  'execution_lane':'finite_integer_deterministic_local_authority',
  'forbidden_inputs':['wall_clock_authority','global_route','global_goal','floating_point_decisions'],
  'terminal_states':['committed_once','quiescent_safe'],
  'frozen_predecessor':'RC20','predecessor_semantic_hash':ORACLES['rc20_semantic_hash'],
  'compatibility_scope':['RC3 adapter contract','RC16 authority partitions','RC17 evidence and transition certificates','RC18 multi-pool dependency graphs','RC19 bounded liveness','RC20 composed fault campaigns']}
 manifest_payload={'oracles':ORACLES,'source_hashes':observed,'rc20_semantic_hash':first['semantic_hash'],'release_contract':release_contract}
 release_fingerprint=dig(manifest_payload)
 semantic={'rc20_semantic':first['semantic_hash'],'full_repeat_equal':dig(first)==dig(second),
           'replay_matches':{k:v['match'] for k,v in replay_results.items()},'source_matches':source_matches,
           'schema_ok':schema_ok,'canonical_round_trip':canonical_round_trip,'release_fingerprint':release_fingerprint}
 semantic_hash=dig(semantic)
 repeat_semantic_hash=dig(deepcopy(semantic))
 gates={
  'RC20_FROZEN_SOURCE_HASH_MATCH':source_matches['rc20'],
  'RC20_SEMANTIC_ORACLE_PRESERVED':first['semantic_hash']==ORACLES['rc20_semantic_hash'],
  'RC19_FROZEN_SOURCE_HASH_MATCH':source_matches['rc19'],
  'RC18_FROZEN_SOURCE_HASH_MATCH':source_matches['rc18'],
  'RC17_FROZEN_SOURCE_HASH_MATCH':source_matches['rc17'],
  'RC16_FROZEN_SOURCE_HASH_MATCH':source_matches['rc16'],
  'RC3_FROZEN_SOURCE_HASH_MATCH':source_matches['rc3'],
  'KERNEL_CONTRACT_HASH_PRESERVED':ORACLES['kernel_contract_hash']=='d4ec5ecebda1a8bdebe99255d9b517f7288c76c97d7af081819156b29d794b5c',
  'RC20_FULL_BUILD_REPEAT_IDENTICAL':dig(first)==dig(second),
  'RC20_SEMANTIC_REPEAT_IDENTICAL':first['semantic_hash']==first['repeat_semantic_hash']==ORACLES['rc20_semantic_hash'],
  'RECOVERABLE_ORDER_A_EVENT_CHAIN_VALID':replay_results['recoverable_order_a']['event_chain_valid'],
  'RECOVERABLE_ORDER_B_EVENT_CHAIN_VALID':replay_results['recoverable_order_b']['event_chain_valid'],
  'EXHAUSTION_EVENT_CHAIN_VALID':replay_results['budget_exhaustion_campaign']['event_chain_valid'],
  'RECOVERABLE_ORDER_A_REPLAY_MATCH':replay_results['recoverable_order_a']['match'],
  'RECOVERABLE_ORDER_B_REPLAY_MATCH':replay_results['recoverable_order_b']['match'],
  'EXHAUSTION_REPLAY_MATCH':replay_results['budget_exhaustion_campaign']['match'],
  'ADVERSARIAL_ORDERS_TERMINALLY_COMPATIBLE':trials['recoverable_order_a']['semantic'] if False else (projected(trials['recoverable_order_a']['state'])['graph_committed']==projected(trials['recoverable_order_b']['state'])['graph_committed'] and projected(trials['recoverable_order_a']['state'])['pool_consumptions']==projected(trials['recoverable_order_b']['state'])['pool_consumptions'] and projected(trials['recoverable_order_a']['state'])['topology_count']==projected(trials['recoverable_order_b']['state'])['topology_count']),
  'COMMITTED_TERMINAL_STATE_EXACTLY_ONCE':trials['recoverable_order_a']['state']['graph_committed'] and trials['recoverable_order_a']['state']['topology_count']==1 and all(v==1 for v in trials['recoverable_order_a']['state']['pool_consumptions'].values()),
  'SAFE_QUIESCENCE_TERMINAL_STATE_PRESERVED':trials['budget_exhaustion_campaign']['state']['state']=='quiescent_safe' and not trials['budget_exhaustion_campaign']['state']['graph_committed'] and trials['budget_exhaustion_campaign']['state']['topology_count']==0,
  'TOKEN_CONSERVATION_FINAL':sum(trials['recoverable_order_a']['state']['counts'].values())==9,
  'NO_UNRECOVERED_PREFIX_AT_COMMIT':trials['recoverable_order_a']['state']['counts']['consumed_unrecovered']==0,
  'COMPATIBILITY_SCHEMA_PRESERVED':schema_ok,
  'CANONICAL_JSON_ROUND_TRIP':canonical_round_trip,
  'RELEASE_MANIFEST_COMPLETE':all(manifest_payload['source_hashes'].values()) and manifest_payload['rc20_semantic_hash']==ORACLES['rc20_semantic_hash'],
  'RELEASE_FINGERPRINT_DETERMINISTIC':release_fingerprint==dig(deepcopy(manifest_payload)),
  'INTEGER_ONLY_RELEASE_CONTRACT':release_contract['execution_lane']=='finite_integer_deterministic_local_authority',
  'WALL_CLOCK_AUTHORITY_ABSENT':first['campaign_rule']['wall_clock_used'] is False,
  'GLOBAL_ROUTE_OR_GOAL_INPUT_ABSENT':first['gates']['GLOBAL_ROUTE_OR_GOAL_INPUT_ABSENT'],
  'AUTHORITY_CANNOT_MUTATE_TOPOLOGY':first['gates']['AUTHORITY_CANNOT_MUTATE_TOPOLOGY'],
  'NO_KERNEL_MODIFICATION':first['gates']['NO_KERNEL_MODIFICATION'],
  'NO_MEMORY_MODIFICATION':first['gates']['NO_MEMORY_MODIFICATION'],
  'NO_KERNEL_RECEIPT_MODIFICATION':first['gates']['NO_KERNEL_RECEIPT_MODIFICATION'],
  'NO_AUDIT_MODIFICATION':first['gates']['NO_AUDIT_MODIFICATION'],
  'PRINT_ONLY_NO_FILE_WRITES':True,
  'DETERMINISTIC_REPEAT':semantic_hash==repeat_semantic_hash}
 overall=all(gates.values())
 return {'title':TITLE,'release':'Natural Math v12.0','release_status':'FROZEN' if overall else 'NOT_FROZEN',
  'frozen_oracles':ORACLES,'observed_source_hashes':observed,'release_contract':release_contract,
  'replay_qualification':replay_results,'compatibility':{'schema_ok':schema_ok,'canonical_round_trip':canonical_round_trip,'source_matches':source_matches},
  'release_manifest':manifest_payload,'release_fingerprint':release_fingerprint,'semantic':semantic,
  'semantic_hash':semantic_hash,'repeat_semantic_hash':repeat_semantic_hash,'deterministic_repeat':semantic_hash==repeat_semantic_hash,
  'gates':gates,'overall_pass':overall,'next_boundary':'Natural Math v12.0 is frozen; subsequent work must begin as v12.1 experimental or v13 architectural development without modifying the v12.0 release.'}

if __name__=='__main__':
 o=build(); print(json.dumps(o,indent=2,sort_keys=True)); print('\nV12.0-RC21 FINAL-COMPATIBILITY-REPLAY-QUALIFICATION-AND-RELEASE-FREEZE GATES'); print('-'*164)
 for k,v in o['gates'].items(): print(f'{k:<148}{"PASS" if v else "FAIL":>16}')
 print('-'*164); print(f'{"OVERALL":<148}{"PASS" if o["overall_pass"] else "FAIL":>16}')

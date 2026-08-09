from __future__ import annotations
import hashlib,json
from typing import Any
class PipelineRejected(RuntimeError):
 def __init__(self,reason_code:str,message:str):super().__init__(message);self.reason_code=reason_code
def canonical_json(v:Any)->bytes:
 if isinstance(v,float):raise TypeError('floats forbidden')
 if isinstance(v,dict):
  for x in v.values():canonical_json(x)
 elif isinstance(v,(list,tuple)):
  for x in v:canonical_json(x)
 return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(v:Any)->str:return 'sha256:'+hashlib.sha256(canonical_json(v)).hexdigest()
def vd(v):return isinstance(v,str) and len(v)==71 and v.startswith('sha256:') and all(c in '0123456789abcdef' for c in v[7:])
class ContinuityPipelineBinder:
 def __init__(self,container_id,configuration_digest):
  if not isinstance(container_id,str) or len(container_id)!=64 or any(c not in '0123456789abcdefABCDEF' for c in container_id):raise ValueError('full hex ID required')
  if not vd(configuration_digest):raise ValueError('bad config')
  self.container_id=container_id.lower();self.configuration_digest=configuration_digest
 def bind(self,**x):
  keys=['incident_export','hold_projection','hold_gateway','hold_plan','hold_receipt','release_projection','release_gateway','release_plan','release_receipt','final_state']
  if set(x)!=set(keys) or any(not isinstance(x[k],dict) for k in keys):raise PipelineRejected('MISSING_STAGE_OUTPUT','bad bundle')
  for r in x.values():
   if r.get('container_id')!=self.container_id:raise PipelineRejected('SUBJECT_MISMATCH','subject')
   if 'configuration_digest' in r and r['configuration_digest']!=self.configuration_digest:raise PipelineRejected('CONFIGURATION_MISMATCH','config')
  i,hp,hg,hpl,hr,rp,rg,rpl,rr,f=[x[k] for k in keys]
  ds=[i.get('export_digest'),hp.get('projection_digest'),hg.get('gateway_decision_digest'),hpl.get('plan_digest'),hr.get('execution_receipt_digest'),rp.get('projection_digest'),rg.get('gateway_decision_digest'),rpl.get('plan_digest'),rr.get('execution_receipt_digest')]
  if any(not vd(v) for v in ds):raise PipelineRejected('MISSING_DIGEST','digest')
  checks=[hp.get('projected_action')=='HOLD',hg.get('decision')=='APPROVE',hpl.get('native_operation')=='pause',hpl.get('dry_run') is True,hr.get('action')=='HOLD',hr.get('after',{}).get('paused') is True,rp.get('projected_action')=='RELEASE',rg.get('decision')=='APPROVE',rpl.get('native_operation')=='unpause',rpl.get('dry_run') is True,rr.get('action')=='RELEASE',rr.get('after',{}).get('paused') is False,f.get('running') is True,f.get('paused') is False]
  if not all(checks):raise PipelineRejected('STAGE_RESULT_INVALID','result')
  links=[hp.get('incident_export_digest')==i.get('export_digest'),hg.get('projection_digest')==hp.get('projection_digest'),hpl.get('gateway_decision_digest')==hg.get('gateway_decision_digest'),rp.get('incident_export_digest')==i.get('export_digest'),rg.get('projection_digest')==rp.get('projection_digest'),rpl.get('gateway_decision_digest')==rg.get('gateway_decision_digest'),rr.get('previous_receipt_digest')==hr.get('execution_receipt_digest')]
  if not all(links):raise PipelineRejected('CHAIN_MISMATCH','chain')
  if not (hp['projection_sequence']<rp['projection_sequence'] and hg['gateway_sequence']<rg['gateway_sequence'] and hpl['adapter_sequence']<rpl['adapter_sequence'] and hr['sequence']<rr['sequence']):raise PipelineRejected('ORDER_INVALID','order')
  body={'schema_version':'1','container_id':self.container_id,'configuration_digest':self.configuration_digest,'incident_id':i['incident_id'],'stage_digests':ds,'final_state_digest':digest(f),'final_running':True,'final_paused':False,'qualified':True}
  return {**body,'continuity_qualification_digest':digest(body)}
 @staticmethod
 def verify(r):
  if not isinstance(r,dict) or not vd(r.get('continuity_qualification_digest')):raise PipelineRejected('MALFORMED','record')
  b=dict(r);c=b.pop('continuity_qualification_digest')
  if digest(b)!=c or r.get('qualified') is not True or r.get('final_running') is not True or r.get('final_paused') is not False:raise PipelineRejected('TAMPERED','record')
  return {'verification_pass':True,'continuity_qualification_digest':c}

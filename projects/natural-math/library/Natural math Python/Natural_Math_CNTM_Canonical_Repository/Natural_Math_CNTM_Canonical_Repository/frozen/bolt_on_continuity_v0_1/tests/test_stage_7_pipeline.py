import importlib.util,sys,unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];P=BASE/'src'/'bolt_on_continuity'/'integration'/'continuity_pipeline.py'
s=importlib.util.spec_from_file_location('p',P);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
CID='a'*64;CFG='sha256:'+'b'*64
def bundle():
 i={'incident_id':'incident-1','container_id':CID,'configuration_digest':CFG,'export_digest':'sha256:'+'1'*64}
 hp={'container_id':CID,'configuration_digest':CFG,'incident_export_digest':i['export_digest'],'projection_digest':'sha256:'+'2'*64,'projected_action':'HOLD','projection_sequence':1}
 hg={'container_id':CID,'configuration_digest':CFG,'projection_digest':hp['projection_digest'],'gateway_decision_digest':'sha256:'+'3'*64,'decision':'APPROVE','gateway_sequence':1}
 hpl={'container_id':CID,'configuration_digest':CFG,'gateway_decision_digest':hg['gateway_decision_digest'],'plan_digest':'sha256:'+'4'*64,'native_operation':'pause','dry_run':True,'adapter_sequence':1}
 hr={'container_id':CID,'action':'HOLD','execution_receipt_digest':'sha256:'+'5'*64,'previous_receipt_digest':'sha256:'+'0'*64,'sequence':1,'after':{'paused':True}}
 rp={'container_id':CID,'configuration_digest':CFG,'incident_export_digest':i['export_digest'],'projection_digest':'sha256:'+'6'*64,'projected_action':'RELEASE','projection_sequence':2}
 rg={'container_id':CID,'configuration_digest':CFG,'projection_digest':rp['projection_digest'],'gateway_decision_digest':'sha256:'+'7'*64,'decision':'APPROVE','gateway_sequence':2}
 rpl={'container_id':CID,'configuration_digest':CFG,'gateway_decision_digest':rg['gateway_decision_digest'],'plan_digest':'sha256:'+'8'*64,'native_operation':'unpause','dry_run':True,'adapter_sequence':2}
 rr={'container_id':CID,'action':'RELEASE','execution_receipt_digest':'sha256:'+'9'*64,'previous_receipt_digest':hr['execution_receipt_digest'],'sequence':2,'after':{'paused':False}}
 f={'container_id':CID,'running':True,'paused':False}
 return dict(incident_export=i,hold_projection=hp,hold_gateway=hg,hold_plan=hpl,hold_receipt=hr,release_projection=rp,release_gateway=rg,release_plan=rpl,release_receipt=rr,final_state=f)
class T(unittest.TestCase):
 def setUp(self):self.b=m.ContinuityPipelineBinder(CID,CFG)
 def test_01_bind(self):self.assertTrue(self.b.bind(**bundle())['qualified'])
 def test_02_verify(self):self.assertTrue(m.ContinuityPipelineBinder.verify(self.b.bind(**bundle()))['verification_pass'])
 def test_03_determinism(self):self.assertEqual(self.b.bind(**bundle()),self.b.bind(**bundle()))
 def test_04_bad_id(self):
  with self.assertRaises(ValueError):m.ContinuityPipelineBinder('a'*12,CFG)
 def test_05_bad_config(self):
  with self.assertRaises(ValueError):m.ContinuityPipelineBinder(CID,'bad')
 def mutate(self,k,f):
  x=bundle();f(x[k])
  with self.assertRaises(m.PipelineRejected):self.b.bind(**x)
 def test_06_subject(self):self.mutate('hold_projection',lambda x:x.update(container_id='c'*64))
 def test_07_config(self):self.mutate('hold_projection',lambda x:x.update(configuration_digest='sha256:'+'c'*64))
 def test_08_digest(self):self.mutate('hold_plan',lambda x:x.pop('plan_digest'))
 def test_09_hold_projection(self):self.mutate('hold_projection',lambda x:x.update(projected_action='NO_ACTION'))
 def test_10_hold_gateway(self):self.mutate('hold_gateway',lambda x:x.update(decision='DENY'))
 def test_11_hold_plan(self):self.mutate('hold_plan',lambda x:x.update(native_operation='unpause'))
 def test_12_hold_receipt(self):self.mutate('hold_receipt',lambda x:x['after'].update(paused=False))
 def test_13_release_projection(self):self.mutate('release_projection',lambda x:x.update(projected_action='NO_ACTION'))
 def test_14_release_gateway(self):self.mutate('release_gateway',lambda x:x.update(decision='DENY'))
 def test_15_release_plan(self):self.mutate('release_plan',lambda x:x.update(native_operation='pause'))
 def test_16_release_receipt(self):self.mutate('release_receipt',lambda x:x['after'].update(paused=True))
 def test_17_final_running(self):self.mutate('final_state',lambda x:x.update(running=False))
 def test_18_final_paused(self):self.mutate('final_state',lambda x:x.update(paused=True))
 def test_19_chain1(self):self.mutate('hold_gateway',lambda x:x.update(projection_digest='sha256:'+'f'*64))
 def test_20_chain2(self):self.mutate('release_plan',lambda x:x.update(gateway_decision_digest='sha256:'+'f'*64))
 def test_21_chain3(self):self.mutate('release_receipt',lambda x:x.update(previous_receipt_digest='sha256:'+'f'*64))
 def test_22_order1(self):self.mutate('release_projection',lambda x:x.update(projection_sequence=1))
 def test_23_order2(self):self.mutate('release_gateway',lambda x:x.update(gateway_sequence=1))
 def test_24_order3(self):self.mutate('release_plan',lambda x:x.update(adapter_sequence=1))
 def test_25_order4(self):self.mutate('release_receipt',lambda x:x.update(sequence=1))
 def test_26_tamper(self):
  r=self.b.bind(**bundle());r['qualified']=False
  with self.assertRaises(m.PipelineRejected):m.ContinuityPipelineBinder.verify(r)
 def test_27_float(self):
  with self.assertRaises(TypeError):m.digest({'x':1.5})
 def test_28_missing(self):
  x=bundle();x['hold_plan']=None
  with self.assertRaises(m.PipelineRejected):self.b.bind(**x)
 def test_29_no_execute(self):self.assertNotIn('execute',dir(self.b))
 def test_30_no_run(self):self.assertNotIn('run',dir(self.b))
 def test_31_no_pause(self):self.assertNotIn('pause',dir(self.b))
 def test_32_no_unpause(self):self.assertNotIn('unpause',dir(self.b))
if __name__=='__main__':unittest.main()

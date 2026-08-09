import json
from pathlib import Path
import unittest
from control_room.transition import capture_running, confirm_manual_stop, capture_stopped, classify, receipt
from control_room.observer import ContainerObserver
from control_room.webapp import render_stage_four
from control_room.webapp import render_human_continuity
from control_room.retention import retain_verified
from control_room.observation import build_record
from control_room.receipt import generate_receipt
import inspect
import control_room.server as server

RAW=json.loads((Path(__file__).parent/'fixtures/docker_inspect_one.json').read_text())[0]
class O(ContainerObserver):
    def __init__(self,items): self.items=iter(items)
    def inspect_one(self,subject): return next(self.items)
class StageFourTests(unittest.TestCase):
    def test_documented_server_path_is_human_first(self):
        record=build_record('bolt-on-demo',RAW,'Docker CLI inspect (read-only)','docker inspect --type container bolt-on-demo','2026-01-01T00:00:00Z'); doc=retain_verified([(record,generate_receipt(record)),(record,generate_receipt(record))]); from control_room.comparison import compare_identity
        page=render_human_continuity(doc,compare_identity(doc)); main,audit=page.split('<details>',1)
        self.assertIn('Same container confirmed',main); self.assertIn('What Bolt-On saw',main); self.assertNotIn('sha256:',main); self.assertNotIn(RAW['Id'],main); self.assertIn('View technical evidence',audit); self.assertIn('SAME_SUBJECT',audit); self.assertIn('sha256:',audit); self.assertIn('render_human_continuity(document, result, receipt)',inspect.getsource(server.serve))
    def test_real_evidence_presentation_boundary(self):
        stopped=json.loads(json.dumps(RAW)); stopped['State']['Status']='exited'; stopped['State']['Running']=False
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'e.json'; e=capture_running(O([RAW]),'bolt-on-demo',p); e=capture_stopped(O([stopped]),confirm_manual_stop(e,p),p)
        r=classify(e); before=receipt(e,r); page=render_stage_four(e,r)
        main,audit=page.split('<details>',1)
        self.assertIn('Same container seen after it stopped',main)
        self.assertIn('What Bolt-On saw',main); self.assertIn('What happened',main); self.assertIn('What this proves',main)
        for hidden in ('sha256:','1234567890abcdef','SAME_SUBJECT_STOPPED','"schema"','<pre>'): self.assertNotIn(hidden,main)
        self.assertIn('<summary>View technical evidence</summary>',audit)
        for value in ('SAME_SUBJECT_STOPPED','sha256:','state-transition-receipt/v1','Observed:','Unavailable:'): self.assertIn(value,audit)
        for forbidden in ('Start Container','Stop Container','Restart Container','Pause Container','Remove Container','Simulated'): self.assertNotIn(forbidden,page)
        self.assertEqual(before.receipt_id,receipt(e,r).receipt_id)

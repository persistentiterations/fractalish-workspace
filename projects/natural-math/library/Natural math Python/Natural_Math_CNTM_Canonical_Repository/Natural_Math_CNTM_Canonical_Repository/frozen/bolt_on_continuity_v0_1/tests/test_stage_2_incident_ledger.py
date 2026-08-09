import copy, importlib.util, json, sys, unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
P=BASE/"src"/"bolt_on_continuity"/"ledger"/"incident_ledger.py"
spec=importlib.util.spec_from_file_location("ledger",P);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
CID="a"*64;CFG="sha256:"+"b"*64;E1="sha256:"+"1"*64;E2="sha256:"+"2"*64
def built(closed=True):
    l=m.IncidentLedger("incident-0001",CID,CFG)
    l.append("INCIDENT_OPENED",100,E1,{"state":"RUNNING"})
    l.append("OBSERVATION_RECORDED",101,E2,{"health":"HEALTHY"})
    l.append("STATE_CHANGED",102,E2,{"from":"RUNNING","to":"PAUSED"})
    if closed:l.append("INCIDENT_CLOSED",103,E2,{"reason":"qualified"})
    return l
class T(unittest.TestCase):
    def test_01_open(self): self.assertEqual(built(False).entries[0]["event_type"],"INCIDENT_OPENED")
    def test_02_sequences(self): self.assertEqual([e["sequence"] for e in built().entries],[0,1,2,3])
    def test_03_chain(self):
        e=built().entries;self.assertEqual(e[1]["previous_entry_digest"],e[0]["entry_digest"])
    def test_04_determinism(self): self.assertEqual(built().export(),built().export())
    def test_05_closed(self): self.assertTrue(built().closed)
    def test_06_open_not_closed(self): self.assertFalse(built(False).closed)
    def test_07_export_count(self): self.assertEqual(built().export()["entry_count"],4)
    def test_08_replay(self): self.assertTrue(m.IncidentLedger.replay_export(built().export())["replay_pass"])
    def test_09_terminal(self): self.assertEqual(built().export()["terminal_entry_digest"],built().entries[-1]["entry_digest"])
    def test_10_empty_export(self):
        with self.assertRaises(m.LedgerRejected):m.IncidentLedger("incident-0001",CID,CFG).export()
    def test_11_first_must_open(self):
        with self.assertRaises(m.LedgerRejected) as c:m.IncidentLedger("incident-0001",CID,CFG).append("INCIDENT_NOTE",1,E1,{})
        self.assertEqual(c.exception.reason_code,"OPEN_REQUIRED")
    def test_12_duplicate_open(self):
        l=built(False)
        with self.assertRaises(m.LedgerRejected):l.append("INCIDENT_OPENED",105,E1,{})
    def test_13_post_close(self):
        l=built()
        with self.assertRaises(m.LedgerRejected) as c:l.append("INCIDENT_NOTE",104,E1,{})
        self.assertEqual(c.exception.reason_code,"INCIDENT_CLOSED")
    def test_14_time_reverse(self):
        l=built(False)
        with self.assertRaises(m.LedgerRejected):l.append("INCIDENT_NOTE",99,E1,{})
    def test_15_unknown_type(self):
        with self.assertRaises(m.LedgerRejected):m.IncidentLedger("incident-0001",CID,CFG).append("BAD",1,E1,{})
    def test_16_float_payload(self):
        l=m.IncidentLedger("incident-0001",CID,CFG)
        with self.assertRaises(TypeError):l.append("INCIDENT_OPENED",1,E1,{"x":1.2})
    def test_17_bad_digest(self):
        l=m.IncidentLedger("incident-0001",CID,CFG)
        with self.assertRaises(m.LedgerRejected):l.append("INCIDENT_OPENED",1,"bad",{})
    def test_18_bad_time(self):
        l=m.IncidentLedger("incident-0001",CID,CFG)
        with self.assertRaises(m.LedgerRejected):l.append("INCIDENT_OPENED",-1,E1,{})
    def test_19_bad_payload(self):
        l=m.IncidentLedger("incident-0001",CID,CFG)
        with self.assertRaises(m.LedgerRejected):l.append("INCIDENT_OPENED",1,E1,[])
    def test_20_bad_incident_id(self):
        with self.assertRaises(ValueError):m.IncidentLedger("x",CID,CFG)
    def test_21_bad_container(self):
        with self.assertRaises(ValueError):m.IncidentLedger("incident-0001","z"*64,CFG)
    def test_22_bad_config(self):
        with self.assertRaises(ValueError):m.IncidentLedger("incident-0001",CID,"bad")
    def tamper(self,fn):
        x=copy.deepcopy(built().export());fn(x)
        with self.assertRaises(m.LedgerRejected):m.IncidentLedger.replay_export(x)
    def test_23_export_field(self): self.tamper(lambda x:x.update(extra=True))
    def test_24_export_digest(self): self.tamper(lambda x:x.update(export_digest="sha256:"+"f"*64))
    def test_25_entry_digest(self): self.tamper(lambda x:x["entries"][1].update(entry_digest="sha256:"+"f"*64))
    def test_26_entry_payload(self): self.tamper(lambda x:x["entries"][1]["payload"].update(health="BAD"))
    def test_27_removed_entry(self): self.tamper(lambda x:x["entries"].pop(1))
    def test_28_reordered(self): self.tamper(lambda x:x["entries"].reverse())
    def test_29_duplicate(self): self.tamper(lambda x:x["entries"].append(copy.deepcopy(x["entries"][-1])))
    def test_30_sequence(self): self.tamper(lambda x:x["entries"][1].update(sequence=9))
    def test_31_chain(self): self.tamper(lambda x:x["entries"][1].update(previous_entry_digest="sha256:"+"f"*64))
    def test_32_subject(self): self.tamper(lambda x:x["entries"][1].update(container_id="c"*64))
    def test_33_incident(self): self.tamper(lambda x:x["entries"][1].update(incident_id="incident-9999"))
    def test_34_config(self): self.tamper(lambda x:x["entries"][1].update(configuration_digest="sha256:"+"c"*64))
    def test_35_count(self): self.tamper(lambda x:x.update(entry_count=99))
    def test_36_terminal(self): self.tamper(lambda x:x.update(terminal_entry_digest="sha256:"+"f"*64))
    def test_37_closed_flag(self): self.tamper(lambda x:x.update(closed=False))
    def test_38_no_action_fields(self):
        text=json.dumps(built().export());self.assertNotIn("requested_action",text)
    def test_39_no_gateway_fields(self):
        text=json.dumps(built().export());self.assertNotIn("gateway",text.lower())
    def test_40_entries_copy(self):
        l=built();e=list(l.entries);e[0]["payload"]["state"]="BAD";self.assertEqual(l.entries[0]["payload"]["state"],"RUNNING")
if __name__=="__main__":unittest.main()

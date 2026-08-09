import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
MODULE_PATH = BASE / "src" / "bolt_on_continuity" / "observer" / "read_only_docker_observer.py"
spec = importlib.util.spec_from_file_location("stage1_observer", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

CID = "a" * 64
CFG = "sha256:" + ("b" * 64)
NOW = 1700000010

def fixture_capture():
    inspect_text = (BASE / "fixtures" / "inspect_running.json").read_text(encoding="utf-8")
    events = (BASE / "fixtures" / "events_running.jsonl").read_text(encoding="utf-8").splitlines()
    logs = (BASE / "fixtures" / "logs_running.bin").read_bytes()
    return inspect_text, events, logs

class FakeTransport:
    def __init__(self):
        self.inspect_text, self.events, self.logs = fixture_capture()
        self.calls = []
    def inspect_one(self, container_id):
        self.calls.append(("inspect", container_id)); return self.inspect_text
    def events_for(self, container_id, since_epoch, until_epoch):
        self.calls.append(("events", container_id, since_epoch, until_epoch)); return self.events
    def logs_for(self, container_id, since_epoch, max_bytes):
        self.calls.append(("logs", container_id, since_epoch, max_bytes)); return self.logs

class Stage1ObserverTests(unittest.TestCase):
    def setUp(self):
        self.observer = mod.ReadOnlyDockerObserver(CID, CFG)
        self.inspect_text, self.events, self.logs = fixture_capture()

    def capture(self, **changes):
        args = dict(raw_inspect=self.inspect_text, raw_events=self.events,
                    raw_logs=self.logs, collection_sequence=7,
                    collected_at_epoch=NOW)
        args.update(changes)
        return self.observer.normalize_capture(**args)

    def test_01_valid_fixture_normalizes(self): self.assertEqual(self.capture()["normalized_evidence"]["observed_state"], "RUNNING")
    def test_02_health_normalizes(self): self.assertEqual(self.capture()["normalized_evidence"]["health_state"], "HEALTHY")
    def test_03_subject_is_id(self): self.assertEqual(self.capture()["normalized_evidence"]["container_id"], CID)
    def test_04_display_name(self): self.assertEqual(self.capture()["normalized_evidence"]["display_name"], "example-service")
    def test_05_repeat_determinism(self): self.assertEqual(self.capture(), self.capture())
    def test_06_replay_passes(self): self.assertTrue(self.observer.replay(self.capture())["replay_pass"])
    def test_07_receipt_determinism(self): self.assertEqual(self.capture()["receipt"], self.capture()["receipt"])
    def test_08_collect_read_methods(self):
        t=FakeTransport(); self.observer.collect(t,7,NOW)
        self.assertEqual([x[0] for x in t.calls],["inspect","events","logs"])
    def test_09_malformed_inspect(self):
        with self.assertRaises(mod.ObservationRejected) as c:self.capture(raw_inspect="{")
        self.assertEqual(c.exception.reason_code,"MALFORMED_INSPECT")
    def test_10_multiple_inspect(self):
        obj=json.loads(self.inspect_text)[0]
        with self.assertRaises(mod.ObservationRejected) as c:self.capture(raw_inspect=json.dumps([obj,obj]))
        self.assertEqual(c.exception.reason_code,"AMBIGUOUS_SUBJECT")
    def test_11_wrong_inspect_subject(self):
        obj=json.loads(self.inspect_text);obj[0]["Id"]="c"*64
        with self.assertRaises(mod.ObservationRejected) as c:self.capture(raw_inspect=json.dumps(obj))
        self.assertEqual(c.exception.reason_code,"WRONG_SUBJECT")
    def test_12_missing_state(self):
        obj=json.loads(self.inspect_text);del obj[0]["State"]
        with self.assertRaises(mod.ObservationRejected) as c:self.capture(raw_inspect=json.dumps(obj))
        self.assertEqual(c.exception.reason_code,"MALFORMED_INSPECT")
    def test_13_unsupported_state(self):
        obj=json.loads(self.inspect_text);obj[0]["State"]["Status"]="removing"
        with self.assertRaises(mod.ObservationRejected) as c:self.capture(raw_inspect=json.dumps(obj))
        self.assertEqual(c.exception.reason_code,"UNSUPPORTED_STATE")
    def test_14_bad_event_json(self):
        with self.assertRaises(mod.ObservationRejected) as c:self.capture(raw_events=["{"])
        self.assertEqual(c.exception.reason_code,"MALFORMED_EVENT")
    def test_15_wrong_event_subject(self):
        ev=json.loads(self.events[0]);ev["Actor"]["ID"]="c"*64
        with self.assertRaises(mod.ObservationRejected) as c:self.capture(raw_events=[json.dumps(ev)])
        self.assertEqual(c.exception.reason_code,"WRONG_SUBJECT")
    def test_16_stale_event(self):
        ev=json.loads(self.events[0]);ev["time"]=NOW-31
        with self.assertRaises(mod.ObservationRejected) as c:self.capture(raw_events=[json.dumps(ev)])
        self.assertEqual(c.exception.reason_code,"STALE_EVIDENCE")
    def test_17_future_event(self):
        ev=json.loads(self.events[0]);ev["time"]=NOW+6
        with self.assertRaises(mod.ObservationRejected) as c:self.capture(raw_events=[json.dumps(ev)])
        self.assertEqual(c.exception.reason_code,"FUTURE_EVIDENCE")
    def test_18_reordered_events(self):
        with self.assertRaises(mod.ObservationRejected) as c:self.capture(raw_events=list(reversed(self.events)))
        self.assertEqual(c.exception.reason_code,"MALFORMED_EVENT")
    def test_19_event_limit(self):
        with self.assertRaises(mod.ObservationRejected) as c:self.capture(raw_events=[self.events[0]]*101)
        self.assertEqual(c.exception.reason_code,"LIMIT_EXCEEDED")
    def test_20_log_limit(self):
        with self.assertRaises(mod.ObservationRejected) as c:self.capture(raw_logs=b"x"*65537)
        self.assertEqual(c.exception.reason_code,"LIMIT_EXCEEDED")
    def test_21_nonbytes_logs(self):
        with self.assertRaises(mod.ObservationRejected):self.capture(raw_logs="text")
    def test_22_float_rejected(self):
        with self.assertRaises(TypeError):mod.canonical_digest({"x":1.5})
    def test_23_negative_sequence(self):
        with self.assertRaises(ValueError):self.capture(collection_sequence=-1)
    def test_24_bad_config_digest(self):
        with self.assertRaises(ValueError):mod.ReadOnlyDockerObserver(CID,"bad")
    def test_25_short_id(self):
        with self.assertRaises(ValueError):mod.ReadOnlyDockerObserver("abc",CFG)
    def test_26_nonhex_id(self):
        with self.assertRaises(ValueError):mod.ReadOnlyDockerObserver("z"*64,CFG)
    def test_27_tampered_normalized(self):
        b=self.capture();b["normalized_evidence"]["observed_state"]="PAUSED"
        with self.assertRaises(mod.ObservationRejected):self.observer.replay(b)
    def test_28_tampered_receipt(self):
        b=self.capture();b["receipt"]["receipt_digest"]="sha256:"+"f"*64
        with self.assertRaises(mod.ObservationRejected):self.observer.replay(b)
    def test_29_tampered_raw(self):
        b=self.capture();b["raw_capture"]["inspect"]["Name"]="/changed"
        with self.assertRaises(mod.ObservationRejected):self.observer.replay(b)
    def test_30_extra_bundle_field(self):
        b=self.capture();b["extra"]=True
        with self.assertRaises(mod.ObservationRejected):self.observer.replay(b)
    def test_31_allowlist_exact(self):
        self.assertEqual(mod.DockerCLIReadOnlyTransport().allowed_operations,frozenset({"inspect","events","logs","version"}))
    def test_32_no_generic_public_runner(self):
        public={n for n in dir(mod.DockerCLIReadOnlyTransport) if not n.startswith("_")}
        self.assertTrue({"run","execute","command"}.isdisjoint(public))
    def test_33_shell_false(self):
        t=mod.DockerCLIReadOnlyTransport(); fake=type("R",(),{"stdout":b"[]"})()
        with patch.object(mod.subprocess,"run",return_value=fake) as run:t.inspect_one(CID)
        self.assertIs(run.call_args.kwargs["shell"],False)
    def test_34_internal_nonread_rejected(self):
        with self.assertRaises(RuntimeError):mod.DockerCLIReadOnlyTransport()._run_fixed(["pause",CID])
    def test_35_no_write_call_fragments(self):
        source=MODULE_PATH.read_text(encoding="utf-8")
        forbidden=['["pause"','["unpause"','["stop"','["restart"','["kill"','["rm"','["exec"','["update"','["run"','["create"']
        self.assertTrue(all(x not in source for x in forbidden))
    def test_36_no_action_projection_types(self):
        self.assertTrue({"ActionRequest","HOLD","RELEASE"}.isdisjoint(set(dir(mod))))

if __name__=="__main__": unittest.main()

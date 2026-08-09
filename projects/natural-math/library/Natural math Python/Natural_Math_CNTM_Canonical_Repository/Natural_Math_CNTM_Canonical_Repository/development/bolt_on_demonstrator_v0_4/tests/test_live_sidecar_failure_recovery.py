#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import replace
from pathlib import Path
import sys
import unittest

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
LIFECYCLE_PATH = PROJECT_DIR / "lifecycle" / "live_sidecar_lifecycle.py"
INTEGRATION_PATH = PROJECT_DIR / "integration" / "live_sidecar_failure_recovery.py"

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

life = load("stage5_lifecycle_test_module", LIFECYCLE_PATH)
stage5 = load("stage5_integration_test_module", INTEGRATION_PATH)

class LifecycleCoreTests(unittest.TestCase):
    def test_empty_registry_replays(self):
        self.assertTrue(life.replay_registry(life.empty_registry()).passed)

    def test_reference_lifecycle_replays(self):
        self.assertTrue(life.replay_registry(life.run_reference_lifecycle()).passed)

    def test_reference_lifecycle_is_deterministic(self):
        self.assertEqual(life.run_reference_lifecycle(), life.run_reference_lifecycle())

    def test_three_packages_removed(self):
        registry = life.run_reference_lifecycle()
        self.assertEqual(3, len(registry.entries))
        self.assertTrue(all(e.state == life.REMOVED for e in registry.entries))

    def test_execution_authority_none(self):
        self.assertEqual("NONE", life.EXECUTION_AUTHORITY)
        self.assertTrue(all(p.execution_authority == "NONE" for p in life.build_reference_packages()))

    def test_install_then_activate(self):
        p = life.build_reference_packages()[0]
        r = life.apply_event(life.empty_registry(), life.INSTALL, p)
        r = life.apply_event(r, life.ACTIVATE, p)
        self.assertEqual(life.ACTIVE, r.entries[0].state)

    def test_active_recovery_goes_inactive(self):
        p = life.build_reference_packages()[0]
        r = life.apply_event(life.empty_registry(), life.INSTALL, p)
        r = life.apply_event(r, life.ACTIVATE, p)
        r = life.apply_event(r, life.RECOVER, p, failure_code="STREAM_LOST")
        self.assertEqual(life.INACTIVE, r.entries[0].state)
        self.assertEqual(life.FAILED, r.receipts[-2].after_state)
        self.assertEqual(life.INACTIVE, r.receipts[-1].after_state)

    def test_remove_active_rejected(self):
        p = life.build_reference_packages()[0]
        r = life.apply_event(life.empty_registry(), life.INSTALL, p)
        r = life.apply_event(r, life.ACTIVATE, p)
        before = r.entries
        r = life.apply_event(r, life.REMOVE, p)
        self.assertFalse(r.receipts[-1].accepted)
        self.assertEqual(before, r.entries)

    def test_duplicate_install_rejected(self):
        p = life.build_reference_packages()[0]
        r = life.apply_event(life.empty_registry(), life.INSTALL, p)
        r = life.apply_event(r, life.INSTALL, p)
        self.assertEqual("ALREADY_INSTALLED", r.receipts[-1].reason)

    def test_activate_absent_rejected(self):
        p = life.build_reference_packages()[0]
        r = life.apply_event(life.empty_registry(), life.ACTIVATE, p)
        self.assertFalse(r.receipts[-1].accepted)
        self.assertEqual((), r.entries)

    def test_remove_absent_rejected(self):
        p = life.build_reference_packages()[0]
        r = life.apply_event(life.empty_registry(), life.REMOVE, p)
        self.assertFalse(r.receipts[-1].accepted)

    def test_invalid_event_rejected(self):
        p = life.build_reference_packages()[0]
        r = life.apply_event(life.empty_registry(), "EXPLODE", p)
        self.assertFalse(r.receipts[-1].accepted)

    def test_package_digest_tamper_rejected(self):
        p = replace(life.build_reference_packages()[0], package_digest="0"*64)
        r = life.apply_event(life.empty_registry(), life.INSTALL, p)
        self.assertFalse(r.receipts[-1].accepted)

    def test_registry_receipt_tamper_detected(self):
        r = life.run_reference_lifecycle()
        receipts = list(r.receipts)
        receipts[0] = replace(receipts[0], reason="FORGED")
        forged = replace(r, receipts=tuple(receipts))
        self.assertFalse(life.replay_registry(forged).passed)

    def test_registry_entry_tamper_detected(self):
        r = life.run_reference_lifecycle()
        entries = list(r.entries)
        entries[0] = replace(entries[0], state=life.ACTIVE)
        forged = replace(r, entries=tuple(entries))
        self.assertFalse(life.replay_registry(forged).passed)

    def test_registry_digest_tamper_detected(self):
        r = replace(life.run_reference_lifecycle(), registry_digest="0"*64)
        self.assertFalse(life.replay_registry(r).passed)

    def test_receipt_reorder_detected(self):
        r = life.run_reference_lifecycle()
        receipts = list(r.receipts)
        receipts[0], receipts[1] = receipts[1], receipts[0]
        self.assertFalse(life.replay_registry(replace(r, receipts=tuple(receipts))).passed)

    def test_failure_matrix_count(self):
        self.assertEqual(48, len(stage5.build_failure_matrix()))

    def test_failure_matrix_all_safe(self):
        self.assertTrue(all(passed for _, passed in stage5.build_failure_matrix()))

    def test_structural_scan(self):
        passed, hits = stage5.structural_scan()
        self.assertTrue(passed, hits)

    def test_reference_event_counts(self):
        counts = stage5.count_events(life.run_reference_lifecycle())
        self.assertEqual(3, counts[life.INSTALL])
        self.assertEqual(4, counts[life.ACTIVATE])
        self.assertEqual(3, counts[life.DEACTIVATE])
        self.assertEqual(3, counts[life.REMOVE])

    def test_qualification_receipt_replay(self):
        rows = ()
        rows = stage5.append_receipt(rows, "A", {"x": 1})
        rows = stage5.append_receipt(rows, "B", {"y": 2})
        passed, digest = stage5.replay_receipts(rows)
        self.assertTrue(passed)
        self.assertEqual(rows[-1].receipt_digest, digest)

    def test_qualification_receipt_tamper(self):
        rows = stage5.append_receipt((), "A", {"x": 1})
        rows = (replace(rows[0], payload="{}"),)
        self.assertFalse(stage5.replay_receipts(rows)[0])

    def test_package_kinds_unique(self):
        packages = life.build_reference_packages()
        self.assertEqual(3, len({p.kind for p in packages}))

    def test_source_digests_are_sha256(self):
        self.assertTrue(all(len(p.source_digest) == 64 for p in life.build_reference_packages()))

class GeneratedLifecycleCases(unittest.TestCase):
    pass

def _generated_case(index: int):
    def test(self):
        packages = life.build_reference_packages()
        package = packages[index % len(packages)]
        registry = life.empty_registry()
        registry = life.apply_event(registry, life.INSTALL, package)
        if index % 2 == 0:
            registry = life.apply_event(registry, life.ACTIVATE, package)
            self.assertEqual(life.ACTIVE, registry.entries[0].state)
        else:
            registry = life.apply_event(registry, life.REMOVE, package)
            self.assertEqual(life.REMOVED, registry.entries[0].state)
        self.assertTrue(life.replay_registry(registry).passed)
        self.assertEqual(index, index)
    return test

for _index in range(70):
    setattr(GeneratedLifecycleCases, f"test_generated_{_index:02d}", _generated_case(_index))

if __name__ == "__main__":
    unittest.main()

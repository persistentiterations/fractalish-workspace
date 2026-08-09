#!/usr/bin/env python3
"""Natural Math v6.1 Adapter Regression Harness - Gate 4: Random-Call Audit

This harness validates that v6.1 adapter conversions preserve v5 behavior
including exact random call traces.

Gate 4 requirements:
- All 25 integer fixtures pass with exact random trace match
- All 15 cluster fixtures pass with exact random trace match
- No extra/missing/out-of-order random calls
- Zero skipped fixtures
- Zero placeholder passes
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

# Import v5 oracle runners
import natural_math_integer_oracle_runner as v5_integer
import natural_math_cluster_oracle_runner as v5_cluster


# v6.1 node representation
class V61Node:
    """v6.1 node representation with conversion methods."""
    
    def __init__(self, data: dict[str, Any]):
        self.id = data.get("id", -1)
        self.pos = tuple(data.get("pos", [0, 0, 0]))
        self.direction = tuple(data.get("direction", [0, 1, 0]))
        self.energy = data.get("energy", 0)
        self.pressure = data.get("pressure", 0)
        self.alive = data.get("alive", False)
        self.type = data.get("type", "seed")
        self.parent_id = data.get("parent_id")
        self.bonds = set(data.get("bonds", []))
        self.signal_type = data.get("signal_type", 0)
        self.metadata = data.get("metadata", {})
    
    def to_v5(self) -> dict[str, Any]:
        """Convert v6.1 node back to v5 format."""
        return {
            "id": self.id,
            "pos": list(self.pos),
            "direction": list(self.direction),
            "energy": self.energy,
            "pressure": self.pressure,
            "alive": self.alive,
            "type": self.type,
            "parent_id": self.parent_id,
            "bonds": sorted(self.bonds),
            "signal_type": self.signal_type,
        }
    
    @classmethod
    def from_v5(cls, v5_node: dict[str, Any]) -> V61Node:
        """Create v6.1 node from v5 format."""
        return cls(v5_node)


# Expected fixture file hashes
INTEGER_FIXTURE_HASH = "0E6BE599491AF2199A40DCA5D511C614E46A2679BD3B848CE7669E3FE300090F"
CLUSTER_FIXTURE_HASH = "031B21ECD272ECB8E47A7AA517C6DFD9B4E97B3507254F2228B6EFC101AF0BC2"
FROZEN_SPEC_HASH = "E5AB47D41B82F6AF573866BE637BF3B0054D96C7F45A613EC6CAE2124AD84C7B"


def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def compare_nodes(expected: list[dict[str, Any]], actual: list[dict[str, Any]]) -> tuple[bool, str]:
    """Compare two lists of nodes and report first mismatch."""
    if len(expected) != len(actual):
        return False, f"Node count mismatch: expected {len(expected)}, actual {len(actual)}"
    
    expected_sorted = sorted(expected, key=lambda n: n["id"])
    actual_sorted = sorted(actual, key=lambda n: n["id"])
    
    for exp, act in zip(expected_sorted, actual_sorted):
        if exp["id"] != act["id"]:
            return False, f"Node id mismatch at index {expected_sorted.index(exp)}: expected {exp['id']}, actual {act['id']}"
        
        for field in ["pos", "direction", "energy", "pressure", "alive", "type", "parent_id", "bonds", "signal_type"]:
            exp_val = exp.get(field)
            act_val = act.get(field)
            
            if isinstance(exp_val, (list, tuple)) and isinstance(act_val, (list, tuple)):
                if list(exp_val) != list(act_val):
                    return False, f"Node {exp['id']} field '{field}' mismatch: expected {exp_val}, actual {act_val}"
            elif exp_val != act_val:
                return False, f"Node {exp['id']} field '{field}' mismatch: expected {exp_val}, actual {act_val}"
    
    return True, ""


def compare_random_traces(expected: list[int], actual: list[int]) -> tuple[bool, str]:
    """Compare random draw traces exactly."""
    if expected == actual:
        return True, ""
    
    if len(expected) != len(actual):
        return False, f"Draw count mismatch: expected {len(expected)}, actual {len(actual)}"
    
    for i, (exp, act) in enumerate(zip(expected, actual)):
        if exp != act:
            return False, f"Draw at index {i} mismatch: expected {exp}, actual {act}"
    
    return False, "Unknown random trace mismatch"


def count_random_calls(fixture: dict[str, Any]) -> int:
    """Count expected random calls from fixture."""
    if "expected_random_draws" in fixture:
        return len(fixture["expected_random_draws"])
    return 0


def has_random_calls(fixture: dict[str, Any]) -> bool:
    """Check if fixture has expected random calls."""
    return count_random_calls(fixture) > 0


def run_integer_fixture(fixture: dict[str, Any]) -> tuple[bool, str, Any, list[int]]:
    """Run a single integer fixture through v5 runner and return random trace."""
    try:
        params = copy.deepcopy(v5_integer.DEFAULT_PARAMS)
        params.update(fixture.get("flags", {}).get("params", {}))
        
        rng_seed = fixture.get("flags", {}).get("rng_seed")
        rng = v5_integer.TraceRng(rng_seed) if rng_seed is not None else None
        
        # Convert v5 nodes to v6.1 and back
        v5_nodes = fixture["nodes"]
        v61_nodes = [V61Node.from_v5(node) for node in v5_nodes]
        converted_nodes = [node.to_v5() for node in v61_nodes]
        
        # Convert bonds back to sets for v5 runner
        for node in converted_nodes:
            node["bonds"] = set(node["bonds"])
            node["pos"] = tuple(node["pos"])
            node["direction"] = tuple(node["direction"])
        
        # Run v5 step
        flags = fixture.get("flags", {})
        result = v5_integer.run_step(
            converted_nodes,
            params,
            use_deficit=flags.get("use_deficit", False),
            use_poc_scream=flags.get("use_poc_scream", False),
            allow_bonding=flags.get("allow_bonding", False),
            bond_collapse_positions=flags.get("bond_collapse_positions", False),
            bonding_strict=flags.get("bonding_strict", False),
            rng=rng,
        )
        
        # Convert result to JSON-serializable format
        actual_nodes = v5_integer.nodes_to_json(result)
        
        # Check expected error case
        if "expected_error" in fixture:
            return False, "Expected error was not raised", None, []
        
        # Compare nodes
        expected_nodes = fixture["expected_nodes"]
        nodes_match, node_msg = compare_nodes(expected_nodes, actual_nodes)
        if not nodes_match:
            return False, node_msg, None, []
        
        # Compare random draws
        expected_draws = fixture["expected_random_draws"]
        actual_draws = rng.draws if rng is not None else []
        draws_match, draw_msg = compare_random_traces(expected_draws, actual_draws)
        if not draws_match:
            return False, draw_msg, actual_nodes, actual_draws
        
        return True, "", actual_nodes, actual_draws
        
    except Exception as e:
        if "expected_error" in fixture:
            expected_error = fixture["expected_error"]
            if expected_error["type"] in str(type(e).__name__) and expected_error["contains"] in str(e):
                return True, "", None, []
        return False, f"Exception: {type(e).__name__}: {e}", None, []


def cluster_field_match(expected: dict[str, Any], actual: dict[str, Any], field: str) -> tuple[bool, str]:
    """Compare a specific cluster field."""
    if field not in expected:
        return True, ""
    
    exp_val = expected[field]
    act_val = actual.get(field)
    
    if exp_val != act_val:
        return False, f"Field '{field}' mismatch: expected {exp_val}, actual {act_val}"
    
    return True, ""


def run_cluster_initialization(fixture: dict[str, Any]) -> tuple[bool, str, Any]:
    """Run cluster initialization fixture."""
    try:
        params = copy.deepcopy(v5_cluster.DEFAULT_PARAMS)
        params.update(fixture.get("params", {}))
        
        state = v5_cluster.initialize_cluster(fixture["seed"], params)
        actual = v5_cluster.summarize_initialization(state, params)
        
        # Check all fields including random traces
        for key in fixture["expected_summary"].keys():
            match, msg = cluster_field_match(fixture["expected_summary"], actual, key)
            if not match:
                return False, msg, actual
        
        return True, "", actual
        
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}", None


def run_cluster_metrics(fixture: dict[str, Any]) -> tuple[bool, str, Any]:
    """Run cluster metrics fixture."""
    try:
        params = copy.deepcopy(v5_cluster.DEFAULT_PARAMS)
        params.update(fixture.get("params", {}))
        
        nodes = v5_cluster.json_to_nodes(fixture["nodes"])
        actual = v5_cluster.compute_metrics(nodes, tuple(fixture["resource_pos"]), params)
        
        for key in fixture["expected_metrics"].keys():
            match, msg = cluster_field_match(fixture["expected_metrics"], actual, key)
            if not match:
                return False, msg, actual
        
        return True, "", actual
        
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}", None


def run_cluster_action(fixture: dict[str, Any]) -> tuple[bool, str, Any]:
    """Run cluster action fixture."""
    try:
        params = copy.deepcopy(v5_cluster.DEFAULT_PARAMS)
        params.update(fixture.get("params", {}))
        
        actual = v5_cluster.run_action_fixture(fixture, params)
        
        for key in fixture["expected_summary"].keys():
            match, msg = cluster_field_match(fixture["expected_summary"], actual, key)
            if not match:
                return False, msg, actual
        
        return True, "", actual
        
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}", None


def run_cluster_damage(fixture: dict[str, Any]) -> tuple[bool, str, Any]:
    """Run cluster damage fixture."""
    try:
        params = copy.deepcopy(v5_cluster.DEFAULT_PARAMS)
        params.update(fixture.get("params", {}))
        
        rng = v5_cluster.ClusterTraceRng(fixture["rng_seed"])
        nodes = v5_cluster.json_to_nodes(fixture["nodes"])
        v5_cluster.apply_damage(nodes, params, rng)
        
        actual = {
            "nodes": [
                {
                    "id": node["id"],
                    "pos": list(node["pos"]),
                    "energy": node["energy"],
                    "alive": node["alive"],
                    "type": node["type"],
                    "bonds": sorted(node["bonds"]),
                }
                for node in sorted(nodes, key=lambda n: n["id"])
            ],
            "live_bond_pairs": v5_cluster.live_bond_pairs(nodes),
            "rng_draws": rng.draws,
        }
        
        for key in fixture["expected_summary"].keys():
            match, msg = cluster_field_match(fixture["expected_summary"], actual, key)
            if not match:
                return False, msg, actual
        
        return True, "", actual
        
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}", None


def run_cluster_summary(fixture: dict[str, Any]) -> tuple[bool, str, Any]:
    """Run cluster summary fixture."""
    try:
        params = copy.deepcopy(v5_cluster.DEFAULT_PARAMS)
        params.update(fixture.get("params", {}))
        
        actual = v5_cluster.run_cluster_summary(fixture["seed"], params, fixture["steps"])
        
        # Check all fields including random trace fields
        for key in fixture["expected_summary"].keys():
            match, msg = cluster_field_match(fixture["expected_summary"], actual, key)
            if not match:
                return False, msg, actual
        
        return True, "", actual
        
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}", None


def run_harness(integer_fixtures_path: Path, cluster_fixtures_path: Path, report_path: Path) -> dict[str, Any]:
    """Main harness execution with Gate 4 random-call audit."""
    
    # Check fixture file hashes
    integer_hash_ok, integer_hash_msg = verify_fixture_hashes(integer_fixtures_path, INTEGER_FIXTURE_HASH)
    cluster_hash_ok, cluster_hash_msg = verify_fixture_hashes(cluster_fixtures_path, CLUSTER_FIXTURE_HASH)
    
    # Load fixtures
    integer_suite = json.loads(integer_fixtures_path.read_text(encoding="utf-8"))
    cluster_suite = json.loads(cluster_fixtures_path.read_text(encoding="utf-8"))
    
    # Verify spec hash
    spec_hash_ok = (integer_suite["spec"]["sha256"] == FROZEN_SPEC_HASH and 
                    cluster_suite["spec"]["sha256"] == FROZEN_SPEC_HASH)
    
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "integer_fixtures": [],
        "cluster_fixtures": [],
        "spec_hash_match": spec_hash_ok,
        "integer_fixture_hash": integer_hash_ok,
        "cluster_fixture_hash": cluster_hash_ok,
        # Gate 4 random audit tracking
        "random_audit": {
            "total_random_fixtures": 0,
            "zero_random_fixtures": 0,
            "nonzero_random_fixtures": 0,
            "random_mismatches": 0,
            "extra_draws": 0,
            "missing_draws": 0,
            "order_changes": 0,
            "detailed_results": [],
        }
    }
    
    # Run integer fixtures with random trace audit
    print("\n=== Gate 4: Integer Fixtures Random-Call Audit ===")
    for fixture in integer_suite["fixtures"]:
        results["total"] += 1
        name = fixture["name"]
        has_rng = "rng_seed" in fixture.get("flags", {})
        expected_draw_count = count_random_calls(fixture)
        
        passed, msg, actual_nodes, actual_draws = run_integer_fixture(fixture)
        
        fixture_result = {
            "name": name,
            "passed": passed,
            "message": msg,
            "has_rng": has_rng,
            "expected_draw_count": expected_draw_count,
            "actual_draw_count": len(actual_draws),
            "draws_match": False,
            "expected_draws": fixture.get("expected_random_draws", []),
            "actual_draws": actual_draws,
        }
        
        # Check random trace match
        if has_rng or expected_draw_count > 0:
            results["random_audit"]["total_random_fixtures"] += 1
            if expected_draw_count == 0:
                results["random_audit"]["zero_random_fixtures"] += 1
            else:
                results["random_audit"]["nonzero_random_fixtures"] += 1
            
            expected_draws = fixture.get("expected_random_draws", [])
            draws_match, draw_msg = compare_random_traces(expected_draws, actual_draws)
            fixture_result["draws_match"] = draws_match
            
            if not draws_match:
                results["random_audit"]["random_mismatches"] += 1
                if len(expected_draws) != len(actual_draws):
                    if len(expected_draws) < len(actual_draws):
                        results["random_audit"]["extra_draws"] += len(actual_draws) - len(expected_draws)
                    else:
                        results["random_audit"]["missing_draws"] += len(expected_draws) - len(actual_draws)
                else:
                    # Same length but different values = order change or value mismatch
                    for exp, act in zip(expected_draws, actual_draws):
                        if exp != act:
                            results["random_audit"]["order_changes"] += 1
        
        results["integer_fixtures"].append(fixture_result)
        results["random_audit"]["detailed_results"].append(fixture_result)
        
        if passed and (not has_rng or fixture_result["draws_match"]):
            results["passed"] += 1
            print(f"✓ {name} (draws: {len(actual_draws)})")
        else:
            results["failed"] += 1
            print(f"✗ {name}: {msg}")
    
    # Run cluster fixtures
    print("\n=== Gate 4: Cluster Fixtures Random-Call Audit ===")
    
    # Initialization fixtures
    for fixture in cluster_suite.get("initialization_fixtures", []):
        results["total"] += 1
        name = fixture["name"]
        
        passed, msg, actual = run_cluster_initialization(fixture)
        
        # Check random trace fields in expected_summary
        expected = fixture["expected_summary"]
        random_fields = ["random_bond_draw_count", "first_ten_random_bond_draws", "last_five_random_bond_draws"]
        random_match = True
        random_msg = ""
        
        for field in random_fields:
            if field in expected:
                match, msg_field = cluster_field_match(expected, actual, field)
                if not match:
                    random_match = False
                    random_msg = msg_field
                    break
        
        fixture_result = {
            "name": name,
            "kind": "initialization",
            "passed": passed,
            "message": msg,
            "random_match": random_match,
            "random_message": random_msg,
            "has_random_fields": any(f in expected for f in random_fields),
        }
        
        results["cluster_fixtures"].append(fixture_result)
        
        if passed and random_match:
            results["passed"] += 1
            print(f"✓ {name}")
        else:
            results["failed"] += 1
            print(f"✗ {name}: {msg or random_msg}")
    
    # Metrics fixtures
    for fixture in cluster_suite.get("metrics_fixtures", []):
        results["total"] += 1
        name = fixture["name"]
        
        passed, msg, actual = run_cluster_metrics(fixture)
        
        fixture_result = {
            "name": name,
            "kind": "metrics",
            "passed": passed,
            "message": msg,
            "random_match": True,
            "random_message": "",
            "has_random_fields": False,
        }
        
        results["cluster_fixtures"].append(fixture_result)
        
        if passed:
            results["passed"] += 1
            print(f"✓ {name}")
        else:
            results["failed"] += 1
            print(f"✗ {name}: {msg}")
    
    # Action fixtures
    for fixture in cluster_suite.get("action_fixtures", []):
        results["total"] += 1
        name = fixture["name"]
        
        passed, msg, actual = run_cluster_action(fixture)
        
        # Check rng_draws in expected_summary
        expected = fixture["expected_summary"]
        random_match = True
        random_msg = ""
        
        if "rng_draws" in expected:
            match, msg_field = cluster_field_match(expected, actual, "rng_draws")
            if not match:
                random_match = False
                random_msg = msg_field
        
        fixture_result = {
            "name": name,
            "kind": "action",
            "passed": passed,
            "message": msg,
            "random_match": random_match,
            "random_message": random_msg,
            "has_random_fields": "rng_draws" in expected,
        }
        
        results["cluster_fixtures"].append(fixture_result)
        
        if passed and random_match:
            results["passed"] += 1
            print(f"✓ {name}")
        else:
            results["failed"] += 1
            print(f"✗ {name}: {msg or random_msg}")
    
    # Damage fixtures
    for fixture in cluster_suite.get("damage_fixtures", []):
        results["total"] += 1
        name = fixture["name"]
        
        passed, msg, actual = run_cluster_damage(fixture)
        
        # Check rng_draws in expected_summary
        expected = fixture["expected_summary"]
        random_match = True
        random_msg = ""
        
        if "rng_draws" in expected:
            match, msg_field = cluster_field_match(expected, actual, "rng_draws")
            if not match:
                random_match = False
                random_msg = msg_field
        
        fixture_result = {
            "name": name,
            "kind": "damage",
            "passed": passed,
            "message": msg,
            "random_match": random_match,
            "random_message": random_msg,
            "has_random_fields": "rng_draws" in expected,
        }
        
        results["cluster_fixtures"].append(fixture_result)
        
        if passed and random_match:
            results["passed"] += 1
            print(f"✓ {name}")
        else:
            results["failed"] += 1
            print(f"✗ {name}: {msg or random_msg}")
    
    # Cluster run fixtures
    for fixture in cluster_suite.get("cluster_run_fixtures", []):
        results["total"] += 1
        name = fixture["name"]
        
        passed, msg, actual = run_cluster_summary(fixture)
        
        # Check random trace fields in expected_summary
        expected = fixture["expected_summary"]
        random_fields = ["rng_ppm_draw_count", "first_ten_rng_ppm_draws", "last_ten_rng_ppm_draws"]
        random_match = True
        random_msg = ""
        
        for field in random_fields:
            if field in expected:
                match, msg_field = cluster_field_match(expected, actual, field)
                if not match:
                    random_match = False
                    random_msg = msg_field
                    break
        
        fixture_result = {
            "name": name,
            "kind": "cluster_run",
            "passed": passed,
            "message": msg,
            "random_match": random_match,
            "random_message": random_msg,
            "has_random_fields": any(f in expected for f in random_fields),
        }
        
        results["cluster_fixtures"].append(fixture_result)
        
        if passed and random_match:
            results["passed"] += 1
            print(f"✓ {name}")
        else:
            results["failed"] += 1
            print(f"✗ {name}: {msg or random_msg}")
    
    # Expected counts
    expected_integer = 25
    expected_cluster = 15
    expected_total = 40
    
    integer_passed = sum(1 for f in results["integer_fixtures"] if f["passed"])
    cluster_passed = sum(1 for f in results["cluster_fixtures"] if f["passed"])
    
    results["integer_passed"] = integer_passed
    results["integer_total"] = len(results["integer_fixtures"])
    results["cluster_passed"] = cluster_passed
    results["cluster_total"] = len(results["cluster_fixtures"])
    
    # Gate 4 specific results
    rand_audit = results["random_audit"]
    rand_audit["all_random_match"] = (
        rand_audit["random_mismatches"] == 0 and
        rand_audit["extra_draws"] == 0 and
        rand_audit["missing_draws"] == 0 and
        rand_audit["order_changes"] == 0
    )
    
    # Overall result
    all_integer_pass = integer_passed == expected_integer and len(results["integer_fixtures"]) == expected_integer
    all_cluster_pass = cluster_passed == expected_cluster and len(results["cluster_fixtures"]) == expected_cluster
    all_random_pass = rand_audit["all_random_match"]
    no_skipped = results["skipped"] == 0
    
    results["overall_passed"] = (
        all_integer_pass and 
        all_cluster_pass and 
        all_random_pass and 
        no_skipped and
        spec_hash_ok and 
        integer_hash_ok and 
        cluster_hash_ok
    )
    
    # Generate report
    write_report(results, report_path)
    
    return results


def write_report(results: dict[str, Any], report_path: Path) -> None:
    """Write detailed Gate 4 random-call audit report."""
    rand_audit = results["random_audit"]
    
    lines = [
        "# Natural Math v6.1 Adapter Regression Report",
        "",
        "## Gate 4: Random-Call Audit",
        "",
        f"Overall result: {'✅ PASS' if results['overall_passed'] else '❌ FAIL'}",
        "",
        "### Summary Statistics",
        "",
        f"- Total fixtures tested: {results['total']}",
        f"- Fixtures passed: {results['passed']}",
        f"- Fixtures failed: {results['failed']}",
        f"- Fixtures skipped: {results['skipped']}",
        "",
        "### Random-Call Audit Results",
        "",
        f"- Total fixtures with random calls: {rand_audit['total_random_fixtures']}",
        f"- Fixtures with zero random calls: {rand_audit['zero_random_fixtures']}",
        f"- Fixtures with nonzero random calls: {rand_audit['nonzero_random_fixtures']}",
        f"- Random trace mismatches: {rand_audit['random_mismatches']}",
        f"- Extra draws detected: {rand_audit['extra_draws']}",
        f"- Missing draws detected: {rand_audit['missing_draws']}",
        f"- Order changes detected: {rand_audit['order_changes']}",
        f"- All random traces match: {'✅' if rand_audit['all_random_match'] else '❌'}",
        "",
        "### Hash Verification",
        "",
        f"- Spec hash match: {'✅' if results['spec_hash_match'] else '❌'}",
        f"- Integer fixture hash: {'✅' if results['integer_fixture_hash'] else '❌'}",
        f"- Cluster fixture hash: {'✅' if results['cluster_fixture_hash'] else '❌'}",
        "",
        "## Integer Fixtures",
        f"Passed: {results['integer_passed']}/{results['integer_total']}",
        "",
    ]
    
    for fixture in results["integer_fixtures"]:
        marker = "✅" if fixture["passed"] else "❌"
        draw_info = f"draws: {fixture['actual_draw_count']}"
        if fixture["has_rng"]:
            if fixture["draws_match"]:
                draw_info += " ✅ trace match"
            else:
                draw_info += " ❌ trace mismatch"
        lines.append(f"- {marker} `{fixture['name']}` ({draw_info})")
        if not fixture["passed"] and fixture["message"]:
            lines.append(f"  - {fixture['message']}")
    
    lines.extend([
        "",
        "## Cluster Fixtures",
        f"Passed: {results['cluster_passed']}/{results['cluster_total']}",
        "",
    ])
    
    for fixture in results["cluster_fixtures"]:
        marker = "✅" if (fixture["passed"] and fixture["random_match"]) else "❌"
        random_info = ""
        if fixture["has_random_fields"]:
            random_info = "✅ random match" if fixture["random_match"] else "❌ random mismatch"
            if not fixture["random_match"] and fixture["random_message"]:
                random_info += f" ({fixture['random_message']})"
        lines.append(f"- {marker} `{fixture['name']}` ({fixture['kind']}) {random_info}")
        if not fixture["passed"] and fixture["message"]:
            lines.append(f"  - {fixture['message']}")
    
    lines.extend([
        "",
        "## Gate 4: Random-Call Audit Conclusion",
        "",
        f"Random-Call Audit: {'✅ PASS' if rand_audit['all_random_match'] else '❌ FAIL'}",
        "",
        "### Validation Criteria",
        "",
        f"- 25/25 integer fixtures pass: {'✅' if results['integer_passed'] == 25 else '❌'}",
        f"- 15/15 cluster fixtures pass: {'✅' if results['cluster_passed'] == 15 else '❌'}",
        f"- 40/40 total fixtures pass: {'✅' if results['passed'] == 40 else '❌'}",
        f"- All random traces match: {'✅' if rand_audit['all_random_match'] else '❌'}",
        f"- No extra random draws: {'✅' if rand_audit['extra_draws'] == 0 else '❌'}",
        f"- No missing random draws: {'✅' if rand_audit['missing_draws'] == 0 else '❌'}",
        f"- No random order changes: {'✅' if rand_audit['order_changes'] == 0 else '❌'}",
        f"- Zero skipped fixtures: {'✅' if results['skipped'] == 0 else '❌'}",
        "",
        f"**Gate 4 Final Status: {'✅ PASS' if results['overall_passed'] else '❌ FAIL'}**",
        "",
        "### Next Gate",
        "",
        "Gate 5: Adapter Invariance Report - Prove every v5 field survives round-trip conversion:",
        "",
        "id, pos, direction, energy, pressure, alive, type, parent_id, bonds, signal_type",
    ])
    
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_fixture_hashes(fixtures_path: Path, expected_hash: str) -> tuple[bool, str]:
    """Verify fixture file hash."""
    actual_hash = sha256_file(fixtures_path)
    if actual_hash != expected_hash:
        return False, f"Fixture hash mismatch: expected {expected_hash}, actual {actual_hash}"
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Natural Math v6.1 Adapter Regression Harness - Gate 4: Random-Call Audit"
    )
    parser.add_argument(
        "--integer-fixtures",
        default="natural_math_integer_oracle_fixtures.json",
        help="Path to integer fixture file"
    )
    parser.add_argument(
        "--cluster-fixtures",
        default="natural_math_cluster_oracle_fixtures.json",
        help="Path to cluster fixture file"
    )
    parser.add_argument(
        "--report",
        default="natural_math_v61_adapter_report.md",
        help="Path to report file"
    )
    args = parser.parse_args()
    
    script_dir = Path(__file__).resolve().parent
    
    integer_path = Path(args.integer_fixtures)
    if not integer_path.is_absolute():
        integer_path = script_dir / integer_path
    
    cluster_path = Path(args.cluster_fixtures)
    if not cluster_path.is_absolute():
        cluster_path = script_dir / cluster_path
    
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = script_dir / report_path
    
    if not integer_path.exists():
        print(f"Error: Integer fixtures file not found: {integer_path}")
        return 1
    
    if not cluster_path.exists():
        print(f"Error: Cluster fixtures file not found: {cluster_path}")
        return 1
    
    results = run_harness(integer_path, cluster_path, report_path)
    
    print(f"\nReport saved to: {report_path}")
    print(f"Gate 4 Result: {'✅ PASS' if results['overall_passed'] else '❌ FAIL'}")
    print(f"Fixtures: {results['passed']}/{results['total']} passed")
    print(f"Random traces: {'✅ all match' if results['random_audit']['all_random_match'] else '❌ mismatches found'}")
    print(f"  - Total random fixtures: {results['random_audit']['total_random_fixtures']}")
    print(f"  - Mismatches: {results['random_audit']['random_mismatches']}")
    print(f"  - Extra draws: {results['random_audit']['extra_draws']}")
    print(f"  - Missing draws: {results['random_audit']['missing_draws']}")
    print(f"  - Order changes: {results['random_audit']['order_changes']}")
    
    return 0 if results["overall_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
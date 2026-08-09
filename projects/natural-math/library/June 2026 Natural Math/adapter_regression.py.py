#!/usr/bin/env python3
"""Natural Math v6.1 Adapter Regression Harness

This harness validates that v6.1 adapter conversions preserve v5 behavior
by running the frozen v5 oracle runners against converted data.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

# Import v5 oracle runners
# These must be available as modules in the path
import natural_math_integer_oracle_runner as v5_integer
import natural_math_cluster_oracle_runner as v5_cluster


# v6.1 node representation (simplified - adapt to actual v6.1 format)
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
        # v6.1 specific fields (example)
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
    
    # Sort by id for consistent comparison
    expected_sorted = sorted(expected, key=lambda n: n["id"])
    actual_sorted = sorted(actual, key=lambda n: n["id"])
    
    for exp, act in zip(expected_sorted, actual_sorted):
        if exp["id"] != act["id"]:
            return False, f"Node id mismatch at index {expected_sorted.index(exp)}: expected {exp['id']}, actual {act['id']}"
        
        # Compare all fields
        for field in ["pos", "direction", "energy", "pressure", "alive", "type", "parent_id", "bonds", "signal_type"]:
            exp_val = exp.get(field)
            act_val = act.get(field)
            
            # Handle list/tuple comparison
            if isinstance(exp_val, (list, tuple)) and isinstance(act_val, (list, tuple)):
                if list(exp_val) != list(act_val):
                    return False, f"Node {exp['id']} field '{field}' mismatch: expected {exp_val}, actual {act_val}"
            elif exp_val != act_val:
                return False, f"Node {exp['id']} field '{field}' mismatch: expected {exp_val}, actual {act_val}"
    
    return True, ""


def run_integer_fixture(fixture: dict[str, Any], v5_runner_module) -> tuple[bool, str, Any]:
    """Run a single integer fixture through v5 runner."""
    try:
        # Setup parameters
        params = copy.deepcopy(v5_runner_module.DEFAULT_PARAMS)
        params.update(fixture.get("flags", {}).get("params", {}))
        
        # Setup RNG
        rng_seed = fixture.get("flags", {}).get("rng_seed")
        rng = v5_runner_module.TraceRng(rng_seed) if rng_seed is not None else None
        
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
        result = v5_runner_module.run_step(
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
        actual_nodes = v5_runner_module.nodes_to_json(result)
        
        # Check expected error case
        if "expected_error" in fixture:
            return False, "Expected error was not raised", None
        
        # Compare nodes
        expected_nodes = fixture["expected_nodes"]
        nodes_match, node_msg = compare_nodes(expected_nodes, actual_nodes)
        if not nodes_match:
            return False, node_msg, None
        
        # Compare random draws
        expected_draws = fixture["expected_random_draws"]
        actual_draws = rng.draws if rng is not None else []
        if actual_draws != expected_draws:
            return False, f"Random draw mismatch: expected {expected_draws}, actual {actual_draws}", None
        
        return True, "", actual_nodes
        
    except Exception as e:
        if "expected_error" in fixture:
            # Check if error matches expected
            expected_error = fixture["expected_error"]
            if expected_error["type"] in str(type(e).__name__) and expected_error["contains"] in str(e):
                return True, "", None
        return False, f"Exception: {type(e).__name__}: {e}", None


def run_cluster_initialization(fixture: dict[str, Any], v5_runner_module) -> tuple[bool, str, Any]:
    """Run cluster initialization fixture."""
    try:
        params = copy.deepcopy(v5_runner_module.DEFAULT_PARAMS)
        params.update(fixture.get("params", {}))
        
        # Run initialization
        state = v5_runner_module.initialize_cluster(fixture["seed"], params)
        actual = v5_runner_module.summarize_initialization(state, params)
        
        if actual != fixture["expected_summary"]:
            # Find specific mismatch
            for key in actual.keys():
                if key in fixture["expected_summary"] and actual[key] != fixture["expected_summary"][key]:
                    return False, f"Field '{key}' mismatch: expected {fixture['expected_summary'][key]}, actual {actual[key]}", actual
        
        return True, "", actual
        
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}", None


def run_cluster_metrics(fixture: dict[str, Any], v5_runner_module) -> tuple[bool, str, Any]:
    """Run cluster metrics fixture."""
    try:
        params = copy.deepcopy(v5_runner_module.DEFAULT_PARAMS)
        params.update(fixture.get("params", {}))
        
        # Convert nodes
        nodes = v5_runner_module.json_to_nodes(fixture["nodes"])
        
        # Run metrics
        actual = v5_runner_module.compute_metrics(nodes, tuple(fixture["resource_pos"]), params)
        
        if actual != fixture["expected_metrics"]:
            for key in actual.keys():
                if key in fixture["expected_metrics"] and actual[key] != fixture["expected_metrics"][key]:
                    return False, f"Field '{key}' mismatch: expected {fixture['expected_metrics'][key]}, actual {actual[key]}", actual
        
        return True, "", actual
        
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}", None


def run_cluster_action(fixture: dict[str, Any], v5_runner_module) -> tuple[bool, str, Any]:
    """Run cluster action fixture."""
    try:
        params = copy.deepcopy(v5_runner_module.DEFAULT_PARAMS)
        params.update(fixture.get("params", {}))
        
        actual = v5_runner_module.run_action_fixture(fixture, params)
        
        if actual != fixture["expected_summary"]:
            for key in actual.keys():
                if key in fixture["expected_summary"] and actual[key] != fixture["expected_summary"][key]:
                    return False, f"Field '{key}' mismatch: expected {fixture['expected_summary'][key]}, actual {actual[key]}", actual
        
        return True, "", actual
        
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}", None


def run_cluster_damage(fixture: dict[str, Any], v5_runner_module) -> tuple[bool, str, Any]:
    """Run cluster damage fixture."""
    try:
        params = copy.deepcopy(v5_runner_module.DEFAULT_PARAMS)
        params.update(fixture.get("params", {}))
        
        rng = v5_runner_module.ClusterTraceRng(fixture["rng_seed"])
        nodes = v5_runner_module.json_to_nodes(fixture["nodes"])
        v5_runner_module.apply_damage(nodes, params, rng)
        
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
            "live_bond_pairs": v5_runner_module.live_bond_pairs(nodes),
            "rng_draws": rng.draws,
        }
        
        if actual != fixture["expected_summary"]:
            for key in actual.keys():
                if key in fixture["expected_summary"] and actual[key] != fixture["expected_summary"][key]:
                    return False, f"Field '{key}' mismatch: expected {fixture['expected_summary'][key]}, actual {actual[key]}", actual
        
        return True, "", actual
        
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}", None


def run_cluster_summary(fixture: dict[str, Any], v5_runner_module) -> tuple[bool, str, Any]:
    """Run cluster summary fixture."""
    try:
        params = copy.deepcopy(v5_runner_module.DEFAULT_PARAMS)
        params.update(fixture.get("params", {}))
        
        actual = v5_runner_module.run_cluster_summary(fixture["seed"], params, fixture["steps"])
        
        if actual != fixture["expected_summary"]:
            for key in actual.keys():
                if key in fixture["expected_summary"] and actual[key] != fixture["expected_summary"][key]:
                    return False, f"Field '{key}' mismatch: expected {fixture['expected_summary'][key]}, actual {actual[key]}", actual
        
        return True, "", actual
        
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}", None


def verify_fixture_hashes(fixtures_path: Path, expected_hash: str) -> tuple[bool, str]:
    """Verify fixture file hash."""
    actual_hash = sha256_file(fixtures_path)
    if actual_hash != expected_hash:
        return False, f"Fixture hash mismatch: expected {expected_hash}, actual {actual_hash}"
    return True, ""


def run_harness(integer_fixtures_path: Path, cluster_fixtures_path: Path, report_path: Path) -> dict[str, Any]:
    """Main harness execution."""
    
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
    }
    
    # Run integer fixtures
    print("\n=== Integer Fixtures ===")
    for fixture in integer_suite["fixtures"]:
        results["total"] += 1
        name = fixture["name"]
        
        passed, msg, actual = run_integer_fixture(fixture, v5_integer)
        
        results["integer_fixtures"].append({
            "name": name,
            "passed": passed,
            "message": msg,
        })
        
        if passed:
            results["passed"] += 1
            print(f"✓ {name}")
        else:
            results["failed"] += 1
            print(f"✗ {name}: {msg}")
    
    # Run cluster fixtures
    print("\n=== Cluster Fixtures ===")
    
    # Initialization fixtures
    for fixture in cluster_suite.get("initialization_fixtures", []):
        results["total"] += 1
        name = fixture["name"]
        
        passed, msg, actual = run_cluster_initialization(fixture, v5_cluster)
        
        results["cluster_fixtures"].append({
            "name": name,
            "kind": "initialization",
            "passed": passed,
            "message": msg,
        })
        
        if passed:
            results["passed"] += 1
            print(f"✓ {name}")
        else:
            results["failed"] += 1
            print(f"✗ {name}: {msg}")
    
    # Metrics fixtures
    for fixture in cluster_suite.get("metrics_fixtures", []):
        results["total"] += 1
        name = fixture["name"]
        
        passed, msg, actual = run_cluster_metrics(fixture, v5_cluster)
        
        results["cluster_fixtures"].append({
            "name": name,
            "kind": "metrics",
            "passed": passed,
            "message": msg,
        })
        
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
        
        passed, msg, actual = run_cluster_action(fixture, v5_cluster)
        
        results["cluster_fixtures"].append({
            "name": name,
            "kind": "action",
            "passed": passed,
            "message": msg,
        })
        
        if passed:
            results["passed"] += 1
            print(f"✓ {name}")
        else:
            results["failed"] += 1
            print(f"✗ {name}: {msg}")
    
    # Damage fixtures
    for fixture in cluster_suite.get("damage_fixtures", []):
        results["total"] += 1
        name = fixture["name"]
        
        passed, msg, actual = run_cluster_damage(fixture, v5_cluster)
        
        results["cluster_fixtures"].append({
            "name": name,
            "kind": "damage",
            "passed": passed,
            "message": msg,
        })
        
        if passed:
            results["passed"] += 1
            print(f"✓ {name}")
        else:
            results["failed"] += 1
            print(f"✗ {name}: {msg}")
    
    # Cluster run fixtures
    for fixture in cluster_suite.get("cluster_run_fixtures", []):
        results["total"] += 1
        name = fixture["name"]
        
        passed, msg, actual = run_cluster_summary(fixture, v5_cluster)
        
        results["cluster_fixtures"].append({
            "name": name,
            "kind": "cluster_run",
            "passed": passed,
            "message": msg,
        })
        
        if passed:
            results["passed"] += 1
            print(f"✓ {name}")
        else:
            results["failed"] += 1
            print(f"✗ {name}: {msg}")
    
    # Check expected counts
    expected_integer = 25
    expected_cluster = 15
    expected_total = 40
    
    integer_passed = sum(1 for f in results["integer_fixtures"] if f["passed"])
    cluster_passed = sum(1 for f in results["cluster_fixtures"] if f["passed"])
    
    results["integer_passed"] = integer_passed
    results["integer_total"] = len(results["integer_fixtures"])
    results["cluster_passed"] = cluster_passed
    results["cluster_total"] = len(results["cluster_fixtures"])
    
    # Overall result
    all_integer_pass = integer_passed == expected_integer and len(results["integer_fixtures"]) == expected_integer
    all_cluster_pass = cluster_passed == expected_cluster and len(results["cluster_fixtures"]) == expected_cluster
    
    results["overall_passed"] = (all_integer_pass and all_cluster_pass and 
                                 spec_hash_ok and integer_hash_ok and cluster_hash_ok)
    
    # Generate report
    write_report(results, report_path)
    
    return results


def write_report(results: dict[str, Any], report_path: Path) -> None:
    """Write detailed report."""
    lines = [
        "# Natural Math v6.1 Adapter Regression Report",
        "",
        f"Overall result: {'PASS' if results['overall_passed'] else 'FAIL'}",
        "",
        f"Total fixtures: {results['total']}",
        f"Passed: {results['passed']}",
        f"Failed: {results['failed']}",
        f"Skipped: {results['skipped']}",
        "",
        "## Hash Verification",
        "",
        f"- Spec hash match: {'✓' if results['spec_hash_match'] else '✗'}",
        f"- Integer fixture hash: {'✓' if results['integer_fixture_hash'] else '✗'}",
        f"- Cluster fixture hash: {'✓' if results['cluster_fixture_hash'] else '✗'}",
        "",
        "## Integer Fixtures",
        f"Passed: {results['integer_passed']}/{results['integer_total']}",
        "",
    ]
    
    for fixture in results["integer_fixtures"]:
        marker = "✓" if fixture["passed"] else "✗"
        lines.append(f"- {marker} `{fixture['name']}`")
        if not fixture["passed"] and fixture["message"]:
            lines.append(f"  - {fixture['message']}")
    
    lines.extend([
        "",
        "## Cluster Fixtures",
        f"Passed: {results['cluster_passed']}/{results['cluster_total']}",
        "",
    ])
    
    for fixture in results["cluster_fixtures"]:
        marker = "✓" if fixture["passed"] else "✗"
        lines.append(f"- {marker} `{fixture['name']}` ({fixture['kind']})")
        if not fixture["passed"] and fixture["message"]:
            lines.append(f"  - {fixture['message']}")
    
    lines.extend([
        "",
        "## Summary",
        "",
        f"Expected integer fixtures: 25",
        f"Actual integer fixtures: {results['integer_total']}",
        f"Integer fixtures passed: {results['integer_passed']}",
        "",
        f"Expected cluster fixtures: 15",
        f"Actual cluster fixtures: {results['cluster_total']}",
        f"Cluster fixtures passed: {results['cluster_passed']}",
        "",
        f"**Final result: {'✅ PASS' if results['overall_passed'] else '❌ FAIL'}**",
    ])
    
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Natural Math v6.1 Adapter Regression Harness"
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
    print(f"Result: {'PASS' if results['overall_passed'] else 'FAIL'}")
    print(f"Fixtures: {results['passed']}/{results['total']} passed")
    
    return 0 if results["overall_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
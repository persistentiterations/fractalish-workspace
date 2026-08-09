#!/usr/bin/env python3
"""Deterministic constructed-fixture common-mode evidence trial."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import hashlib
import json


HERE = Path(__file__).resolve().parent
OUT = HERE / "results"


@dataclass(frozen=True)
class Witness:
    witness_id: str
    relay_id: str
    provenance_root: str
    dependency_path: str
    value: str
    root_status: str = "VALID"


@dataclass(frozen=True)
class Case:
    case_id: str
    witnesses: tuple[Witness, ...]
    expected: str
    expected_total_roots: int
    expected_supporting_roots: int
    expected_opposing_roots: int
    expected_conflicted_roots: int = 0


def w(witness, relay, provenance, dependency, value="YES", status="VALID"):
    return Witness(witness, relay, provenance, dependency, value, status)


CASES = (
    Case("three_relays_one_root", (
        w("W1", "R1", "ROOT_A", "CAUSE_A"),
        w("W2", "R2", "ROOT_A", "CAUSE_A"),
        w("W3", "R3", "ROOT_A", "CAUSE_A"),
    ), "HOLD", 1, 1, 0),
    Case("two_sensors_shared_clock", (
        w("SENSOR_1", "BUS_1", "SENSOR_1", "CLOCK_X"),
        w("SENSOR_2", "BUS_2", "SENSOR_2", "CLOCK_X"),
    ), "HOLD", 1, 1, 0),
    Case("two_sensors_shared_calibration", (
        w("SENSOR_1", "BUS_1", "SENSOR_1", "CALIBRATION_X"),
        w("SENSOR_2", "BUS_2", "SENSOR_2", "CALIBRATION_X"),
    ), "HOLD", 1, 1, 0),
    Case("two_sensors_shared_owner", (
        w("SENSOR_1", "BUS_1", "SENSOR_1", "OWNER_FEED_X"),
        w("SENSOR_2", "BUS_2", "SENSOR_2", "OWNER_FEED_X"),
    ), "HOLD", 1, 1, 0),
    Case("two_models_shared_training_dataset", (
        w("MODEL_1", "PATH_1", "MODEL_1", "DATASET_X"),
        w("MODEL_2", "PATH_2", "MODEL_2", "DATASET_X"),
    ), "HOLD", 1, 1, 0),
    Case("agents_different_words_same_document", (
        w("AGENT_1", "PATH_1", "DOC_X", "DOC_X", value="YES"),
        w("AGENT_2", "PATH_2", "DOC_X", "DOC_X", value="YES"),
    ), "HOLD", 1, 1, 0),
    Case("paths_converge_on_dependency", (
        w("W1", "LEFT_PATH", "ROOT_LEFT", "SERVICE_A>SHARED_DB"),
        w("W2", "RIGHT_PATH", "ROOT_RIGHT", "SERVICE_B>SHARED_DB"),
    ), "HOLD", 1, 1, 0),
    Case("genuine_independent_pair", (
        w("W1", "R1", "ROOT_A", "CAUSE_A"),
        w("W2", "R2", "ROOT_B", "CAUSE_B"),
    ), "ESTABLISH", 2, 2, 0),
    Case("duplicate_witness_id_same_report", (
        w("W1", "R1", "ROOT_A", "CAUSE_A"),
        w("W1", "R1", "ROOT_A", "CAUSE_A"),
    ), "HOLD", 1, 1, 0),
    Case("duplicate_relay_id_different_roots", (
        w("W1", "R_SHARED", "ROOT_A", "CAUSE_A"),
        w("W2", "R_SHARED", "ROOT_B", "CAUSE_B"),
    ), "ESTABLISH", 2, 2, 0),
    Case("same_root_opposed_values", (
        w("W1", "R1", "ROOT_A", "CAUSE_A", value="YES"),
        w("W2", "R2", "ROOT_A", "CAUSE_A", value="NO"),
    ), "HOLD", 1, 0, 0, 1),
    Case("known_provenance_unknown_dependency", (
        w("W1", "R1", "ROOT_A", ""),
    ), "UNRESOLVED", 0, 0, 0),
    Case("missing_provenance", (
        w("W1", "R1", "", ""),
        w("W2", "R2", "", ""),
    ), "UNRESOLVED", 0, 0, 0),
    Case("contradicted_root_plus_opposed_valid_roots", (
        w("W1", "R1", "ROOT_A", "CAUSE_A", value="YES", status="CONTRADICTED"),
        w("W2", "R2", "ROOT_B", "CAUSE_B", value="YES"),
        w("W3", "R3", "ROOT_C", "CAUSE_C", value="NO"),
    ), "HOLD", 2, 1, 1),
    Case("dependency_cycle", (
        w("W1", "R1", "ROOT_A", "SERVICE_A>SERVICE_B>SERVICE_A"),
        w("W2", "R2", "ROOT_B", "CAUSE_B"),
    ), "UNRESOLVED", 0, 0, 0),
    Case("copies_plus_independent", (
        w("W1", "R1", "ROOT_A", "CAUSE_A"),
        w("W2", "R2", "ROOT_A", "CAUSE_A"),
        w("W3", "R3", "ROOT_A", "CAUSE_A"),
        w("W4", "R4", "ROOT_B", "CAUSE_B"),
    ), "ESTABLISH", 2, 2, 0),
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def ultimate_dependency(path: str):
    if not path:
        return None
    parts = path.split(">")
    if any(not part for part in parts) or len(parts) != len(set(parts)):
        return None
    return parts[-1]


def group_key(item: Witness, policy: str, index: int):
    if policy == "MESSAGE_COUNT":
        return f"MESSAGE_{index}"
    if policy == "RELAY_ID_COUNT":
        return item.relay_id
    if policy == "DECLARED_PROVENANCE_ROOT":
        return item.provenance_root or None
    return ultimate_dependency(item.dependency_path)


def decide(case: Case, policy: str):
    # Exact duplicate witness records are one observation. A duplicated ID with
    # different content is unresolved identity, not two votes.
    by_witness = {}
    for item in case.witnesses:
        prior = by_witness.get(item.witness_id)
        if prior is not None and prior != item:
            return "UNRESOLVED", 0, 0, 0, 0
        by_witness[item.witness_id] = item
    witnesses = list(by_witness.values())

    if policy == "CAUSAL_DEPENDENCY_ROOT":
        invalid_roots = {
            ultimate_dependency(item.dependency_path)
            for item in witnesses if item.root_status == "CONTRADICTED"
        }
    else:
        invalid_roots = set()

    groups = {}
    for index, item in enumerate(witnesses):
        if item.root_status != "VALID":
            continue
        key = group_key(item, policy, index)
        if key is None:
            return "UNRESOLVED", 0, 0, 0, 0
        if policy == "CAUSAL_DEPENDENCY_ROOT" and key in invalid_roots:
            continue
        groups.setdefault(key, set()).add(item.value)

    total = len(groups)
    conflicted = sum(1 for values in groups.values() if values == {"YES", "NO"})
    supporting = sum(1 for values in groups.values() if values == {"YES"})
    opposing = sum(1 for values in groups.values() if values == {"NO"})
    if conflicted or opposing:
        decision = "HOLD"
    elif supporting >= 2:
        decision = "ESTABLISH"
    else:
        decision = "HOLD"
    return decision, total, supporting, opposing, conflicted


def execute():
    policies = (
        "MESSAGE_COUNT", "RELAY_ID_COUNT", "DECLARED_PROVENANCE_ROOT",
        "CAUSAL_DEPENDENCY_ROOT",
    )
    rows = []
    for policy in policies:
        head = "0" * 64
        for tick, case in enumerate(CASES, 1):
            decision, total, supporting, opposing, conflicted = decide(case, policy)
            counts_pass = (
                total == case.expected_total_roots
                and supporting == case.expected_supporting_roots
                and opposing == case.expected_opposing_roots
                and conflicted == case.expected_conflicted_roots
            )
            body = {
                "tick": tick,
                "case": case.case_id,
                "policy": policy,
                "decision": decision,
                "expected": case.expected,
                "total_independent_roots": total,
                "expected_total_roots": case.expected_total_roots,
                "supporting_roots": supporting,
                "expected_supporting_roots": case.expected_supporting_roots,
                "opposing_roots": opposing,
                "expected_opposing_roots": case.expected_opposing_roots,
                "conflicted_roots": conflicted,
                "expected_conflicted_roots": case.expected_conflicted_roots,
                "decision_pass": decision == case.expected,
                "root_counts_pass": counts_pass,
                "previous_hash": head,
            }
            head = digest(body)
            body["receipt_hash"] = head
            rows.append(body)
    summaries = []
    for policy in policies:
        selected = [x for x in rows if x["policy"] == policy]
        summaries.append({
            "policy": policy,
            "decision_correct": sum(int(x["decision_pass"]) for x in selected),
            "root_counts_correct": sum(int(x["root_counts_pass"]) for x in selected),
            "total": len(selected),
            "false_establishments": sum(int(x["decision"] == "ESTABLISH" and x["expected"] != "ESTABLISH") for x in selected),
            "missed_establishments": sum(int(x["decision"] != "ESTABLISH" and x["expected"] == "ESTABLISH") for x in selected),
            "receipt_head": selected[-1]["receipt_hash"],
        })
    return summaries, rows


def assert_causal_acceptance(summaries, rows):
    causal = next(x for x in summaries if x["policy"] == "CAUSAL_DEPENDENCY_ROOT")
    if causal["decision_correct"] != causal["total"]:
        raise AssertionError("causal dependency policy decision failure")
    if causal["root_counts_correct"] != causal["total"]:
        raise AssertionError("causal dependency policy root-count failure")
    if causal["false_establishments"] or causal["missed_establishments"]:
        raise AssertionError("causal dependency policy establishment failure")
    causal_rows = [x for x in rows if x["policy"] == "CAUSAL_DEPENDENCY_ROOT"]
    if not all(x["decision_pass"] and x["root_counts_pass"] for x in causal_rows):
        raise AssertionError("causal dependency case assertion failure")


def write_outputs(summaries, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in (("summary.csv", summaries), ("case_results.csv", rows)):
        with (OUT / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    report = {
        "trial": "common-mode-evidence-constructed-fixtures",
        "case_count": len(CASES),
        "summaries": summaries,
        "replay_hash": digest((summaries, rows)),
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main():
    first = execute()
    if first != execute():
        raise SystemExit("deterministic replay failed")
    try:
        assert_causal_acceptance(*first)
    except AssertionError as error:
        raise SystemExit(str(error)) from error
    write_outputs(*first)
    for summary in first[0]:
        print(summary)
    print("causal_acceptance_pass=true")
    print("replay_pass=true")
    print("replay_hash=" + digest(first))


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Natural Math exploratory v0.25
Can the burden of proof for a relationship be learned locally?

This trial deliberately compares:
  1. fixed confirmation thresholds,
  2. a scalar adaptive "burden of proof", and
  3. relationship-specific historical reliability.

The purpose is falsification, not promotion into the Natural Math kernel.
No randomness. Standard library only.
"""

from collections import defaultdict
import statistics, csv, json, hashlib
from pathlib import Path

OUT = Path("natural_math_v025_outputs")
OUT.mkdir(exist_ok=True)

def sha16(x):
    return hashlib.sha256(
        json.dumps(x, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]

def run(policy="fixed3", cycles=5, segment=90, n_nodes=18,
        variant=0, partial_mod=5,
        distractor_schedule=(1,2,3,2,1),
        failure_trigger=3):

    total = cycles * 5 * segment
    modulus = (29,31,37)[variant % 3]

    def where(t):
        cycle = t // (5 * segment)
        slot = (t % (5 * segment)) // segment
        return cycle, ("A","B","C","B_PARTIAL","A")[slot]

    def base(label, i, t):
        k = {"A":3,"B":5,"C":7}[label]
        q = {"A":11,"B":13,"C":17}[label]
        return (
            i*q
            + (t // (2 + (i+k) % 5))*k
            + (t // (23+k))*((i+k) % 7 + 1)
            + (t // 71)**2
        ) % modulus

    def true_label(t):
        _, p = where(t)
        return "B" if p == "B_PARTIAL" else p

    def actual(i,t):
        cyc,p = where(t)
        label = "B" if p == "B_PARTIAL" else p
        v = base(label,i,t)
        if p == "B_PARTIAL" and ((t + 2*i + variant) % partial_mod == 0):
            v = (v + 1 + (i % 2)) % modulus
        return v

    def predict(label,i,t):
        if label in ("A","B","C"):
            return base(label,i,t)
        # D is not causal. It shadows observations for short deterministic runs.
        cyc,_ = where(t)
        streak = distractor_schedule[cyc % len(distractor_schedule)]
        v = actual(i,t)
        if ((t+i+variant) % (streak+1)) == streak:
            return (v+1) % modulus
        return v

    nodes = {}
    for i in range(n_nodes):
        nodes[i] = {
            "active":"A",
            "dormant":set(("B","C","D")),
            "failure_streak":0,
            "probe":defaultdict(int),

            # scalar burden candidate
            "burden":{x:2 for x in ("A","B","C","D")},
            "probation":None,

            # relationship history candidate
            "correct":{x:0 for x in ("A","B","C","D")},
            "wrong":{x:0 for x in ("A","B","C","D")},
        }

    false_D = [0]*cycles
    wrong_authority = [0]*cycles
    final_correct = [0]*cycles
    switches = [0]*cycles
    receipts = []

    for t in range(total):
        cyc,_ = where(t)

        for i,n in nodes.items():
            active = n["active"]
            ok = predict(active,i,t) == actual(i,t)

            if ok:
                n["correct"][active] += 1
            else:
                n["wrong"][active] += 1

            if active != true_label(t):
                wrong_authority[cyc] += 1

            # Scalar adaptive policy learns from failed reactivations.
            if n["probation"] is not None:
                p = n["probation"]
                if ok:
                    p["post"] += 1
                    if p["post"] >= p["target"]:
                        n["probation"] = None
                else:
                    if policy == "scalar_adaptive":
                        observed_run = p["evidence"] + p["post"]
                        n["burden"][p["label"]] = min(
                            8,
                            max(n["burden"][p["label"]], observed_run + 1)
                        )
                    n["probation"] = None

            n["failure_streak"] = 0 if ok else n["failure_streak"] + 1

            if n["failure_streak"] < failure_trigger:
                continue

            viable = []
            for label in sorted(n["dormant"]):
                match = predict(label,i,t) == actual(i,t)
                n["probe"][label] = n["probe"][label] + 1 if match else 0

                if policy.startswith("fixed"):
                    needed = int(policy[-1])
                    if n["probe"][label] >= needed:
                        viable.append(label)

                elif policy == "scalar_adaptive":
                    if n["probe"][label] >= n["burden"][label]:
                        viable.append(label)

                elif policy == "history_weighted":
                    # Minimal current gate: two present local confirmations.
                    # Authority among viable relationships is then determined by
                    # that relationship's own accumulated local consequences.
                    if n["probe"][label] >= 2:
                        viable.append(label)

            if not viable:
                continue

            if policy == "history_weighted":
                # No global accuracy. Each relationship carries only its own
                # correct/wrong active receipts. Present evidence still matters.
                def score(label):
                    hist = n["correct"][label] - n["wrong"][label]
                    return (
                        hist + n["probe"][label],
                        n["probe"][label],
                        -n["wrong"][label],
                        -ord(label)
                    )
                best = max(viable, key=score)
            else:
                def score(label):
                    needed = (
                        int(policy[-1]) if policy.startswith("fixed")
                        else n["burden"][label]
                    )
                    return (
                        n["probe"][label] - needed,
                        n["probe"][label],
                        -ord(label)
                    )
                best = max(viable, key=score)

            old = active
            evidence = n["probe"][best]
            n["dormant"].add(old)
            n["dormant"].remove(best)
            n["active"] = best
            n["failure_streak"] = 0
            n["probe"].clear()
            switches[cyc] += 1

            if policy == "scalar_adaptive":
                n["probation"] = {
                    "label":best,
                    "target":n["burden"][best],
                    "post":0,
                    "evidence":evidence,
                }

            if best == "D":
                false_D[cyc] += 1

            receipts.append({
                "t":t, "cycle":cyc, "node":i,
                "event":"SWITCH", "from":old, "to":best,
                "true":true_label(t)
            })

        if (t+1) % (5*segment) == 0:
            final_correct[cyc] = sum(
                n["active"] == "A" for n in nodes.values()
            )

    result = {
        "policy":policy,
        "variant":variant,
        "partial_mod":partial_mod,
        "false_D_total":sum(false_D),
        "false_D_by_cycle":";".join(map(str,false_D)),
        "wrong_authority_total":sum(wrong_authority),
        "wrong_authority_by_cycle":";".join(map(str,wrong_authority)),
        "final_correct_by_cycle":";".join(map(str,final_correct)),
        "switches_by_cycle":";".join(map(str,switches)),
        "final_correct_last":final_correct[-1],
        "mean_D_burden":round(statistics.mean(
            n["burden"]["D"] for n in nodes.values()
        ),3),
        "mean_B_burden":round(statistics.mean(
            n["burden"]["B"] for n in nodes.values()
        ),3),
    }
    result["hash"] = sha16({"result":result,"receipts":receipts})
    return result,receipts

def main():
    policies = ("fixed2","fixed3","fixed4",
                "scalar_adaptive","history_weighted")
    rows=[]
    for variant in range(3):
        for partial_mod in (4,5,6):
            for policy in policies:
                result,_ = run(
                    policy=policy,
                    variant=variant,
                    partial_mod=partial_mod,
                )
                rows.append(result)

    with (OUT/"v0_25_results.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    for policy in policies:
        subset=[r for r in rows if r["policy"]==policy]
        print(policy)
        print("  cases:",len(subset))
        print("  perfect final:",sum(r["final_correct_last"]==18 for r in subset))
        print("  total false D:",sum(r["false_D_total"] for r in subset))
        print("  mean wrong authority:",round(statistics.mean(
            r["wrong_authority_total"] for r in subset
        ),2))

if __name__=="__main__":
    main()

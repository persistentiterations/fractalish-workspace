#!/usr/bin/env python3
"""
Natural Math exploratory v0.26
Conditional relationship history

Question:
Can a relationship accumulate separate reliability histories under different
locally observable boundary conditions, without being told what those
conditions "mean"?

Policies compared:
  fixed3
  unconditional_history
  conditional_history

No randomness. Standard library only.
Exploratory harness, not canonical Natural Math.
"""

from collections import defaultdict
import csv, json, hashlib, statistics
from pathlib import Path

OUT = Path("natural_math_v026_outputs")
OUT.mkdir(exist_ok=True)

def sha16(x):
    return hashlib.sha256(
        json.dumps(x, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]

def run(policy="conditional_history",
        cycles=6,
        segment=80,
        n_nodes=18,
        variant=0,
        partial_mod=5,
        failure_trigger=3,
        signature_granularity=3):

    phases = ("A","B","C","B_PARTIAL","A")
    total = cycles * len(phases) * segment
    mod = (29,31,37)[variant % 3]

    def phase_info(t):
        cyc = t // (len(phases)*segment)
        slot = (t % (len(phases)*segment)) // segment
        return cyc, phases[slot]

    def base(label, i, t):
        k = {"A":3,"B":5,"C":7}[label]
        q = {"A":11,"B":13,"C":17}[label]
        return (
            i*q
            + (t // (2 + (i+k) % 5))*k
            + (t // (19+k))*((i+k) % 7 + 1)
            + (t // 67)**2
        ) % mod

    def true_label(t):
        _, p = phase_info(t)
        return "B" if p == "B_PARTIAL" else p

    def local_condition(i,t):
        """
        A local, meaning-free signature. It is not the phase label.
        It uses only nearby/current observables:
          - parity/coarse bucket of two local source-like signals
          - reserve-like local cyclic variable
          - local change direction
        """
        s1 = base("A", i, t)
        s2 = base("B", i, t)
        prev = base("A", i, max(0,t-1))
        delta_sign = -1 if s1 < prev else 1 if s1 > prev else 0
        reserve_bucket = ((t + 2*i + variant) // 7) % signature_granularity
        return (
            s1 % signature_granularity,
            s2 % signature_granularity,
            reserve_bucket,
            delta_sign,
        )

    def actual(i,t):
        _, p = phase_info(t)
        label = "B" if p == "B_PARTIAL" else p
        v = base(label,i,t)
        if p == "B_PARTIAL" and ((t + 2*i + variant) % partial_mod == 0):
            v = (v + 1 + (i % 2)) % mod
        return v

    def predict(label,i,t):
        if label in ("A","B","C"):
            return base(label,i,t)
        # D = near-match distractor: imitates for deterministic short runs.
        cyc,_ = phase_info(t)
        streak = (1,2,3,2,1,3)[cyc % 6]
        v = actual(i,t)
        if ((t+i+variant) % (streak+1)) == streak:
            return (v+1) % mod
        return v

    nodes={}
    for i in range(n_nodes):
        nodes[i]={
            "active":"A",
            "dormant":set(("B","C","D")),
            "failure_streak":0,
            "probe":defaultdict(int),

            # unconditional history
            "good":defaultdict(int),
            "bad":defaultdict(int),

            # conditional history: key=(relationship, local signature)
            "cgood":defaultdict(int),
            "cbad":defaultdict(int),
        }

    false_D=[0]*cycles
    wrong_steps=[0]*cycles
    final_correct=[0]*cycles
    complete_cycles=[True]*cycles
    switches=[0]*cycles
    receipts=[]

    expected_transition_slots = [1,2,3,4]
    expected_seen = {cyc:{slot:0 for slot in expected_transition_slots}
                     for cyc in range(cycles)}

    for t in range(total):
        cyc,p = phase_info(t)
        slot = (t % (len(phases)*segment)) // segment

        for i,n in nodes.items():
            sig = local_condition(i,t)
            active = n["active"]
            ok = predict(active,i,t) == actual(i,t)

            if ok:
                n["good"][active] += 1
                n["cgood"][(active,sig)] += 1
            else:
                n["bad"][active] += 1
                n["cbad"][(active,sig)] += 1

            if active != true_label(t):
                wrong_steps[cyc] += 1

            n["failure_streak"] = 0 if ok else n["failure_streak"] + 1
            if n["failure_streak"] < failure_trigger:
                continue

            viable=[]
            for label in sorted(n["dormant"]):
                match = predict(label,i,t) == actual(i,t)
                n["probe"][label] = n["probe"][label] + 1 if match else 0
                if n["probe"][label] >= 2:
                    viable.append(label)

            if not viable:
                continue

            if policy == "fixed3":
                viable3=[x for x in viable if n["probe"][x] >= 3]
                if not viable3:
                    continue
                best=max(viable3, key=lambda x:(n["probe"][x], -ord(x)))

            elif policy == "unconditional_history":
                def score(label):
                    hist=n["good"][label]-n["bad"][label]
                    return (hist+n["probe"][label], n["probe"][label], -n["bad"][label], -ord(label))
                best=max(viable,key=score)

            elif policy == "conditional_history":
                def score(label):
                    cg=n["cgood"][(label,sig)]
                    cb=n["cbad"][(label,sig)]
                    local_hist=cg-cb
                    # Current evidence dominates stale history; conditional
                    # history only breaks ties / modulates authority locally.
                    return (
                        3*n["probe"][label] + local_hist,
                        n["probe"][label],
                        -cb,
                        -ord(label)
                    )
                best=max(viable,key=score)
            else:
                raise ValueError(policy)

            old=active
            n["dormant"].add(old)
            n["dormant"].remove(best)
            n["active"]=best
            n["failure_streak"]=0
            n["probe"].clear()
            switches[cyc]+=1

            if best=="D":
                false_D[cyc]+=1

            # Count whether nodes follow each required transition in that cycle.
            expected = {1:"B",2:"C",3:"B",4:"A"}.get(slot)
            if expected is not None and best == expected:
                expected_seen[cyc][slot] += 1

            receipts.append({
                "t":t,"cycle":cyc,"node":i,"sig":str(sig),
                "event":"SWITCH","from":old,"to":best,
                "true":true_label(t)
            })

        if (t+1) % (len(phases)*segment) == 0:
            final_correct[cyc]=sum(n["active"]=="A" for n in nodes.values())
            complete_cycles[cyc]=(
                false_D[cyc]==0
                and final_correct[cyc]==n_nodes
                and all(expected_seen[cyc][slot] >= n_nodes
                        for slot in expected_transition_slots)
            )

    result={
        "policy":policy,
        "variant":variant,
        "partial_mod":partial_mod,
        "signature_granularity":signature_granularity,
        "cycles":cycles,
        "complete_cycle_count":sum(complete_cycles),
        "complete_cycle_flags":";".join("1" if x else "0" for x in complete_cycles),
        "false_D_total":sum(false_D),
        "false_D_by_cycle":";".join(map(str,false_D)),
        "wrong_steps_total":sum(wrong_steps),
        "wrong_steps_by_cycle":";".join(map(str,wrong_steps)),
        "final_correct_by_cycle":";".join(map(str,final_correct)),
        "switches_by_cycle":";".join(map(str,switches)),
    }
    result["hash"]=sha16({"result":result,"receipts":receipts})
    return result,receipts

def main():
    policies=("fixed3","unconditional_history","conditional_history")
    rows=[]
    for variant in range(3):
        for partial_mod in (4,5,6):
            for granularity in (2,3,4):
                for policy in policies:
                    r,_=run(policy=policy,
                            variant=variant,
                            partial_mod=partial_mod,
                            signature_granularity=granularity)
                    rows.append(r)

    with (OUT/"v0_26_results.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    for policy in policies:
        sub=[r for r in rows if r["policy"]==policy]
        print(policy)
        print(" cases",len(sub))
        print(" all 6 cycles complete",
              sum(r["complete_cycle_count"]==6 for r in sub))
        print(" mean completed cycles",
              round(statistics.mean(r["complete_cycle_count"] for r in sub),3))
        print(" total false D",
              sum(r["false_D_total"] for r in sub))
        print(" mean wrong steps",
              round(statistics.mean(r["wrong_steps_total"] for r in sub),2))

if __name__=="__main__":
    main()

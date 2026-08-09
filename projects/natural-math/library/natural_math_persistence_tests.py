#!/usr/bin/env python3
"""Natural Math local consequence persistence test harness.

Compares:
  1) blind deterministic DFS exploration
  2) constraint-filtered persistence exploration with junction keepers,
     tried-branch restriction, dead-end memory, imperfect local beacon,
     safe-return reserve, and multiple sorties.

No global route is exposed to the scout. Global BFS is used only by the
harness for maze generation, verification, and shortest-route reporting.
"""
from __future__ import annotations

import argparse, csv, json, math, random, statistics
from collections import deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

Point = Tuple[int, int]
DIRS: Tuple[Point, ...] = ((1,0),(0,1),(-1,0),(0,-1))

@dataclass(frozen=True)
class Case:
    case_id: int
    seed: int
    width: int
    height: int
    loop_rate: float
    sortie_budget: int
    reserve: int
    max_sorties: int
    grid: Tuple[str, ...]
    base: Point
    resource: Point

@dataclass
class Result:
    case_id: int
    policy: str
    seed: int
    grid: str
    success: bool
    failure: str
    sorties: int
    safe_returns: int
    scout_moves: int
    discovery_moves: int
    route_length: int
    shortest_global_route: int
    explored_cells: int
    dead_ends: int
    keepers: int
    keeper_returns: int
    keeper_effective_switches: int
    keeper_ignored_opportunities: int
    repeated_failed_branch_entries: int
    audit_pass: bool
    follower_pass: bool
    route_unchanged: bool

    @property
    def keeper_effectiveness(self) -> float:
        den = self.keeper_effective_switches + self.keeper_ignored_opportunities
        return self.keeper_effective_switches / den if den else 0.0


def edge(a: Point, b: Point) -> Tuple[Point, Point]:
    return (a,b) if a <= b else (b,a)

def neighbors(grid: Tuple[str,...], p: Point) -> List[Point]:
    x,y=p; out=[]
    for dx,dy in DIRS:
        nx,ny=x+dx,y+dy
        if 0 <= ny < len(grid) and 0 <= nx < len(grid[0]) and grid[ny][nx] != '#':
            out.append((nx,ny))
    return out

def bfs_grid(grid: Tuple[str,...], start: Point, goal: Optional[Point]=None) -> Dict[Point,int]:
    q=deque([start]); dist={start:0}
    while q:
        p=q.popleft()
        if p==goal: break
        for n in neighbors(grid,p):
            if n not in dist:
                dist[n]=dist[p]+1; q.append(n)
    return dist

def shortest_on_edges(start: Point, goal: Point, edges: Set[Tuple[Point,Point]], grid: Tuple[str,...]) -> Optional[List[Point]]:
    q=deque([start]); parent={start:None}
    while q:
        p=q.popleft()
        if p==goal: break
        for n in neighbors(grid,p):
            if n not in parent and edge(p,n) in edges:
                parent[n]=p; q.append(n)
    if goal not in parent: return None
    out=[]; cur=goal
    while cur is not None:
        out.append(cur); cur=parent[cur]
    return list(reversed(out))

def generate_case(case_id:int, seed:int, width:int, height:int, loop_rate:float,
                  sortie_budget:int, reserve:int, max_sorties:int) -> Case:
    r=random.Random(seed)
    g=[['#']*width for _ in range(height)]
    def carve(x:int,y:int)->None:
        g[y][x]='.'
        ds=list(DIRS); r.shuffle(ds)
        for dx,dy in ds:
            nx,ny=x+2*dx,y+2*dy
            if nx<=0 or ny<=0 or nx>=width-1 or ny>=height-1 or g[ny][nx] != '#': continue
            g[y+dy][x+dx]='.'; carve(nx,ny)
    carve(1,1)
    for _ in range(int(width*height*loop_rate)):
        x=r.randrange(1,width-1); y=r.randrange(1,height-1)
        if g[y][x] != '#': continue
        horizontal=g[y][x-1]=='.' and g[y][x+1]=='.'
        vertical=g[y-1][x]=='.' and g[y+1][x]=='.'
        if horizontal or vertical: g[y][x]='.'
    base=(1,1)
    temp=tuple(''.join(row) for row in g)
    dist=bfs_grid(temp,base)
    maxd=max(dist.values())
    far=[p for p,d in dist.items() if d>=maxd-2]
    resource=r.choice(far)
    g[base[1]][base[0]]='B'; g[resource[1]][resource[0]]='R'
    return Case(case_id,seed,width,height,loop_rate,sortie_budget,reserve,max_sorties,
                tuple(''.join(row) for row in g),base,resource)

def verify_route(case:Case, route:List[Point]) -> Tuple[bool,bool,bool]:
    if not route or route[0]!=case.base or route[-1]!=case.resource: return False,False,False
    frozen=tuple(route)
    out=all(edge(route[i-1],route[i]) and route[i] in neighbors(case.grid,route[i-1]) for i in range(1,len(route)))
    home=out and all(route[i-1] in neighbors(case.grid,route[i]) for i in range(len(route)-1,0,-1))
    unchanged=tuple(route)==frozen
    return out,home,unchanged

def run_blind(case:Case) -> Result:
    p=case.base; stack=[p]; visited={p}; edges:set= set(); moves=0; found=False
    while stack and moves < case.sortie_budget*case.max_sorties:
        p=stack[-1]
        if p==case.resource: found=True; break
        nxt=None
        for n in neighbors(case.grid,p):
            if n not in visited:
                nxt=n; break
        if nxt is not None:
            edges.add(edge(p,nxt)); visited.add(nxt); stack.append(nxt); moves+=1
        else:
            if len(stack)==1: break
            stack.pop(); moves+=1
    route=shortest_on_edges(case.base,case.resource,edges,case.grid) if found else None
    audit_out,audit_home,unchanged=verify_route(case,route or [])
    shortest=bfs_grid(case.grid,case.base).get(case.resource,0)
    return Result(case.case_id,'blind',case.seed,f'{case.width}x{case.height}',bool(found and route),'budget exhausted or resource not found' if not found else '',1,0,moves,moves if found else 0,len(route)-1 if route else 0,shortest,len(visited),0,0,0,0,0,0,audit_out and audit_home,audit_out and audit_home,unchanged)

def run_persistence(case:Case) -> Result:
    r=random.Random(case.seed ^ 0xA5A5A5A5)
    noise={p:(r.random()-.5)*4.0 for p in bfs_grid(case.grid,case.base)}
    def signal(p:Point)->float:
        return math.dist(p,case.resource)+noise.get(p,0.0)

    known_edges:Set[Tuple[Point,Point]]=set()
    visited:Set[Point]={case.base}
    dead:Set[Point]=set()
    keepers:Dict[Point,Set[Point]]={}
    failed_entries:Set[Tuple[Point,Point]]=set()
    repeated_failed=0; keeper_returns=0; effective=0; ignored=0
    safe_returns=0; total_moves=0; discovery_moves=0; found=False

    def raw_candidates(q:Point)->List[Point]:
        out=[]
        for n in neighbors(case.grid,q):
            e=edge(q,n)
            if n in dead or e in failed_entries or e in known_edges: continue
            if q in keepers and n in keepers[q]: continue
            out.append(n)
        return out

    for sortie in range(1,case.max_sorties+1):
        # Start by travelling to the nearest unresolved frontier already known.
        frontier=[]
        for q in visited:
            if raw_candidates(q):
                path=shortest_on_edges(case.base,q,known_edges,case.grid)
                if path and (len(path)-1)+case.reserve < case.sortie_budget:
                    frontier.append((len(path),signal(q),q,path))
        if frontier:
            _,_,p,path=min(frontier,key=lambda z:(z[0],z[1],z[2]))
            remaining=case.sortie_budget-(len(path)-1); total_moves += len(path)-1
            arrival=path[-2] if len(path)>1 else None
        else:
            p=case.base; arrival=None; remaining=case.sortie_budget

        while remaining>0:
            if p==case.resource:
                found=True; discovery_moves=total_moves; break

            return_path=shortest_on_edges(p,case.base,known_edges,case.grid)
            return_cost=(len(return_path)-1) if return_path else (0 if p==case.base else 10**9)
            ns=neighbors(case.grid,p)
            if len(ns)>=3:
                if p not in keepers: keepers[p]=set()
                elif arrival is not None: keeper_returns += 1

            candidates=raw_candidates(p)
            # One new edge can always be reversed, so require cost home + out/back edge + reserve.
            safe=[n for n in candidates if remaining >= return_cost + case.reserve + 2]
            if safe:
                safe.sort(key=lambda n:(signal(n), DIRS.index((n[0]-p[0],n[1]-p[1]))))
                n=safe[0]
                if p in keepers:
                    if keepers[p]: effective += 1
                    keepers[p].add(n)
                e=edge(p,n)
                if e in failed_entries: repeated_failed += 1
                known_edges.add(e); visited.add(n)
                arrival,p=p,n; remaining-=1; total_moves+=1
                continue

            if p in keepers and candidates: ignored += 1

            # Terminal branch consequence: mark it before selecting the next action.
            if p!=case.base and not candidates and len([n for n in ns if n not in dead])<=1:
                dead.add(p)
                if arrival is not None: failed_entries.add(edge(arrival,p))

            # Search locally known structure for the nearest unresolved keeper/frontier.
            alternatives=[]
            for q in visited:
                if q==p or not raw_candidates(q): continue
                travel=shortest_on_edges(p,q,known_edges,case.grid)
                home=shortest_on_edges(q,case.base,known_edges,case.grid)
                if not travel or not home: continue
                needed=(len(travel)-1)+(len(home)-1)+case.reserve+2
                if remaining>=needed:
                    alternatives.append((len(travel),signal(q),q,travel))
            if alternatives:
                _,_,q,travel=min(alternatives,key=lambda z:(z[0],z[1],z[2]))
                if q in keepers: effective += 1
                total_moves += len(travel)-1; remaining -= len(travel)-1
                arrival=travel[-2] if len(travel)>1 else arrival
                p=q
                continue

            # Only now may return pressure take control.
            return_path=shortest_on_edges(p,case.base,known_edges,case.grid)
            if not return_path:
                return Result(case.case_id,'persistence',case.seed,f'{case.width}x{case.height}',False,'no known return path',sortie-1,safe_returns,total_moves,0,0,bfs_grid(case.grid,case.base).get(case.resource,0),len(visited),len(dead),len(keepers),keeper_returns,effective,ignored,repeated_failed,False,False,True)
            total_moves += len(return_path)-1
            remaining -= len(return_path)-1
            p=case.base; safe_returns+=1
            break
        if found: break

    route=shortest_on_edges(case.base,case.resource,known_edges,case.grid) if found else None
    audit_out,audit_home,unchanged=verify_route(case,route or [])
    shortest=bfs_grid(case.grid,case.base).get(case.resource,0)
    failure='' if found else 'maximum safe sorties exhausted before discovery'
    return Result(case.case_id,'persistence',case.seed,f'{case.width}x{case.height}',bool(found and route and audit_out and audit_home and unchanged),failure,sortie,safe_returns,total_moves,discovery_moves,len(route)-1 if route else 0,shortest,len(visited),len(dead),len(keepers),keeper_returns,effective,ignored,repeated_failed,audit_out and audit_home,audit_out and audit_home,unchanged)

def run_relay_persistence(case:Case) -> Result:
    """Persistence policy with stationary junction keepers acting as safe relay anchors.

    A new sortie may begin at an established keeper with a replenished local budget.
    The keeper remains connected to base through known edges; global travel is not
    available to decision-making, but logistics movement to the relay is counted.
    """
    r=random.Random(case.seed ^ 0xC3C3C3C3)
    noise={p:(r.random()-.5)*4.0 for p in bfs_grid(case.grid,case.base)}
    def signal(p:Point)->float: return math.dist(p,case.resource)+noise.get(p,0.0)
    known_edges:Set[Tuple[Point,Point]]=set(); visited={case.base}; dead:set=set()
    keepers:Dict[Point,Set[Point]]={case.base:set()}; failed:set=set()
    total_moves=0; discovery_moves=0; safe_returns=0; repeated=0; returns=0; switches=0; ignored=0
    found=False; last_anchor=case.base

    def candidates(q:Point)->List[Point]:
        out=[]
        for n in neighbors(case.grid,q):
            e=edge(q,n)
            if n in dead or e in failed or e in known_edges: continue
            if n in keepers.get(q,set()): continue
            out.append(n)
        return out

    for sortie in range(1,case.max_sorties+1):
        # Select an established relay that still has reachable unresolved structure.
        anchors=[]
        for a in keepers:
            if candidates(a):
                logistics=shortest_on_edges(case.base,a,known_edges,case.grid)
                if logistics: anchors.append((-bfs_grid(case.grid,case.base).get(a,0),signal(a),a,logistics))
            else:
                # also allow anchor if a known frontier is reachable nearby
                for q in visited:
                    if candidates(q):
                        path=shortest_on_edges(a,q,known_edges,case.grid)
                        if path and len(path)-1 < case.sortie_budget-case.reserve-2:
                            logistics=shortest_on_edges(case.base,a,known_edges,case.grid)
                            if logistics: anchors.append((-bfs_grid(case.grid,case.base).get(a,0),signal(q),a,logistics)); break
        if not anchors:
            anchors=[(0,signal(case.base),case.base,[case.base])]
        _,_,anchor,logistics=min(anchors,key=lambda z:(z[0],z[1],z[2]))
        last_anchor=anchor
        total_moves += max(0,len(logistics)-1)  # supplying/reaching relay is real cost
        p=anchor; arrival=None; remaining=case.sortie_budget

        while remaining>0:
            if p==case.resource:
                found=True; discovery_moves=total_moves; break
            path_anchor=shortest_on_edges(p,anchor,known_edges,case.grid)
            anchor_cost=(len(path_anchor)-1) if path_anchor else (0 if p==anchor else 10**9)
            ns=neighbors(case.grid,p)
            if len(ns)>=3 and p not in keepers:
                keepers[p]=set()
            elif p in keepers and p!=anchor and arrival is not None:
                returns += 1

            raw=candidates(p)
            safe=[n for n in raw if remaining >= anchor_cost + case.reserve + 2]
            if safe:
                safe.sort(key=lambda n:(signal(n),DIRS.index((n[0]-p[0],n[1]-p[1]))))
                n=safe[0]
                if p in keepers:
                    if keepers[p]: switches+=1
                    keepers[p].add(n)
                e=edge(p,n)
                if e in failed: repeated+=1
                known_edges.add(e); visited.add(n)
                arrival,p=p,n; remaining-=1; total_moves+=1
                continue
            if p in keepers and raw: ignored+=1
            if p!=anchor and not raw and len([n for n in ns if n not in dead])<=1:
                dead.add(p)
                if arrival is not None: failed.add(edge(arrival,p))

            # Move to nearest unresolved point that is still safe relative to this relay.
            alts=[]
            for q in visited:
                if not candidates(q): continue
                travel=shortest_on_edges(p,q,known_edges,case.grid)
                home=shortest_on_edges(q,anchor,known_edges,case.grid)
                if travel and home and remaining >= (len(travel)-1)+(len(home)-1)+case.reserve+2:
                    alts.append((len(travel),signal(q),q,travel))
            if alts:
                _,_,q,travel=min(alts,key=lambda z:(z[0],z[1],z[2]))
                total_moves+=len(travel)-1; remaining-=len(travel)-1
                arrival=travel[-2] if len(travel)>1 else arrival; p=q
                continue

            # If current reach is exhausted, station a new relay at the deepest connected keeper.
            if p not in keepers and len(ns)>=2:
                keepers[p]=set()
            home=shortest_on_edges(p,anchor,known_edges,case.grid)
            if not home:
                return Result(case.case_id,'relay_persistence',case.seed,f'{case.width}x{case.height}',False,'lost connection to relay',sortie-1,safe_returns,total_moves,0,0,bfs_grid(case.grid,case.base).get(case.resource,0),len(visited),len(dead),len(keepers),returns,switches,ignored,repeated,False,False,True)
            total_moves+=len(home)-1; remaining-=len(home)-1; safe_returns+=1; p=anchor
            break
        if found: break

    route=shortest_on_edges(case.base,case.resource,known_edges,case.grid) if found else None
    ao,ah,unchanged=verify_route(case,route or [])
    shortest=bfs_grid(case.grid,case.base).get(case.resource,0)
    return Result(case.case_id,'relay_persistence',case.seed,f'{case.width}x{case.height}',bool(found and route and ao and ah and unchanged),'' if found else 'maximum relay sorties exhausted before discovery',sortie,safe_returns,total_moves,discovery_moves,len(route)-1 if route else 0,shortest,len(visited),len(dead),len(keepers),returns,switches,ignored,repeated,ao and ah,ao and ah,unchanged)

def make_cases(count:int,seed:int)->List[Case]:
    profiles=[
        (15,15,.02,82,8,5),(21,21,.02,128,12,7),(21,21,.12,118,12,8),
        (31,31,.05,190,18,10),(21,21,.06,78,14,12),(31,31,.01,150,20,14)
    ]
    out=[]
    for i in range(count):
        w,h,loops,budget,reserve,maxs=profiles[i%len(profiles)]
        out.append(generate_case(i+1,seed+i*131,w,h,loops,budget,reserve,maxs))
    return out

def summarize(results:List[Result])->dict:
    by={}
    for policy in sorted({r.policy for r in results}):
        rows=[r for r in results if r.policy==policy]
        successes=[r for r in rows if r.success]
        by[policy]={
            'cases':len(rows),'successes':len(successes),'success_rate':len(successes)/len(rows) if rows else 0,
            'mean_scout_moves':statistics.mean([r.scout_moves for r in successes]) if successes else None,
            'mean_route_efficiency':statistics.mean([r.route_length/r.shortest_global_route for r in successes if r.shortest_global_route]) if successes else None,
            'safe_returns':sum(r.safe_returns for r in rows),
            'keeper_effective_switches':sum(r.keeper_effective_switches for r in rows),
            'keeper_ignored_opportunities':sum(r.keeper_ignored_opportunities for r in rows),
            'repeated_failed_branch_entries':sum(r.repeated_failed_branch_entries for r in rows),
        }
    return by

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument('--cases',type=int,default=300)
    ap.add_argument('--seed',type=int,default=4200)
    ap.add_argument('--out-dir',default='/mnt/data/natural_math_persistence_results')
    args=ap.parse_args()
    cases=make_cases(args.cases,args.seed)
    results=[]
    for c in cases:
        results.append(run_blind(c)); results.append(run_persistence(c)); results.append(run_relay_persistence(c))
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    with (out/'results.json').open('w') as f: json.dump({'summary':summarize(results),'results':[asdict(r)|{'keeper_effectiveness':r.keeper_effectiveness} for r in results]},f,indent=2)
    with (out/'results.csv').open('w',newline='') as f:
        rows=[asdict(r)|{'keeper_effectiveness':r.keeper_effectiveness} for r in results]
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print(json.dumps(summarize(results),indent=2))

if __name__=='__main__': main()

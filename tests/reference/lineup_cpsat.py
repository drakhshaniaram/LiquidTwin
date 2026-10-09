"""Terminal line-up, two stages.
Stage 1: per job, enumerate candidate routes (k-shortest simple paths) on the pipe graph, after
         filtering arcs by certification, velocity, residue compatibility and checking pump head.
Stage 2: CP-SAT picks one route per job + start times (exclusive shared elements, changeover gaps,
         maintenance windows, tank stock/ullage, lateness).
Units: min, m, mm, m3, m3/h, head m.  Output JSON is compatible with lineup_viz.html.
"""
import json
import math
import sys
from itertools import islice

import networkx as nx
from ortools.sat.python import cp_model

PI = math.pi
# ---------------- data (mirrors lineup_sample.dzn) ----------------
# element: id -> (a, b, type, len, diam, dz, pump_head, residue, certified products)
E = {
 1: (1, 3, "JETTY", 400, 400, 2, 0, 1, {1, 2}),   2: (2, 3, "JETTY", 350, 400, 2, 0, 2, {1, 2}),
 3: (3, 12, "PUMP", 20, 400, 0, 60, 0, {1, 2}),   4: (12, 4, "COMMON", 900, 400, 6, 0, 0, {1, 2}),
 5: (3, 4, "COMMON", 1100, 300, -4, 0, 0, {1, 2}), 6: (4, 5, "TH", 300, 400, 0, 0, 1, {1, 2}),
 7: (4, 6, "TH", 350, 400, 0, 0, 2, {1, 2}),      8: (5, 7, "SEG", 80, 400, 0, 0, 1, {1, 2}),
 9: (5, 8, "SEG", 120, 400, 0, 0, 2, {1, 2}),     10: (6, 8, "SEG", 100, 400, 0, 0, 2, {1, 2}),
 11: (6, 9, "SEG", 90, 400, 0, 0, 0, {1, 2}),     12: (4, 13, "PUMP", 20, 250, 0, 50, 0, {1, 2}),
 13: (13, 10, "LOAD", 500, 250, 3, 0, 1, {1}),    14: (13, 11, "LOAD", 650, 250, 3, 0, 2, {2}),
 15: (5, 6, "VALVE", 0, 400, 0, 0, 0, {1, 2}),
}
FRIC = {1: 0.018, 2: 0.015}
CHANGEOVER = {(1, 1): 0, (2, 2): 0, (1, 2): 45, (2, 1): 45}
FLUSH_FACTOR = {(1, 2): 1.5, (2, 1): 1.5}
INCOMPAT = set()                                   # (residue, product) pairs needing manual cleaning
TANKS = {7: dict(prod=1, stock=2000, cap=8000, ok=True), 8: dict(prod=2, stock=1500, cap=5000, ok=True),
         9: dict(prod=0, stock=0, cap=6000, ok=True)}   # keyed by node id
MAINT = [(7, 0, 120)]                              # (element, from, to)
JOBS = [  # id, product, vol, rate, eta, etc, src candidates, dst candidates
 dict(id=1, prod=1, vol=4000, rate=1000, eta=0,   etc=400, src=[1],    dst=[7, 9]),
 dict(id=2, prod=2, vol=3000, rate=800,  eta=30,  etc=600, src=[2],    dst=[8, 9]),
 dict(id=3, prod=1, vol=600,  rate=300,  eta=60,  etc=480, src=[7, 9], dst=[10]),
 dict(id=4, prod=2, vol=500,  rate=250,  eta=100, etc=400, src=[8, 9], dst=[11]),
]
VMAX, FLUSH_RATE, VALVE_OP, H = 3.0, 600.0, 3, 1000
WT, WLATE, WFLUSH, WVALVE, WCOMMON = 1, 20, 1, 2, 3
K = 20  # candidate routes per (src, dst)

# ---------------- stage 1: candidate routes ----------------
def arc_data(job, e, rev):
    a, b, typ, L, D, dz, pump, res, cert = E[e]
    v = job["rate"] / 3600 / (PI * (D / 1000) ** 2 / 4)
    dzA = -dz if rev else dz
    need = 10 * (FRIC[job["prod"]] * L / (D / 1000) * v * v / 19.62 + dzA)          # dm
    fill = math.ceil(L / v / 60) + (VALVE_OP if typ == "VALVE" else 0)
    fv = 0.0 if res in (0, job["prod"]) else FLUSH_FACTOR.get((res, job["prod"]), 0.0) * PI * (D / 1000) ** 2 / 4 * L
    ok = (job["prod"] in cert and v <= VMAX and not (rev and pump > 0)
          and (res == 0 or res == job["prod"] or (res, job["prod"]) not in INCOMPAT))
    return dict(need=round(need), pump=0 if rev else round(10 * pump), fill=fill, fv=round(fv),
                ft=math.ceil(fv / FLUSH_RATE * 60), ok=ok)

def routes_for(job):
    G = nx.DiGraph(); info = {}
    for e, (a, b, *_ ) in E.items():
        for rev, (u, w) in ((False, (a, b)), (True, (b, a))):
            d = arc_data(job, e, rev)
            if not d["ok"]: continue
            cost = d["fill"] + d["ft"] + 1
            if G.has_edge(u, w) and G[u][w]["weight"] <= cost: continue
            G.add_edge(u, w, weight=cost); info[(u, w)] = (e, d)
    src = [n for n in job["src"] if n not in TANKS or (TANKS[n]["ok"] and TANKS[n]["prod"] == job["prod"] and TANKS[n]["stock"] >= job["vol"])]
    dst = [n for n in job["dst"] if n not in TANKS or (TANKS[n]["ok"] and TANKS[n]["prod"] in (0, job["prod"]) and TANKS[n]["cap"] - TANKS[n]["stock"] >= job["vol"])]
    out = []
    for s in src:
        for t in dst:
            if s == t or s not in G or t not in G: continue
            try: paths = list(islice(nx.shortest_simple_paths(G, s, t, weight="weight"), K))
            except nx.NetworkXNoPath: continue
            for p in paths:
                arcs = [info[(p[i], p[i + 1])] for i in range(len(p) - 1)]
                if sum(d["pump"] - d["need"] for _, d in arcs) < 0: continue          # pump head budget
                els = [e for e, _ in arcs]
                out.append(dict(src=s, dst=t, elems=els, fill=sum(d["fill"] for _, d in arcs),
                                ft=sum(d["ft"] for _, d in arcs), fv=sum(d["fv"] for _, d in arcs),
                                valves=sum(E[e][2] == "VALVE" for e in els), common=sum(E[e][2] == "COMMON" for e in els)))
    return out

# ---------------- stage 2: CP-SAT ----------------
def solve(time_limit=30):
    cand = {j["id"]: routes_for(j) for j in JOBS}
    for j in JOBS:
        print(f"job {j['id']}: {len(cand[j['id']])} candidate routes", file=sys.stderr)
        if not cand[j["id"]]: sys.exit(f"job {j['id']} has no feasible route (certification/velocity/head/stock)")
    m = cp_model.CpModel()
    s, en, late, lit, obj = {}, {}, {}, {}, []
    for j in JOBS:
        i = j["id"]; dur = math.ceil(j["vol"] * 60 / j["rate"])
        s[i] = m.NewIntVar(j["eta"], H, f"s{i}"); en[i] = m.NewIntVar(0, H, f"e{i}"); late[i] = m.NewIntVar(0, H, f"l{i}")
        m.Add(late[i] >= en[i] - j["etc"])
        lit[i] = [m.NewBoolVar(f"r{i}_{r}") for r in range(len(cand[i]))]
        m.AddExactlyOne(lit[i])
        for l, r in zip(lit[i], cand[i]):
            m.Add(en[i] == s[i] + dur + r["fill"] + r["ft"]).OnlyEnforceIf(l)
            obj.append((WFLUSH * r["fv"] + WVALVE * r["valves"] + WCOMMON * r["common"]) * l)
            for e_, f_, t_ in MAINT:                                              # maintenance windows
                if e_ in r["elems"]:
                    before = m.NewBoolVar("")
                    m.Add(en[i] <= f_).OnlyEnforceIf([l, before]); m.Add(s[i] >= t_).OnlyEnforceIf([l, before.Not()])
        obj.append(WT * (en[i] - j["eta"]) + WLATE * late[i])
    byid = {j["id"]: j for j in JOBS}
    for a in byid:                                                                 # shared-element conflicts
        for b in byid:
            if a >= b: continue
            for la, ra in zip(lit[a], cand[a]):
                for lb, rb in zip(lit[b], cand[b]):
                    if set(ra["elems"]) & set(rb["elems"]):
                        o = m.NewBoolVar("")
                        m.Add(en[a] + CHANGEOVER[(byid[a]["prod"], byid[b]["prod"])] <= s[b]).OnlyEnforceIf([la, lb, o])
                        m.Add(en[b] + CHANGEOVER[(byid[b]["prod"], byid[a]["prod"])] <= s[a]).OnlyEnforceIf([la, lb, o.Not()])
    for n, t in TANKS.items():                                                     # aggregate stock / ullage
        m.Add(sum(byid[i]["vol"] * l for i in byid for l, r in zip(lit[i], cand[i]) if r["src"] == n) <= t["stock"])
        m.Add(sum(byid[i]["vol"] * l for i in byid for l, r in zip(lit[i], cand[i]) if r["dst"] == n) <= t["cap"] - t["stock"])
    m.Minimize(sum(obj))
    sv = cp_model.CpSolver(); sv.parameters.max_time_in_seconds = time_limit; sv.parameters.num_workers = 8
    st = sv.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): sys.exit("no solution: " + sv.StatusName(st))
    jobs = []
    for j in JOBS:
        i = j["id"]; r = next(r for l, r in zip(lit[i], cand[i]) if sv.Value(l))
        jobs.append(dict(id=i, src=r["src"], dst=r["dst"], start=sv.Value(s[i]), end=sv.Value(en[i]),
                         late=sv.Value(late[i]), elems=r["elems"]))
    print(f"status={sv.StatusName(st)}", file=sys.stderr)
    return dict(obj=int(sv.ObjectiveValue()), jobs=jobs)

if __name__ == "__main__":
    print(json.dumps(solve()))

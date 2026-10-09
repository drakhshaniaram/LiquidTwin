# 09 Routing Engine (Stage 1)

Reference: `lineup_cpsat.py` `arc_data()` and `routes_for()`. This document formalizes and extends it.

## Inputs
Job (product p, volume V, rate Q, ETA/ETC, source and destination candidates, direction) plus graph snapshot, tank states, changeover matrix.

## Steps
1. **Candidate endpoints.** Sources must be certified for p, available, and `stock >= V` (OUT jobs, or tank-to-tank). Destinations must be available, `product in {empty, p}`, and `capacity - stock >= V`. Non-tank nodes (jetty, loading point) pass through.
2. **Arc filtering.** Drop an arc if any holds:
   - p not in `certified_products`
   - velocity `v > v_max`
   - reverse traversal of a pump
   - residue `r` is non-empty, different from p, and `(r, p)` is in the incompatible set (manual cleaning)
   - dedication excludes the job's tank group/product
   - element unavailable for the job window
3. **Arc cost** `w = fill_min + flush_min + 1` (the +1 is a hop penalty). Valve arcs add valve operation time.
4. **k-shortest simple paths** (Yen), K = 20 per (source, destination), by `w`.
5. **Pump head check.** `sum(pump_head) - sum(required_head) >= 0` along the path (see [10](10-Hydraulics-Engine.md)).
6. **Route metrics:** fill time, flush volume and time, valve count, common-header count, head margin, max velocity, elements.
7. **Output:** 0..N candidates, ranked; typically 3-7 on the sample.

## Quickest-route mode (planner)
Single job, no competing jobs: rank routes by total time `= fill + flush + volume/rate` and tie-break by flush volume, valves, common-header use. Response includes explanations for excluded arcs on the shortest unconstrained path ("Pipe P-12 excluded: velocity 3.4 m/s > 3.0").

## Extensions over the reference
| Reference limit | Improvement |
|---|---|
| Parallel elements collapsed | Keep all, expand alternatives |
| Static residue per element | Residue state resolved in Stage 2 sequencing; Stage 1 uses residue at `ETA` |
| Hard-coded friction per product | Product table, Colebrook option |
| Integer `dm` heads | Floats internally, rounding only at CP-SAT boundary |
| Routes through valves forced open per arc | Valve states modeled as exclusive elements |
| No tank-to-tank (transfer) explicit | Direction `TRANSFER` supported |

## Scale
Thousands of arcs, 100 jobs x ~30 endpoint pairs. Prune with bidirectional Dijkstra bounds, cache per (product, rate class). Target < 1 s for single job; Stage 1 for 100 jobs < 20 s on 8 cores (parallel per job).

## Failure output
If no route: structured `no_route` with the first blocking reason per cut (e.g., all paths blocked by maintenance on E7), enabling UI guidance.

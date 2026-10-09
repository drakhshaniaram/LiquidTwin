# 11 Optimization Engine (Stage 2, CP-SAT)

Reference: `lineup_cpsat.py` `solve()`; sample proved OPTIMAL, objective 1327, all four jobs on time.

## Decision variables
Per job `i`: start `s_i in [ETA_i, H]`, end `e_i`, lateness `l_i >= 0`, route literal `x_{i,r}` (exactly one).

## Constraints
1. **Route choice:** `sum_r x_{i,r} = 1`.
2. **Duration:** `x_{i,r} => e_i = s_i + ceil(V_i*60/Q_i) + fill_r + flush_time_r`.
3. **Lateness:** `l_i >= e_i - ETC_i`.
4. **Maintenance windows** per element `(from, to)`: if route uses it, either `e_i <= from` or `s_i >= to`.
5. **Exclusive shared elements** with changeover gap: for two jobs sharing an element, either `e_a + gap(p_a, p_b) <= s_b` or the converse.
6. **Tank stock/ullage:** aggregate (MVP) `sum vol_out <= stock`, `sum vol_in <= cap - stock`; Phase 5b time-indexed cumulative (see below).
7. **Horizon** `H` (reference 1000 min).

## Objective
$$\min\ \sum_i \big(w_T (e_i-\mathrm{ETA}_i) + w_L l_i\big)+\sum_{i,r} x_{i,r}\,(w_F\, fv_r + w_V\, valves_r + w_C\, common_r)$$
Reference weights: `w_T=1, w_L=20, w_F=1, w_V=2, w_C=3`. Weights are configuration per scenario.

## Scaling redesign (hundreds of jobs)
Reference conflict constraints are O(J^2 R^2). Replace with:
- For each job/route/element an **optional interval** `[s_i, e_i)` with presence `x_{i,r}`.
- Per element `AddNoOverlap` over its optional intervals.
- Changeover gaps via per-element **circuit** (sequence-dependent setup) or via interval padding by `max_gap` plus pairwise gap constraints only for pairs of *different products* on that element.
- Time bucketing/horizon rolling (e.g., 72 h with re-optimization every hour).

## Time-indexed inventory (Phase 5b)
Cumulative constraint per tank: `stock0 + inflow(t) - outflow(t)` within `[min, cap]` using reservoir/cumulative with job start/end events.

## Dynamic residue (Phase 5b)
Residue of each element after a job = job product. Flush cost when consecutive users differ is taken from the sequence on that element (circuit arcs carry the flush cost), replacing the static residue of the reference.

## Solver configuration
`max_time_in_seconds` default 30, `num_workers` 8, seeded (`random_seed`), warm-start from greedy plan, solution callback for progress/incumbents, objective bound reported as gap.

## Infeasibility handling
Stage 1 empty -> `NO_ROUTE(job, reasons)`. Stage 2 INFEASIBLE -> assumptions-based unsat core mapped to jobs/elements (e.g., "jobs 2 and 4 conflict on E7 during maintenance").

## Outputs
`{status, objective, bound, jobs:[{id, src, dst, start, end, late, route:[element_id,...], flush_volume}], kpis, element_timeline}`. Compatible with the reference JSON so the existing viewer works.

## Regression
`tests/reference` runs Python reference and new service on the sample; must match status OPTIMAL and objective 1327.

# Contract: Multi-Job Optimization

## Endpoint

`POST /api/v1/terminals/{terminal_id}/optimization/prepare`

`POST /api/v1/terminals/{terminal_id}/optimize`

Both endpoints accept the same terminal version and `OptimizationScenario`. Prepare returns each job's candidate routes or blockers without solving. Optimize deterministically re-generates candidates from the same immutable version before invoking the pure engine optimizer, so the API remains stateless and cannot accept client-invented route candidates. Both are synchronous and create no persistent scenario record.

## Job preparation and route candidates

- Every job is validated before solving and carries its own direction, product, endpoints, volume, minimum rate, ETA, due time, and optional pump suction inputs.
- Stage 1 candidates are generated using the selected terminal version. Availability is not used to remove candidates at ETA; Stage 2 applies maintenance against chosen schedule intervals.
- Any job with no Stage 1 route is returned with `NO_ROUTE`, the job ID, and Stage 1 blockers; it is not silently omitted.
- Preparation returns candidate route IDs, element paths, route metrics, and blockers per job for review before solving.
- Every scheduled job selects exactly one candidate route. The schedule cannot replace or mutate a route.

## Result

Return `status`, a human-readable `detail`, `terminal_version`, `solver_version`, `objective`, `best_bound`, per-job selected route/start/end/lateness, KPIs, `element_timeline`, and unscheduled-job explanations. A time-limited incumbent uses `FEASIBLE`; only a proven solution uses `OPTIMAL`. A time limit without an incumbent uses `UNKNOWN`. A no-route result is distinct from a CP-SAT `INFEASIBLE` result.

## Constraints and objective

- All starts, ends, due times, maintenance windows, and changeover gaps use integer minutes relative to `horizon_start`.
- Each element is exclusive for the full selected job interval; configured product changeover gaps are enforced between consecutive jobs.
- Maintenance intervals block use. Aggregate source stock and destination ullage are enforced across all jobs in the scenario.
- The weighted objective defaults to the reference weights and includes waiting, lateness, flush volume, valve count, and shared-header count.

## Determinism and limits

Default solver limit is 30 seconds, one worker, and a fixed seed. Request limits and all numeric fields are validated before model construction. Results identify the solver status and terminal version used.
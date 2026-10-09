# Data Model: Multi-Job Terminal Optimization

Optimization scenarios are request-scoped. Terminal topology, products, tank state, changeover rules, pump curves, and configured availability are read from the selected terminal version and its availability records.

## OptimizationScenario

| Field | Type | Rule |
|---|---|---|
| terminal_version | integer | Required; must match the selected immutable terminal version. |
| horizon_start | ISO date-time | Required; origin for all relative minute values. |
| horizon_minutes | integer | 1 through 10,080; default 1,000. |
| jobs | OptimizationJob[] | 1 through 100 jobs in the MVP API boundary. |
| objective_weights | ObjectiveWeights | Optional; bounded nonnegative integer weights. |
| time_limit_seconds | number | 1 through 30; default 30. |
| random_seed | integer | Optional; fixed default for reproducible runs. |

## OptimizationJob

| Field | Type | Rule |
|---|---|---|
| id | string | Required and unique within the scenario. |
| direction | IN / OUT / TRANSFER | Required. |
| product_id | string | Required; must exist in the terminal version. |
| source_ids / destination_ids | string[] | Required, nonempty; passed to Stage 1 candidate generation. |
| volume_m3 / rate_m3h | number | Required and positive; requested rate is the minimum accepted route flow. |
| earliest_start_min | integer | Relative to horizon start; 0 through horizon. |
| due_min | integer | Relative to horizon start; between earliest start and horizon. |
| pump_suction_inputs | PumpSuctionInput[] | Optional; required by Stage 1 for every curve pump on a candidate route. |

## ObjectiveWeights

`waiting`, `lateness`, `flush_volume`, `valves`, and `shared_headers` are nonnegative bounded integers. Defaults match the oracle: 1, 20, 1, 2, and 3.

## OptimizationResult

| Field | Type | Meaning |
|---|---|---|
| status | OPTIMAL / FEASIBLE / INFEASIBLE / NO_ROUTE / UNKNOWN | Solver result; FEASIBLE is not a proof of optimality, and UNKNOWN has no feasible incumbent. |
| detail | string | Human-readable status explanation; never presents UNKNOWN or INFEASIBLE as a feasible schedule. |
| terminal_version | integer | Version used for candidate generation. |
| objective / best_bound | integer or null | Objective and best lower bound when available. |
| jobs | ScheduledJob[] | Route, timing, lateness, and status per scheduled job. |
| unscheduled_jobs | UnscheduledJob[] | Stage 1 blockers or jobs identified by an infeasibility core. |
| kpis | object | On-time count, total lateness, waiting, flush volume, and makespan. |
| element_timeline | ElementUseInterval[] | Ordered uses and maintenance windows by resource. |

## Solver model

- A route literal selects exactly one Stage 1 route for each required job.
- Job start/end variables are integer minutes; route duration is fixed from Stage 1 route metrics.
- Each selected route-element use creates an optional interval; element `NoOverlap` includes fixed maintenance intervals.
- Per-element sequence circuits enforce product changeover gaps and reject transitions that require manual cleaning.
- Aggregate source stock and destination ullage are constrained across the whole horizon.
- Derived schedules and timelines are returned only; they are not written into `TerminalDocument` or persisted.
# Research: Multi-Job Terminal Optimization

## Decision: CP-SAT in the pure engine package

Use the repository's declared OR-Tools CP-SAT dependency for integer-minute route selection and scheduling. Keep model construction and solving in `packages/engine`; the API prepares request-scoped inputs and the browser renders results.

Rationale: `tests/reference/lineup_cpsat.py` is the behavioral oracle and already defines the accepted domain objective and sample constraints. A second solver or new service would duplicate established behavior.

Alternatives considered: hand-built greedy scheduling cannot prove OPTIMAL/objective 1327; a generic MILP layer adds a dependency and would not reproduce the CP-SAT oracle directly.

## Decision: Generate route candidates with Stage 1, schedule availability separately

Call `route_job` for each job to derive feasible route alternatives, passing the request's pump suction values and no time-window availability filter. Apply maintenance windows to the selected route intervals in Stage 2 so a route blocked at the earliest start can still be scheduled after the window.

Rationale: Stage 1 remains the single source of physical route feasibility. Stage 2 owns start-time-dependent maintenance and conflicts.

Alternatives considered: pre-filtering candidates against availability at ETA incorrectly drops jobs that can start later; reimplementing graph search in the optimizer would fork routing rules.

## Decision: Resource intervals plus per-element sequencing circuits

Create an optional interval for each job/element use, present when the selected route includes that element. Apply `AddNoOverlap` with fixed maintenance intervals. Add a per-element circuit over jobs that use the element; selected successor arcs enforce product-pair changeover gaps or forbid transitions requiring manual cleaning.

Rationale: This keeps conflict modeling tied to shared resources rather than expanding every route pair. It follows Constitution VI for larger job sets while retaining route-choice literals.

Alternatives considered: pairwise job-route disjunctions reproduce the small oracle but grow as O(J²R²); do not use that as the general implementation.

## Decision: Deterministic CP-SAT configuration

Default to a 30-second time limit, one worker, and a fixed seed. Allow validated time-limit and seed inputs; keep worker count at one for reproducible default results. Return FEASIBLE with objective/bound when a time-limited incumbent exists, never OPTIMAL unless CP-SAT proves it.

Rationale: multi-worker CP-SAT can introduce search-order nondeterminism; the Constitution requires reproducibility for identical inputs and solver settings.

## Decision: Request-scoped scenarios and minute offsets

Represent scenario horizon start as an ISO timestamp and encode all job ETA, due time, maintenance, and schedule values as integer minutes relative to that instant. Do not persist jobs or optimization results in the terminal document or database in this phase.

Rationale: this gives the UI and API one explicit clock origin while preserving the terminal document as the authoritative topology and equipment model.

## Decision: Reference objective and aggregate inventory

Use configurable integer weights defaulting to the oracle values (`waiting=1`, `lateness=20`, `flush_volume=1`, `valves=2`, `shared_headers=3`). Treat tank stock and ullage as aggregate horizon budgets; defer time-indexed inventory to a later phase.

Rationale: matches `docs/11-Optimization-Engine.md` and the existing four-job reference case without expanding scope into inventory simulation.
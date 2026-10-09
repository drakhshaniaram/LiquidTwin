# Tasks: Multi-Job Terminal Optimization

**Input**: Design documents from `specs/003-multi-job-optimization/`
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/optimization.md`, `quickstart.md`
**Tests**: Required by Constitution IV and the reference-oracle requirement.

## Phase 1: Setup

- [X] T001 Promote `ortools>=9.10` to the engine runtime dependency used by the API through `packages/engine/pyproject.toml`.
- [X] T002 Define request/response schemas for preparation and optimization in `specs/001-terminal-designer-routing/contracts/openapi.yaml` and regenerate `apps/web/src/api/client.ts`.

## Phase 2: User Story 1 - Prepare a Set of Terminal Jobs (P1)

**Goal**: Validate jobs and review Stage 1 route candidates or blockers before scheduling.
**Independent test**: Prepare the four reference jobs and verify each has candidates; prepare a job with no Stage 1 path and verify it remains visible with blockers.

- [X] T003 [P] [US1] Write failing engine tests for per-job Stage 1 candidate generation, determinism, and NO_ROUTE blockers in `packages/engine/tests/test_optimization.py`.
- [X] T004 [US1] Add scenario/job/preparation result types and a pure candidate-preparation function using `route_job` in `packages/engine/src/liquidtwin_engine/optimization.py`.
- [X] T005 [P] [US1] Add preparation API tests for valid candidates and jobs with no candidates in `services/api/tests/test_terminals_api.py`.
- [X] T006 [US1] Implement `POST /terminals/{terminal_id}/optimization/prepare`, pin the requested terminal version, and return each job's route metrics or blockers in `services/api/src/liquidtwin_api/routes/optimization.py` and `services/api/src/liquidtwin_api/main.py`.
- [X] T007 [US1] Add typed preparation request helpers and route-candidate UI models in `apps/web/src/api/terminals.ts` and `apps/web/src/api/client.ts`.
- [X] T008 [US1] Build the multi-job scenario editor and candidate/blocker review state in `apps/web/src/App.tsx` and `apps/web/src/styles.css`.

## Phase 3: User Story 2 - Optimize a Terminal Lineup (P1)

**Goal**: Select one reviewed route per job and produce a feasible, explainable schedule.
**Independent test**: The four-job oracle is OPTIMAL with objective 1327 and all four jobs on time; maintenance, shared resources, changeovers, and aggregate inventory are respected.

- [X] T009 [P] [US2] Write failing solver tests for route choice, timing, lateness/objective terms, fixed-seed determinism, and the 1327 reference objective in `packages/engine/tests/test_optimization.py`.
- [X] T010 [P] [US2] Write failing resource tests for maintenance, shared-element exclusivity, product changeover gaps, and aggregate tank stock/ullage in `packages/engine/tests/test_optimization.py` and the reference oracle.
- [X] T011 [US2] Implement CP-SAT route literals, integer start/end/lateness variables, horizon bounds, and configured objective weights in `packages/engine/src/liquidtwin_engine/optimization.py`.
- [X] T012 [US2] Add per-job/per-element optional intervals with `AddNoOverlap` maintenance constraints and per-element sequencing circuits for changeover gaps/manual-clean transitions in `packages/engine/src/liquidtwin_engine/optimization.py`.
- [X] T013 [US2] Add aggregate source stock and destination ullage constraints and map infeasibility assumptions to jobs/resources in `packages/engine/src/liquidtwin_engine/optimization.py`.
- [X] T014 [US2] Implement bounded deterministic solver configuration and distinct OPTIMAL, FEASIBLE, INFEASIBLE, NO_ROUTE, and UNKNOWN result serialization in `packages/engine/src/liquidtwin_engine/optimization.py`.
- [X] T015 [P] [US2] Add optimize endpoint oracle coverage for terminal version, status/objective/KPI/timeline serialization in `services/api/tests/test_terminals_api.py`.
- [X] T016 [US2] Implement `POST /terminals/{terminal_id}/optimize` using existing terminal/availability repositories and the pure engine optimizer in `services/api/src/liquidtwin_api/routes/optimization.py`.
- [X] T017 [US2] Add solve actions, progress/status, selected route, start/end, lateness, and objective presentation in `apps/web/src/App.tsx` and `apps/web/src/styles.css`.

## Phase 4: User Story 3 - Understand and Inspect a Plan (P2)

**Goal**: Explain solver status and conflicts and inspect selected routes on the terminal graph.
**Independent test**: Inspect the optimal reference schedule and an infeasible case; no infeasible or time-limited plan is represented as optimal, and selecting a job highlights its selected route.

- [X] T018 [P] [US3] Add tests for infeasible job explanations, FEASIBLE and UNKNOWN states, KPIs, and per-element timelines in `packages/engine/tests/test_optimization.py` and `services/api/tests/test_terminals_api.py`.
- [X] T019 [US3] Return objective/bound, KPIs, per-job details, unscheduled-job reasons, and ordered element-use intervals in `packages/engine/src/liquidtwin_engine/optimization.py` and `services/api/src/liquidtwin_api/routes/optimization.py`.
- [X] T020 [US3] Render an element timeline, named solver/conflict explanations, and route selection highlighting in the optimizer UI in `apps/web/src/App.tsx` and `apps/web/src/styles.css`.

## Phase 5: Oracle, Scale, and Release Gates

- [X] T021 [P] Add a four-job optimizer oracle regression asserting OPTIMAL, objective 1327, and all jobs on time in `tests/reference/test_multi_job_optimization_oracle.py`.
- [X] T022 [P] Add a synthetic 40-job test that exercises per-element interval modeling without route-pair expansion and captures solve latency in `packages/engine/tests/test_optimization.py`.
- [X] T023 Update `docs/11-Optimization-Engine.md` with the implemented model, statuses, objective, limits, and deferred inventory behavior.
- [X] T024 Run the reference oracle, full engine/API and frontend tests, schema generation, Ruff, mypy, ESLint, Prettier, and production build; record results in `specs/003-multi-job-optimization/quickstart.md`.

## Dependencies and Execution Order

- Setup T001-T002 precedes API and web work.
- US1 candidate preparation precedes US2 solving; both use the same terminal version and deterministic Stage 1 candidates.
- US2 interval, sequence, and inventory constraints precede US3 result inspection.
- Oracle and release gates in T021-T024 close the feature; the established reference objective is non-negotiable.

## Implementation Strategy

- Complete US1 preparation and candidate review first.
- Implement and test the pure engine solver before wiring the synchronous API.
- Complete the four-job oracle before expanding the UI or scale tests.
- Keep the scenario request-scoped; defer persistent optimization history and time-indexed inventory.
# Implementation Plan: Multi-Job Terminal Optimization

**Branch**: `003-multi-job-optimization` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-multi-job-optimization/spec.md`

## Summary

Add a deterministic Stage 2 scheduler that prepares Stage 1 route candidates for a versioned terminal and submitted job set, then solves that reviewed scenario. Use OR-Tools CP-SAT to choose one route per job and schedule jobs within a finite horizon while respecting maintenance, shared-element exclusivity and changeovers, aggregate tank stock/ullage, and the configured weighted objective. Return NO_ROUTE, INFEASIBLE, FEASIBLE, OPTIMAL, or UNKNOWN without persisting transient scenarios.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.12 engine/API; TypeScript 5.9, React 18, Node 20 web

**Primary Dependencies**: OR-Tools CP-SAT, NetworkX Stage 1 candidate generation, FastAPI/Pydantic, React Query/Zustand

**Storage**: No new tables. Terminal versions and availability remain in PostgreSQL; optimization scenarios/results are request-scoped and returned to the caller.

**Testing**: pytest for solver constraints and oracle; API contract tests; Vitest for pure UI helpers; browser verification of scenario preparation and schedule inspection.

**Target Platform**: Linux API/container and evergreen desktop/mobile browsers

**Project Type**: Cross-cutting engine/API/web feature in the existing monorepo

**Performance Goals**: Four-job reference scenario proves OPTIMAL/objective 1327 within 30 seconds. Beyond dozens of jobs, resource constraints use per-element optional intervals and sequence circuits, not route-pair conflict expansion.

**Constraints**: Fixed minute resolution; Stage 1 remains the only route-feasibility source; all required jobs must be scheduled or the result is not feasible; deterministic default uses one solver worker and fixed seed; maintenance is modeled in the scenario horizon; objective weights and solver limit are bounded inputs.

**Scale/Scope**: MVP covers submitted terminal job sets, the four-job reference oracle, availability windows, route-level exclusive equipment, and aggregate tank inventory. Time-indexed inventory, live SCADA, D365 work-order integration, and persisted scenario history remain out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| I. Single Terminal Document | Pass | Terminal topology, products, tank attributes, changeovers, and equipment remain sourced from the versioned TerminalDocument. |
| II. Physics-Aware and Explainable | Pass | Stage 1 supplies feasible routes and blockers; Stage 2 adds explicit schedule conflicts, maintenance, inventory, and objective terms. |
| III. Reference-Oracle Regression | Hard gate | Four-job output must remain OPTIMAL with objective 1327 and all jobs on time. |
| IV. Test-First | Pass | Solver constraints and objective require failing tests before implementation; engine stays UI/network independent. |
| V. Deterministic and Reproducible | Pass | Fixed seed and one worker are defaults; report terminal version and solver parameters. |
| VI. Performance Budgets | Pass by design, measure at release | Per-element optional intervals and setup circuits avoid O(J²R²) route-pair expansion beyond dozens of jobs; four-job solve limit is 30 seconds. |
| VII. Mobile-First, Simple | Tracked inherited deviation | The planner UI must remain responsive; feature 001 owns the required PixiJS renderer migration. |
| Security (OIDC) | Tracked inherited deviation | Optimization remains behind the existing API boundary; do not expose the trusted-network MVP publicly before OIDC. |

Post-design re-check: no new constitution deviation is required. Solver complexity is contained per resource; objective and inventory assumptions are explicit in the data model.

## Project Structure

### Documentation (this feature)

```text
specs/003-multi-job-optimization/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/optimization.md
└── tasks.md
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
packages/engine/src/liquidtwin_engine/optimization.py
packages/engine/tests/test_optimization.py
services/api/src/liquidtwin_api/routes/optimization.py
services/api/tests/test_optimization_api.py
specs/001-terminal-designer-routing/contracts/openapi.yaml
apps/web/src/api/terminals.ts
apps/web/src/App.tsx
apps/web/src/styles.css
tests/reference/test_multi_job_optimization_oracle.py
tests/reference/lineup_cpsat.py
```

**Structure Decision**: Implement the pure CP-SAT model in the engine package, add request-scoped prepare and optimize API endpoints using the existing terminal and availability repositories, and build scenario/result views into the current React operations workspace. Both endpoints take the same immutable terminal version and job input; optimize re-derives candidates so previewed paths cannot drift. Do not introduce scenario persistence or a new deployable service.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| - | No new constitution violations | - |

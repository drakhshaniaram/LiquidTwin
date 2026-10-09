# Implementation Plan: Terminal Designer, Graph and Quickest-Route Planner

**Branch**: `001-terminal-designer-routing` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-terminal-designer-routing/spec.md`

## Summary

Deliver the first MVP slice: a mobile-friendly web app where users design or import a terminal (JSON/CSV), a backend builds a validated directed multigraph, and a routing engine (Stage 1 of the reference line-up algorithm) returns the quickest feasible route with explanations. Availability windows are accepted from the UI and from an external API and change routing results. Approach: TypeScript/React/PixiJS front end; Python/FastAPI back end with a pure-Python engine library (graph, hydraulics, routing); PostgreSQL storing versioned JSONB terminal documents; one JSON Schema generating both TypeScript and Pydantic types. Multi-job optimization (CP-SAT) is out of scope but the engine library is structured so Stage 2 plugs in later. The MVP is single user (no locking or concurrent-edit handling); append-only versions and the anonymous actor seam keep multi-user open. Route selection follows the clarified pipeline (k shortest paths, feasibility filter, shortlist) and the user confirms the final route, stored as a ConfirmedRoute.

## Technical Context

**Language/Version**: Python 3.12 (backend, engine); TypeScript 5.x on Node 20 (frontend)

**Primary Dependencies**: FastAPI, Pydantic v2, networkx (rustworkx if profiling requires), SQLAlchemy + Alembic, psycopg; React 18, Vite, PixiJS v8, Zustand, TanStack Query, elkjs (auto-layout), Papa Parse (CSV)

**Storage**: PostgreSQL 16 (JSONB terminal documents, version history, availability windows). Redis is not needed yet (no long-running solver jobs in this feature)

**Testing**: pytest + hypothesis (engine, API), Vitest (frontend logic), Playwright (E2E incl. mobile viewport), JSON Schema contract tests, reference-oracle test against `lineup_cpsat.py` sample

**Target Platform**: Linux containers (API, DB); evergreen browsers incl. iOS Safari and Android Chrome (PWA)

**Project Type**: web application (frontend + backend + shared schema package)

**Performance Goals**: single-job route < 1 s and graph build < 200 ms on 500 tanks / 5,000 pipes; render >= 30 fps for that terminal on a mid-range phone; availability change applied < 20 ms incrementally

**Constraints**: deterministic results; units fixed (min, m, mm, m3, m3/h, head m); no authentication in this feature (spec FR-019), so deploy to trusted network only; all input validated at API boundary

**Scale/Scope**: up to 500 tanks, 5,000 pipes, 100 loading points, 500 valves, 50 jetties per terminal; single organization; about 6 screens (terminal list, designer, validation, route planner, availability, version history)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| I. Single Terminal Document | Pass | One JSON Schema (`contracts/terminal-document.schema.json`) generates TS and Pydantic types; CSV import maps to the same document |
| II. Physics-Aware and Explainable | Pass | Hydraulics module (velocity, friction, lift, pump head); every excluded arc carries a reason code (`data-model.md`: ExclusionReason) |
| III. Reference-Oracle Regression | Pass | `tests/reference` loads the sample terminal and compares routes/metrics to `lineup_cpsat.py` Stage 1 output; the objective-1327 oracle is reserved for the Stage 2 feature |
| IV. Test-First | Pass | Engine is a UI-free library with contract tests written first (see quickstart) |
| V. Deterministic and Reproducible | Pass | K-shortest-path tie-breaking by stable element id; responses record document version and engine version |
| VI. Performance Budgets | Pass | Budgets copied into Technical Context; benchmark task required |
| VII. Mobile-First, Simple | Pass | PWA, touch gestures, responsive panels; no Redis/queue until needed |
| Security constraint (OIDC) | **Deviation** | No sign-in per spec FR-019; see Complexity Tracking |

Post-design re-check (after Phase 1): unchanged; the single deviation is justified below.

## Project Structure

### Documentation (this feature)

```text
specs/001-terminal-designer-routing/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml
│   ├── terminal-document.schema.json
│   └── csv-import.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
apps/web/                      # React + Vite + PixiJS PWA
├── src/
│   ├── canvas/                # Pixi scene, layers, LOD, hit-testing
│   ├── editor/                # tools, undo/redo, property panels, validation list
│   ├── import-export/         # JSON and CSV import/export, mapping wizard
│   ├── planner/               # route request form, result list, explanation panel
│   ├── availability/          # availability editor
│   ├── api/                   # typed client generated from openapi.yaml
│   └── state/                 # Zustand stores
└── tests/                     # Vitest + Playwright

services/api/                  # FastAPI
├── src/liquidtwin_api/
│   ├── routes/                # terminals, versions, validate, route, availability
│   ├── db/                    # SQLAlchemy models, Alembic migrations
│   └── schemas/               # generated Pydantic types
└── tests/

packages/engine/               # pure Python library, no web/DB imports
├── src/liquidtwin_engine/
│   ├── document.py            # parse + normalize TerminalDocument
│   ├── graph.py               # multigraph build, availability overlay
│   ├── hydraulics.py          # velocity, friction head, lift, pump head
│   ├── routing.py             # filters, k-shortest paths, route metrics, explanations
│   ├── validation.py          # terminal validation rules
│   └── csv_import.py          # CSV bundle -> TerminalDocument
└── tests/

packages/schema/               # JSON Schema + codegen scripts (TS + Pydantic)
tests/reference/               # sample terminal JSON + lineup_cpsat.py oracle comparison
```

**Structure Decision**: Web application with a separate pure engine library so the same code is reused by the future optimizer feature, the regression tests, and the API. The existing root files (`index.html`, `LiquidScheduler-sim.html`, `src/config.js`) are the legacy prototype and stay untouched until the simulation feature supersedes them.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| No authentication (constitution: OIDC required) | Explicit product decision for the MVP slice (spec FR-019) to speed up first delivery | Adding OIDC now delays the first usable slice; mitigated by trusted-network deployment, no external exposure, and an API dependency seam so OIDC can be added without changing routes. Must be closed before any internet-facing deployment |
| Separate `packages/engine` library (beside web, api, schema) | Constitution IV requires UI-free engine libraries; reused by the optimizer and reference tests | Embedding engine logic in the API would couple it to FastAPI and block reuse by CP-SAT and tests |

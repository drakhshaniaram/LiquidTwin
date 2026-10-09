# Implementation Plan: Terminal Designer, Graph and Quickest-Route Planner

**Branch**: `001-terminal-designer-routing` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-terminal-designer-routing/spec.md`

## Summary

Deliver a mobile-friendly terminal designer and graph view, JSON/CSV import and export, validation, versioned persistence, availability management, and quickest-route planning. The canonical engine `TerminalGraph` is derived once from the versioned terminal document; both the graph API projection and the routing engine use this builder. Routing filters the graph for the job, generates up to K shortest node paths, expands parallel elements, checks pump head, and returns an explainable shortlist for user confirmation. The production renderer remains PixiJS v8 per the constitution. The current designer and graph view are an SVG prototype; the 5,000-pipe mobile performance target is not yet verified, and SVG must not be treated as having passed that gate. The backend is Python/FastAPI with a UI-free engine library; PostgreSQL stores versioned JSONB documents; JSON Schema generates TypeScript and Pydantic types. Multi-job optimization (CP-SAT) is out of scope. The MVP is single-user without sign-in, with append-only versions and an anonymous actor seam.

## Technical Context

**Language/Version**: Python 3.12 (backend, engine); TypeScript 5.x on Node 20 (frontend)

**Primary Dependencies**: FastAPI, Pydantic v2, networkx (rustworkx only if profiling requires), SQLAlchemy + Alembic, psycopg; React 18, Vite 7, TanStack Query, Zustand, Papa Parse. The current canvas uses React-rendered SVG; PixiJS v8 is the required production renderer target. elkjs is selected for import auto-layout but is not wired into the current editor yet.

**Storage**: PostgreSQL 16 (JSONB terminal documents, version history, availability windows). Redis is not needed yet (no long-running solver jobs in this feature)

**Testing**: pytest + hypothesis (engine, API), Vitest (frontend logic), Playwright (E2E incl. mobile viewport), JSON Schema contract tests, reference-oracle test against `lineup_cpsat.py` sample

**Target Platform**: Linux containers (API, DB); evergreen browsers incl. iOS Safari and Android Chrome (PWA)

**Project Type**: web application (frontend + backend + shared schema package)

**Performance Goals**: single-job route < 1 s and graph build < 200 ms on 500 tanks / 5,000 pipes; render >= 30 fps for that terminal on a Pixel 5-class phone; availability change applied < 20 ms incrementally. The graph/routing tests pass on small fixtures; the scale benchmark and real-device frame-rate gate remain unverified. A 500-tank/5,000-pipe fixture generator is not present yet.

**Constraints**: deterministic results; units fixed (min, m, mm, m3, m3/h, head m); no authentication in this feature (spec FR-019), so deploy to trusted network only; all input validated at API boundary

**Scale/Scope**: up to 500 tanks, 5,000 pipes, 100 loading points, 500 valves, 50 jetties per terminal; single organization; terminal register, designer/layout view, graph view, validation, route planner, availability, and version history

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| I. Single Terminal Document | Pass | One JSON Schema (`contracts/terminal-document.schema.json`) generates TS and Pydantic types; CSV import maps to the same document |
| II. Physics-Aware and Explainable | Pass | Hydraulics module (velocity, friction, lift, pump head); every excluded arc carries a reason code (`data-model.md`: ExclusionReason) |
| III. Reference-Oracle Regression | Pass | `tests/reference` loads the sample terminal and compares routes/metrics to `lineup_cpsat.py` Stage 1 output; the objective-1327 oracle is reserved for the Stage 2 feature |
| IV. Test-First | Pass | Engine is a UI-free library with contract tests written first (see quickstart) |
| V. Deterministic and Reproducible | Pass | K-shortest-path tie-breaking by stable element id; responses record document version and engine version |
| VI. Performance Budgets | **Open** | Budgets are stated above, but the 500-tank/5,000-pipe route/graph benchmark and Pixel 5-class 30 fps test have not been run; no synthetic fixture generator is present |
| VII. Mobile-First, Simple | **Tracked deviation** | Responsive SVG prototype supports touch and graph inspection. PixiJS remains the production renderer target; release-scale performance is not claimed until migration and/or required acceptance evidence is complete |
| Security constraint (OIDC) | **Deviation** | No sign-in per spec FR-019; see Complexity Tracking |

Post-design re-check (after Phase 1): the OIDC and interim-renderer deviations remain documented below; the performance gate remains open.

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
apps/web/                      # React + Vite PWA; current UI uses SVG
├── src/
│   ├── App.tsx                # current terminal register, editor, layout and graph views
│   ├── api/                   # generated OpenAPI client and terminal API functions
│   ├── editor/history.ts      # undo/redo history
│   ├── store/workspace.ts     # active terminal state
│   └── styles.css
└── tests/                     # Vitest editor tests

services/api/                  # FastAPI
├── src/liquidtwin_api/
│   ├── routes/                # implemented: terminals, graph, validate; route and availability APIs remain planned
│   ├── db/                    # SQLAlchemy models, repository, Alembic migrations
│   └── schemas/               # generated Pydantic types
└── tests/

packages/engine/               # pure Python library, no web/DB imports
├── src/liquidtwin_engine/
│   ├── document.py            # parse + normalize TerminalDocument
│   ├── graph.py               # shared directed multigraph builder
│   ├── hydraulics.py          # velocity, friction, lift and pump head
│   ├── routing.py             # filters, k-shortest paths, metrics and explanations
│   ├── validation.py          # terminal validation rules
│   └── csv_import.py          # CSV bundle -> TerminalDocument
└── tests/

packages/schema/               # JSON Schema + generated TS and Pydantic types
tests/reference/               # sample terminal and lineup_cpsat.py oracle tests
```

**Structure Decision**: Keep graph derivation and route computation in `packages/engine`; the API graph endpoint serializes that shared model rather than implementing a second graph. The current React editor remains in `App.tsx`; extract the renderer and remaining route/availability screens into dedicated modules as they are implemented. The route and availability contracts exist, but their routers are not mounted yet. Root `index.html`, `LiquidScheduler-sim.html`, and `src/config.js` remain the legacy prototype.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| No authentication (constitution: OIDC required) | Explicit product decision for the MVP slice (spec FR-019) to speed up first delivery | Adding OIDC now delays the first usable slice; mitigated by trusted-network deployment, no external exposure, and an API dependency seam so OIDC can be added without changing routes. Must be closed before any internet-facing deployment |
| Separate `packages/engine` library (beside web, api, schema) | Constitution IV requires UI-free engine libraries; reused by the optimizer and reference tests | Embedding engine logic in the API would couple it to FastAPI and block reuse by CP-SAT and tests |
| Interim SVG renderer instead of constitution-required PixiJS | The current SVG editor and graph view establish and validate interaction and graph semantics; keep this implementation explicitly provisional while the production renderer is migrated to PixiJS | Replacing the renderer in the same slice would combine graph/API behavior changes with a canvas rewrite. This is not a performance waiver: SC-007 and the 5,000-pipe target remain release gates |

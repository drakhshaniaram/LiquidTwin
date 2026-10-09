# Tasks: Terminal Designer, Graph and Quickest-Route Planner

**Input**: Design documents in `specs/001-terminal-designer-routing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Tests**: Included. Constitution principle IV (Test-First) requires engine tests written and failing before implementation.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: US1 Design/import, US2 Quickest route, US3 Availability, US4 Mobile

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Verify repository layout from plan.md: `apps/web/`, `services/api/`, `packages/engine/`, `packages/schema/`, `tests/reference/`, and `tests/perf/` exist; shared documentation lives in `docs/README.md`
- [X] T002 [P] Initialize `packages/engine/pyproject.toml` (Python 3.12, networkx, pydantic, pytest, hypothesis; test-only: ortools for the reference oracle) and `packages/engine/src/liquidtwin_engine/__init__.py` exposing `__version__`
- [X] T003 [P] Initialize `services/api/pyproject.toml` (FastAPI, SQLAlchemy, Alembic, psycopg, httpx, pytest) depending on `packages/engine`
- [X] T004 [P] Initialize `apps/web` with Vite + React 18 + TypeScript 5, PixiJS v8, Zustand, TanStack Query, Papa Parse, elkjs, Vitest, Playwright, vite-plugin-pwa in `apps/web/package.json`
- [X] T005 [P] Add `docker-compose.yml` at repo root with PostgreSQL 16 service `db` and `.env.example`
- [X] T006 [P] Configure linting and formatting: `ruff` and `mypy` in `pyproject.toml` files, ESLint and Prettier in `apps/web/`, plus a CI workflow `.github/workflows/ci.yml` running all test commands from quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T007 Reconcile design docs with the clarified spec: add `ConfirmedRoute` entity (request, route steps, terminal_version, outdated flag), update the `RAIL_CAR` node type and `ENDPOINT_DIRECTION` exclusion reason in `specs/001-terminal-designer-routing/data-model.md`, and update `plan.md` (summary, structure, single-user MVP with multi-user seam: append-only versions, actor seam, optional `base_version` on save reserved for later)
- [x] T008 Update `specs/001-terminal-designer-routing/contracts/openapi.yaml`: add `POST /terminals/{terminalId}/routes/confirm` (stores a ConfirmedRoute) and `GET /terminals/{terminalId}/routes/confirmed`, add `ENDPOINT_DIRECTION` to the exclusion reasons, and add `RAIL_CAR` to the node types in `terminal-document.schema.json`
- [X] T009 Copy `terminal-document.schema.json` into `packages/schema/terminal-document.schema.json` and add codegen scripts `packages/schema/codegen.sh` (json-schema-to-typescript to `apps/web/src/api/types.ts`, datamodel-code-generator to `services/api/src/liquidtwin_api/schemas/terminal_document.py`)
- [X] T010 Add `schema:check` script (regenerates and fails on diff) in `packages/schema/package.json` and wire into `.github/workflows/ci.yml`
- [X] T011 [P] Create the reference sample terminal `tests/reference/sample-terminal.json` from `lineup_cpsat.py` data (15 elements, tanks 7/8/9, products 1/2, changeover 45 min, flush factor 1.5, friction 0.018/0.015, VMAX 3.0) and copy `lineup_cpsat.py` to `tests/reference/lineup_cpsat.py` (oracle tests import its Stage 1 functions and need `ortools` installed)
- [X] T012 [P] Create the equivalent CSV bundle in `tests/reference/csv/` (products.csv, changeover.csv, nodes.csv, tanks.csv, elements.csv) per `contracts/csv-import.md`
- [X] T013 Implement document parsing and normalization (order by id, apply schema defaults) in `packages/engine/src/liquidtwin_engine/document.py` using generated Pydantic models from T009
- [X] T014 Define shared engine types (ExclusionReason enum, Exclusion, ValidationIssue, Route, RouteMetrics) in `packages/engine/src/liquidtwin_engine/types.py` matching data-model.md and openapi.yaml
- [X] T015 Create SQLAlchemy models `Terminal`, `TerminalVersion` (document JSONB, append-only), `AvailabilityWindow` (unique on terminal_id+element_id+source+external_ref), `ConfirmedRoute` in `services/api/src/liquidtwin_api/db/models.py`
- [X] T016 Create the first Alembic migration for the models in `services/api/src/liquidtwin_api/db/migrations/`
- [X] T017 Create FastAPI app skeleton with `/api/v1` router, `current_actor()` dependency returning an anonymous actor (OIDC seam, plan Complexity Tracking), structured JSON logging and error handler returning `{code, message}` in `services/api/src/liquidtwin_api/main.py`
- [X] T017a Create a minimal terminal repository (load latest or specific version document, append version) in `services/api/src/liquidtwin_api/db/repository.py`, used by US1 routes and US2 routing
- [X] T018 [P] Generate the typed API client from `openapi.yaml` into `apps/web/src/api/client.ts` and add `npm run api:gen`
- [X] T019 [P] Create app shell with routing (terminal list, designer, planner, availability, versions), Zustand store skeleton, and PWA manifest in `apps/web/src/`

**Checkpoint**: foundation ready; user stories can start.

---

## Phase 3: User Story 1 - Design or import a terminal (Priority: P1) MVP

**Goal**: Create terminals visually or by JSON/CSV import, validate continuously, and save versions (single user).

**Independent Test**: Import the sample from JSON and from the CSV bundle; both give identical documents with no ERROR issues. Build a small terminal by hand, save, reload unchanged.

### Tests for User Story 1 (write first, must fail)

- [X] T020 [P] [US1] Validation rule tests (dangling pipe, header on several tanks, duplicate ids, unknown product, stock > capacity, isolated node) in `packages/engine/tests/test_validation.py`
- [X] T021 [P] [US1] CSV import tests incl. per-row errors, unknown column rejection, `x_` columns ignored, all-or-nothing in `packages/engine/tests/test_csv_import.py`
- [X] T022 [P] [US1] JSON/CSV equivalence test (`-k import_equivalence`) comparing documents from `tests/reference/sample-terminal.json` and `tests/reference/csv/` in `tests/reference/test_import_equivalence.py`
- [X] T023 [P] [US1] API contract tests for terminals CRUD, import, export, versions, restore, and validate in `services/api/tests/test_terminals_api.py`
- [ ] T024 [P] [US1] Editor logic tests (undo/redo depth 200, copy/paste id remap, connect rules) in `apps/web/tests/editor.test.ts`
- [ ] T025 [P] [US1] Playwright test for the import flow and save/reload in `apps/web/tests/e2e/designer.spec.ts`

### Implementation for User Story 1

- [X] T026 [P] [US1] Implement validation rules from data-model.md ("Validation rules" section) with `fix_hint` text in `packages/engine/src/liquidtwin_engine/validation.py`
- [X] T027 [P] [US1] Implement CSV bundle to TerminalDocument conversion with row/file error reporting per `contracts/csv-import.md` in `packages/engine/src/liquidtwin_engine/csv_import.py`
- [X] T028 [US1] Implement document export to JSON and CSV bundle (round-trip) in `packages/engine/src/liquidtwin_engine/export.py`
- [X] T029 [US1] Implement terminal and version routes (create, get latest or `?version`, list, append version, restore via `restore_from`) in `services/api/src/liquidtwin_api/routes/terminals.py`
- [X] T030 [US1] Implement import (JSON and multipart CSV) and export routes in `services/api/src/liquidtwin_api/routes/import_export.py`
- [X] T031 [US1] Implement validate route in `services/api/src/liquidtwin_api/routes/validate.py`
- [ ] T033 [P] [US1] Build the Pixi canvas scene with layers, pan/zoom, selection, and level-of-detail in `apps/web/src/canvas/scene.ts`
- [ ] T034 [P] [US1] Implement equipment palette and placement tools for all node types (TANK, JETTY, LOADING_POINT, RAIL_PLATFORM, RAIL_CAR, MANIFOLD, JUNCTION) in `apps/web/src/editor/palette.ts`
- [ ] T035 [US1] Implement connection tool for elements (TANK_HEADER, SEGMENT, COMMON_HEADER, LINE, PUMP, VALVE) with port snapping and orthogonal waypoints in `apps/web/src/editor/connect.ts`
- [ ] T036 [US1] Implement undo/redo command stack (depth >= 200), grouping, copy/paste with id remap in `apps/web/src/editor/history.ts`
- [ ] T037 [P] [US1] Generate property panels from the JSON Schema (typed forms, read-only computed area/volume) in `apps/web/src/editor/properties.tsx`
- [ ] T037a [P] [US1] Build the changeover matrix editor (from product, to product, gap_min, flush_factor, manual_clean_required) in `apps/web/src/editor/changeover.tsx`
- [X] T038 [P] [US1] Implement live validation list with click-to-locate in the terminal designer validation tray
- [X] T039 [P] [US1] Implement JSON file and multipart CSV bundle import from the register; shared server parser returns per-row errors and enforces all-or-nothing in `apps/web/src/App.tsx` and `services/api/src/liquidtwin_api/routes/import_export.py`
- [ ] T040 [P] [US1] Implement auto-layout for documents without coordinates using elkjs in a Web Worker in `apps/web/src/import-export/layout.worker.ts`
- [X] T041 [US1] Implement save, version history list, and restore UI in `apps/web/src/App.tsx`
- [X] T043 [US1] Implement terminal list and create/import/export/delete actions in `apps/web/src/App.tsx`

**Checkpoint**: User Story 1 works and is demonstrable on its own.

---

## Phase 4: User Story 2 - Quickest route for one operation (Priority: P1)

**Goal**: Build the graph, return a feasible shortlist with metrics and explanations, user confirms the final route.

**Independent Test**: On the sample terminal each reference job returns routes matching `lineup_cpsat.py` Stage 1; excluded pipes are named with a reason; no-route responses list blockers.

### Tests for User Story 2 (write first, must fail)

- [X] T044 [P] [US2] Hydraulics unit tests (area, velocity with installation factor, friction head, lift sign on reverse, fill minutes, flush volume/time) in `packages/engine/tests/test_hydraulics.py`
- [X] T045 [P] [US2] Graph tests (two arcs per element, pump forward-only, parallel elements kept, TANK_HEADER single-tank) in `packages/engine/tests/test_graph.py`
- [X] T046 [P] [US2] Routing tests for each filter and reason code (NOT_CERTIFIED, VELOCITY, RESIDUE, ONE_WAY_PUMP, DEDICATED_OTHER_GROUP, PUMP_HEAD, ENDPOINT_STOCK, ENDPOINT_SPACE, ENDPOINT_PRODUCT, ENDPOINT_DIRECTION), the source-equals-destination case, and no-route blockers in `packages/engine/tests/test_routing.py`
- [X] T047 [P] [US2] Property tests: excluded arcs never appear in returned routes; results deterministic across runs in `packages/engine/tests/test_routing_properties.py`
- [X] T048 [US2] Reference-oracle test: Stage 1 candidates and metrics on the sample match `tests/reference/lineup_cpsat.py` for all 4 jobs (3 to 7 candidates per job) in `tests/reference/test_stage1_oracle.py`
- [X] T049 [P] [US2] API contract tests for `POST /terminals/{id}/routes` (shortlist, exclusions, no_route) and `routes/confirm` in `services/api/tests/test_terminals_api.py`
- [ ] T050 [P] [US2] Performance benchmark: route < 1 s and graph build < 200 ms on 500 tanks / 5,000 pipes in `tests/perf/test_route_benchmark.py` with generator `tests/perf/generate_terminal.py`

### Implementation for User Story 2

- [X] T051 [P] [US2] Implement hydraulics (Darcy-Weisbach, lift, installation factor, fill and flush) mirroring `arc_data()` of the reference in `packages/engine/src/liquidtwin_engine/hydraulics.py`
- [X] T052 [US2] Implement multigraph build with forward/reverse arcs and element index in `packages/engine/src/liquidtwin_engine/graph.py`
- [X] T053 [US2] Implement per-job arc filtering with reason codes (certification, velocity, residue, one-way pump, dedication) in `packages/engine/src/liquidtwin_engine/routing.py`
- [X] T054 [US2] Implement endpoint filtering using current stored stock (FR-011: source stock >= volume, destination free space >= volume, product compatible; tank `allow_inbound`/`allow_outbound`/`allow_simultaneous` respected, reason `ENDPOINT_DIRECTION`) in `packages/engine/src/liquidtwin_engine/routing.py`
- [X] T055 [US2] Implement k-shortest simple paths (K=20, stable tie-break by element id), expansion of parallel elements, pump head budget check in `packages/engine/src/liquidtwin_engine/routing.py`
- [X] T056 [US2] Implement route metrics (fill, transfer, flush time and volume, valves, common headers, head margin, max velocity) and shortlist ordering: total time, then flush volume, valve count, shared-header use (FR-013) in `packages/engine/src/liquidtwin_engine/routing.py`
- [X] T057 [US2] Implement no-route explanation (cheapest blocked path and its blockers) in `packages/engine/src/liquidtwin_engine/explain.py`
- [X] T058 [US2] Implement `POST /terminals/{id}/routes` including `terminal_version` and `engine_version` in the response in `services/api/src/liquidtwin_api/routes/routing.py`
- [X] T059 [US2] Implement `POST /terminals/{id}/routes/confirm` storing the user-selected route (FR-023) in `services/api/src/liquidtwin_api/routes/routing.py`
- [X] T060 [P] [US2] Build the route request form (source, destination, product, volume, rate, window, direction) in `apps/web/src/App.tsx`
- [X] T061 [P] [US2] Build the shortlist and metrics panel with a confirm button when more than one route remains in `apps/web/src/App.tsx`
- [X] T062 [P] [US2] Build the explanation panel (exclusions by reason, no-route blockers with element focus) in `apps/web/src/App.tsx`
- [X] T063 [US2] Implement route highlight overlay and alternative preview on the layout and graph views in `apps/web/src/App.tsx` and `apps/web/src/styles.css`
- [ ] T064 [US2] Add Playwright flow: request route, see explanation for an uncertified pipe, confirm a route in `apps/web/tests/e2e/planner.spec.ts`

**Checkpoint**: User Stories 1 and 2 both work; core MVP value delivered.

---

## Phase 5: User Story 3 - Keep equipment availability current (Priority: P2)

**Goal**: Availability windows from UI and external feed change routing and flag outdated results.

**Independent Test**: Mark a pipe unavailable for a window; the route changes inside the window and returns after it.

### Tests for User Story 3 (write first, must fail)

- [X] T065 [P] [US3] Engine tests for window overlap against job window and UNAVAILABLE reason code in `packages/engine/tests/test_availability.py`
- [X] T066 [P] [US3] API tests for availability upsert idempotency (element_id+source+external_ref), unknown elements reported not fatal, list filters, delete, max 5000 items in `services/api/tests/test_terminals_api.py`
- [ ] T067 [P] [US3] Playwright test for marking maintenance and re-requesting a route in `apps/web/tests/e2e/availability.spec.ts`

### Implementation for User Story 3

- [ ] T068 [US3] Implement availability overlay on the graph (incremental flagging, < 20 ms) in `packages/engine/src/liquidtwin_engine/graph.py`
- [X] T069 [US3] Apply availability windows in arc filtering for the job window (FR-010, FR-016) in `packages/engine/src/liquidtwin_engine/routing.py`
- [X] T070 [US3] Implement availability routes (list, upsert, delete) in `services/api/src/liquidtwin_api/routes/availability.py`
- [X] T071 [US3] Mark ConfirmedRoute records outdated when an overlapping window changes in `services/api/src/liquidtwin_api/routes/availability.py`
- [X] T072 [P] [US3] Build the manual availability editor, scheduled-window list, and graph status overlay in `apps/web/src/App.tsx` and `apps/web/src/styles.css`
- [X] T073 [US3] Show outdated status for confirmed routes in `apps/web/src/App.tsx`
- [X] T074 [US3] Parse and persist availability.csv rows during CSV import in `packages/engine/src/liquidtwin_engine/csv_import.py` and `services/api/src/liquidtwin_api/routes/import_export.py`

**Checkpoint**: Availability changes route results end to end.

---

## Phase 6: User Story 4 - Use it on a phone or tablet (Priority: P2)

**Goal**: Smooth touch use and responsive layouts; phone workflow centered on view, route request, explanation.

**Independent Test**: On a Pixel 5 viewport open the 500-tank terminal, pan/zoom smoothly, request a route.

### Tests for User Story 4 (write first, must fail)

- [ ] T075 [P] [US4] Playwright mobile-viewport test (Pixel 5): pan/zoom gestures and route request in `apps/web/tests/e2e/mobile.spec.ts`
- [ ] T076 [P] [US4] Frame-rate benchmark on the generated large terminal (>= 30 fps target, SC-007; Pixel 5 profile with 4x CPU throttle, plus one manual real-device check) in `apps/web/tests/perf/fps.spec.ts`

### Implementation for User Story 4

- [ ] T077 [US4] Implement pointer-event gestures (one-finger pan, pinch zoom, tap select, long-press palette) in `apps/web/src/canvas/gestures.ts`
- [ ] T078 [P] [US4] Implement responsive layout with bottom-sheet panels below 768 px in `apps/web/src/pages/layout.tsx`
- [ ] T079 [P] [US4] Tune rendering for large terminals (batching, culling, LOD thresholds) in `apps/web/src/canvas/scene.ts`
- [ ] T080 [P] [US4] Configure PWA install, caching of the app shell, offline view of last-loaded terminal in `apps/web/vite.config.ts`

**Checkpoint**: All four stories work independently.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T081 [P] Update `docs/05-System-Architecture.md`, `docs/08-Graph-Engine.md`, `docs/09-Routing-Engine.md` for route confirmation and Stage 1 pipeline decisions
- [ ] T082 [P] Add structured logging and OpenTelemetry tracing to API and engine calls in `services/api/src/liquidtwin_api/main.py`
- [ ] T083 Security pass: input size limits, CSV/JSON parser limits, error messages without internals, deploy note that the app is trusted-network only until OIDC (plan Complexity Tracking) in `services/api/src/liquidtwin_api/main.py` and `README.md`
- [ ] T084 Run all quickstart.md scenarios and record results in `specs/001-terminal-designer-routing/quickstart.md`
- [ ] T085 [P] Add Dockerfiles for api and web, and a production compose file in `docker-compose.prod.yml`

---

## Phase 8: Graph Projection and Designer View (Completed)

**Purpose**: Expose the canonical engine graph for inspection and render that same topology in the designer.

- [X] T086 [P] [US2] Add graph API tests for directed arcs, parallel elements, structural errors, and retained non-structural issues in `services/api/tests/test_terminals_api.py`
- [X] T087 [US2] Expose a versioned graph projection using the shared `build_graph` model in `services/api/src/liquidtwin_api/routes/graph.py`
- [X] T088 [US2] Block reverse pump traversal even when head is zero and cover it in `packages/engine/src/liquidtwin_engine/routing.py` and `packages/engine/tests/test_routing.py`
- [X] T089 [US2] Add the responsive Layout/Graph view with direction and validation status in `apps/web/src/App.tsx` and `apps/web/src/styles.css`
- [X] T090 [US2] Regenerate and consume the typed graph API contract in `apps/web/src/api/client.ts` and `apps/web/src/api/terminals.ts`
- [X] T091 [US3] Overlay active/upcoming element availability states on the Graph view in `apps/web/src/App.tsx` and `apps/web/src/styles.css`

---

## Dependencies & Execution Order

- Phase 1 has no dependencies. Phase 2 depends on Phase 1 and blocks all stories.
- US1 depends only on Phase 2. US2 depends on Phase 2 (including the repository T017a) and on `document.py` (T013); it can start in parallel with US1 for engine work (T044 to T057), while its UI (T060 to T064) needs the canvas from US1 (T033).
- US3 depends on US2 routing (T053 to T056). US4 depends on the canvas from US1 (T033) and the planner UI from US2.
- Within a story: tests first (must fail), then engine, then API, then UI.

```text
Setup -> Foundational -> US1 --\
                    \-> US2 ----> US3
                         \------> US4 (needs US1 canvas + US2 planner)
                                    \-> Polish
```

## Parallel Examples

- **Foundational**: T011, T012, T018, T019 together after T009.
- **US1 tests**: T020 to T025 together; **US1 engine**: T026 and T027 together; **US1 UI**: T033, T034, T037, T038, T039, T040 together.
- **US2 tests**: T044 to T047, T049, T050 together; UI: T060, T061, T062 together.

## Implementation Strategy

- **MVP**: Phases 1, 2, 3 and 4 (US1 + US2). Validate with quickstart scenarios 1 to 3 and the oracle test (T048) before moving on.
- **Incremental**: add US3, then US4, then Polish; each is independently demonstrable.
- **Gates**: constitution III (oracle) must be green before US2 is considered done; performance benchmarks (T050, T076) gate release of this feature.

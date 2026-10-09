# Tasks: Advanced Pump Hydraulics

**Input**: Design documents in `specs/002-advanced-hydraulics/`
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/pump-hydraulics.md`, `quickstart.md`
**Tests**: Required by Constitution IV; engine tests are written and observed failing before engine changes.

## Format
- `[P]` means parallelizable work in different files with no incomplete dependency.
- `[US1]`, `[US2]`, and `[US3]` map to the feature spec's stories.

## Phase 1: Setup and Schema Compatibility

- [X] T001 Verify the existing codegen environment and extend `packages/schema/codegen.sh` to generate both API and engine Pydantic models
- [X] T002 [P] Add schema compatibility tests proving schema 1.0 documents parse unchanged and schema 1.1 pump fields round-trip in `packages/engine/tests/test_document_versions.py`
- [X] T003 [P] Add generated-model contract checks for schema 1.1 through `services/api/tests/test_terminals_api.py` and frontend TypeScript build
- [X] T004 Bump the terminal document schema to accept versions `1.0` and `1.1`, add optional pump curve/suction-requirement/train fields, preserve all existing defaults, and sync the feature-001 schema contract in `packages/schema/terminal-document.schema.json` and `specs/001-terminal-designer-routing/contracts/terminal-document.schema.json`
- [X] T005 Regenerate TypeScript and API/engine Pydantic models with `packages/schema/codegen.sh`; make drift checking include `packages/engine/src/liquidtwin_engine/schema_models.py`
- [X] T006 Update the API schema model and shared engine parser to accept both versions in `services/api/src/liquidtwin_api/schemas/terminal_document.py`, `packages/engine/src/liquidtwin_engine/schema_models.py`, and `packages/engine/src/liquidtwin_engine/document.py`

## Phase 2: User Story 1 - Define Pump Performance (P1)

**Goal**: Store, validate, import/export, and edit curve-based pump data without changing legacy constant-head terminals.
**Independent test**: A valid quadratic and tabular curve round-trip; malformed or out-of-range samples produce field-level validation errors; schema 1.0 oracle fixtures remain unchanged.

- [X] T007 [P] [US1] Write failing tests for quadratic/tabular curve boundaries, monotonic tabular points, duplicate flow samples, invalid head, and missing fields in `packages/engine/tests/test_pump_curves.py`
- [X] T008 [P] [US1] Write failing CSV import/export round-trip tests for pump curve, suction, speed-range, and train fields in `packages/engine/tests/test_csv_import.py`
- [X] T009 [US1] Add normalized curve/suction/train fields to the engine `Element` and terminal dataclasses while retaining legacy `head_m` in `packages/engine/src/liquidtwin_engine/document.py`
- [X] T010 [US1] Validate curve mode, quadratic coefficients, tabular point count/order/range, suction inputs, speed bounds, and pump-train member references in `packages/engine/src/liquidtwin_engine/validation.py`
- [X] T011 [US1] Extend the `elements.csv` field map and preserve schema version 1.0/1.1 during import in `packages/engine/src/liquidtwin_engine/csv_import.py`
- [X] T012 [US1] Export new curve/suction/train fields to CSV without dropping legacy fields in `packages/engine/src/liquidtwin_engine/export.py`
- [X] T013 [US1] Add schema-driven pump performance, suction, speed, and train editing controls to the designer inspector in `apps/web/src/App.tsx`

## Phase 3: User Story 2 - Check Operating Point and Suction Margin (P1)

**Goal**: Reject physically infeasible pump routes and report achieved operating conditions.
**Independent test**: A known pump/system intersection meets the requested minimum rate; no-intersection, out-of-range, speed, and suction cases return named reason codes; all schema 1.0 oracle results remain unchanged.

- [X] T014 [P] [US2] Write failing reference-point tests for curve interpolation, quadratic evaluation, intersection boundaries, multiple roots, and determinism in `packages/engine/tests/test_hydraulics.py` and `packages/engine/tests/test_pump_curves.py`
- [X] T015 [P] [US2] Write failing route tests for achieved minimum-rate acceptance, no operating point, range violations, VFD limits, per-pump available suction input, and reverse-pump exclusion in `packages/engine/tests/test_routing.py`
- [X] T016 [US2] Implement deterministic in-range quadratic and piecewise-linear tabular pump curve evaluation in `packages/engine/src/liquidtwin_engine/hydraulics.py`
- [X] T017 [US2] Implement bounded operating-point search against route system-head curves with no extrapolation and stable root selection in `packages/engine/src/liquidtwin_engine/hydraulics.py`
- [X] T018 [US2] Add explicit pump curve/speed/suction exclusion codes and pump-specific explanation details in `packages/engine/src/liquidtwin_engine/types.py` and `packages/engine/src/liquidtwin_engine/explain.py`
- [X] T019 [US2] Integrate achieved minimum-flow, pump head, system head, speed, and NPSH margin checks into route feasibility while keeping the schema 1.0 constant-head branch unchanged in `packages/engine/src/liquidtwin_engine/routing.py`
- [X] T020 [US2] Extend route request, route metrics, exclusion enums, OpenAPI contract, and generated client with per-pump `pump_suction_inputs` and operating-point details in `packages/engine/src/liquidtwin_engine/types.py`, `specs/001-terminal-designer-routing/contracts/openapi.yaml`, `specs/002-advanced-hydraulics/contracts/pump-hydraulics.md`, and generated API types
- [X] T021 [US2] Add API regression tests for curve-mode route request inputs, operating metrics, and pump-specific exclusions in `services/api/tests/test_terminals_api.py`
- [X] T022 [US2] Let planners enter operation-specific available suction per curve-based pump and show achieved operating flow, head margin, suction margin, and pump exclusions in `apps/web/src/App.tsx`

## Phase 4: User Story 3 - Evaluate Pump Trains and VFD (P2)

**Goal**: Evaluate series/parallel pump combinations and choose only permitted speed settings.
**Independent test**: Series/parallel combinations and VFD boundary cases match independently calculated points within 1% and respect every member pump limit.

- [X] T023 [P] [US3] Write failing reference tests for series head addition, parallel flow addition, unequal curves, and VFD affinity scaling in `packages/engine/tests/test_pump_curves.py`
- [X] T024 [US3] Implement series and parallel combined curves with member operating-range enforcement in `packages/engine/src/liquidtwin_engine/hydraulics.py`
- [X] T025 [US3] Select a deterministic allowed speed ratio that meets the requested minimum flow and route head in `packages/engine/src/liquidtwin_engine/hydraulics.py`
- [X] T026 [US3] Integrate train operating points and per-member suction checks into route metrics and explanations in `packages/engine/src/liquidtwin_engine/routing.py`
- [X] T027 [US3] Add pump-train editor controls and member validation feedback in `apps/web/src/App.tsx`

## Phase 5: Polish and Compatibility Gates

- [X] T028 [P] Add a schema 1.1 curve-mode sample and oracle-style hydraulic expectations in `tests/reference/test_pump_curve_oracle.py` and `tests/reference/pump-curve-terminal.json`
- [X] T029 Run the complete feature-001 Stage 1 oracle suite unchanged and record schema 1.0 compatibility results in `specs/002-advanced-hydraulics/quickstart.md`
- [X] T030 Update `docs/10-Hydraulics-Engine.md` and `docs/06-Domain-Model.md` with curve, suction, VFD, pump-train, and schema-version behavior
- [X] T031 Run schema codegen checks, engine/API tests, frontend tests, Ruff, mypy, ESLint, and Prettier; record command results in `specs/002-advanced-hydraulics/quickstart.md`
- [X] T032 Add a large-terminal curve benchmark only after a 500-tank/5,000-pipe fixture generator exists; otherwise keep feature-001 performance gates explicitly open in `specs/002-advanced-hydraulics/quickstart.md`

## Dependencies and Execution Order
- T001-T006 establish schema/version compatibility before any curve behavior is implemented.
- US1 validation/import/export fields (T007-T013) precede curve-mode routing in US2.
- US2 operating points (T014-T022) precede explicit trains/VFD integration in US3.
- T028-T032 are release/compatibility gates; the feature-001 constant-head oracle must pass before feature 002 is considered complete.

## Implementation Strategy
- Land schema 1.1 as additive, then verify schema 1.0 before changing engine behavior.
- Complete US1 curve data/validation first, US2 single-pump operating points second, and US3 trains/VFD last.
- Do not begin Stage 2 optimizer work until feature 002 preserves the Stage 1 oracle and emits deterministic curve-mode route metrics.

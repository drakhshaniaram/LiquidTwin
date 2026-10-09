# Quickstart: Validate Terminal Designer and Quickest-Route Planner

Run these after implementation to prove the feature end to end. Interfaces: [contracts/openapi.yaml](contracts/openapi.yaml), [contracts/terminal-document.schema.json](contracts/terminal-document.schema.json), [contracts/csv-import.md](contracts/csv-import.md). Entities: [data-model.md](data-model.md).

## Prerequisites
- Python 3.12, Node 20.19+ (or 22.12+ / 24+), Docker (for PostgreSQL 16)
- Reference script `lineup_cpsat.py` available at `tests/reference/` (copy of the original; used only as an oracle)

## Setup
1. Start the database: `docker compose up -d db`
2. Backend: `cd services/api; pip install -e ../../packages/engine -e .[dev]; alembic upgrade head; uvicorn liquidtwin_api.main:app --port 8000`
3. Frontend: `cd apps/web; npm install; npm run dev` (opens on port 5173)
4. Schema codegen check: `cd packages/schema; npm ci; npm run schema:check` (fails if generated TS/Pydantic types drift from the JSON Schema)

## Automated validation
| Command | Proves |
|---|---|
| `pytest packages/engine` | graph, hydraulics, routing, validation unit and property tests |
| `pytest tests/reference` | Stage 1 routes and metrics on the sample terminal match `lineup_cpsat.py` (SC-004) |
| `pytest services/api` | API contract tests against `openapi.yaml`, import all-or-nothing |
| `pytest tests/reference -k import_equivalence` | JSON and CSV import give identical documents (SC-005) |
| `npm test --prefix apps/web` | editor logic, undo/redo, CSV parsing |
| `npx playwright test` (desktop + Pixel 5 viewport) | Stories 1 to 4 flows, touch pan/zoom |
| `pytest tests/perf -m benchmark` | route < 1 s and graph build < 200 ms on the 500-tank terminal (SC-003) |

## Manual scenarios
1. **Import (Story 1)**: Import `tests/reference/sample-terminal.json`, then the CSV bundle in `tests/reference/csv/`. Expect identical terminals and no ERROR validation issues.
2. **Route (Story 2)**: Request product P1, volume 4000, rate 1000 from Jetty1 (node 1) to tank node 7 or 9. Expect the reference route highlighted with metrics; alternatives ranked below.
3. **Explanation (Story 2)**: Request a product not certified on a header. Expect the route to avoid it and the explanation to name the header with reason `NOT_CERTIFIED`.
4. **Availability (Story 3)**: `POST /terminals/{id}/availability` marking the common header in maintenance for the job window, request again. Expect a different route, or `no_route` naming that header. After the window, expect the original route.
5. **Mobile (Story 4)**: Open the large synthetic terminal (`tests/perf/generate_terminal.py --tanks 500 --pipes 5000`) on a phone or emulated Pixel 5; pan and zoom stay smooth, request a route and read the explanation.

## Manual usability checks
- SC-001: import the sample terminal from a file and have it ready for routing in under 1 minute.
- SC-002: from opening a terminal, request and read a route in under 30 seconds.
- SC-007: pan and zoom the 500-tank terminal on one real mid-range phone (Pixel 5 class); expect at least 30 fps.
- SC-008: five planners request a route on a phone; at least 90% succeed on the first attempt.

## Expected outcomes
All automated checks pass; manual scenarios match the acceptance scenarios in [spec.md](spec.md).

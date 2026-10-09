# Quickstart: Advanced Pump Hydraulics

Run from repository root after implementation. This feature depends on feature 001's terminal schema, route engine, and reference oracle.

## Prerequisites
- Python 3.12 and Node 20.19+ (or 22.12+ / 24+)
- Install API and engine development dependencies from `services/api/` and `packages/engine/`

## Automated checks
| Command | Proves |
|---|---|
| `python -m pytest packages/engine/tests/test_hydraulics.py packages/engine/tests/test_pump_curves.py` | Curve evaluation, system-curve intersection, VFD, train aggregation, and suction limits |
| `python -m pytest packages/engine/tests/test_validation.py packages/engine/tests/test_csv_import.py` | Schema 1.0/1.1 compatibility and curve import validation |
| `python -m pytest tests/reference/test_stage1_oracle.py` | Legacy constant-head reference behavior is unchanged |
| `python -m pytest tests/reference/test_pump_curve_oracle.py` | Curve-mode reference points and route feasibility |
| `bash packages/schema/codegen.sh --check` | Generated TypeScript/Pydantic models match the versioned JSON Schema |
| `ruff check packages/engine services/api` | Python lint |
| `python -m mypy packages/engine/src services/api/src` | Engine/API types |

## Manual scenarios
1. Create a schema 1.1 pump with a tabulated curve; validate it and request a route at an in-range minimum flow. Confirm achieved flow, pump/system head, and transfer duration are shown.
2. Request a rate beyond the curve range. Confirm no extrapolation and a `PUMP_FLOW_OUT_OF_RANGE` explanation naming the pump.
3. Use a system curve with a known intersection. Confirm the operating point is within 1% of the independent reference calculation.
4. Send per-pump `pump_suction_inputs` with available suction below `npsh_required_m + npsh_margin_m`. Confirm the route is rejected with `PUMP_SUCTION_MARGIN` and the pump ID.
5. Evaluate series and parallel train fixtures at known points and at the VFD speed boundaries; confirm route feasibility and limits.
6. Run all feature-001 schema 1.0 reference jobs and confirm their route candidates and metrics remain unchanged.

## Release gates
- No schema 1.0 document changes meaning or fails to parse.
- All accepted curve-mode routes meet requested minimum rate, pump/system head, speed, and suction constraints.
- Existing reference-oracle tests remain green; added curve tests use independent closed-form or tabular reference points.
- Route latency remains below the feature-001 1-second budget on the large fixture when it exists.

## Verified results (2026-10-09)
- `python -m pytest packages/engine/tests services/api/tests tests/reference`: 100 passed, including all five Stage 1 oracle cases and the quadratic curve route oracle.
- `npm test --prefix apps/web -- --run`: 3 passed.
- `npm run build --prefix apps/web` and `npm run lint --prefix apps/web`: passed.
- `ruff check packages/engine services/api`: passed.
- Targeted mypy with `--ignore-missing-imports` on the changed engine/API modules: passed. Without that option, this environment lacks NetworkX and local API package stubs.
- Schema codegen drift check: passed; OpenAPI TypeScript client regenerated and the web build passed.
- The two existing header validation tests initially exposed a misplaced loop during train validation; both now pass in the full suite.
- No 500-tank/5,000-pipe benchmark fixture generator is present. The performance budget remains open and no large-terminal performance claim is made.

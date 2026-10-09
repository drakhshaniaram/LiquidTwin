# Quickstart: Multi-Job Terminal Optimization

## Prerequisites

- Python 3.12 and Node 20.19+ (or 22.12+ / 24+)
- OR-Tools installed in the engine/API environment
- A valid terminal with Stage 1 route candidates for each submitted job

## Automated checks

| Command | Proves |
|---|---|
| `python -m pytest packages/engine/tests/test_optimization.py` | Route choice, maintenance, changeover, tank budgets, objective, time-limit status, and determinism |
| `python -m pytest tests/reference/test_multi_job_optimization_oracle.py` | Four-job output is OPTIMAL, objective 1327, all jobs on time |
| `python -m pytest services/api/tests/test_optimization_api.py` | Request validation, NO_ROUTE, infeasibility details, result serialization |
| `npm test --prefix apps/web -- --run` | Scenario and result UI behavior |
| `npm run build --prefix apps/web` | TypeScript and production bundle |

## Manual scenario

1. Open Route Planner and select a terminal.
2. Add the four jobs from `tests/reference/lineup_cpsat.py`, using the same horizon origin and due/ETA offsets.
3. Prepare the scenario and verify that each job shows candidate routes or its blockers.
4. Optimize. Expected reference result: OPTIMAL, objective 1327, four jobs on time.
5. Open a scheduled job to inspect its selected route and highlight it in the terminal graph.
6. Add a shared-equipment maintenance window or competing job and verify non-overlap/changeover; remove the only candidate route and verify a named NO_ROUTE job.

## Release gates

- The reference scenario matches the behavioral oracle at objective 1327 and all jobs on time.
- No schedule uses a non-Stage-1 route or violates an element, maintenance, inventory, or changeover constraint.
- Repeated runs with identical inputs/seed produce identical status, objective, and schedule.
- Time-limited incumbents are labeled FEASIBLE, never OPTIMAL.
- A time limit with no incumbent is labeled UNKNOWN, never INFEASIBLE or FEASIBLE.
- The four-job oracle completes within 30 seconds; larger scenarios use per-element interval/sequence constraints.

## Verified results (2026-10-09)

- `python -m pytest packages/engine/tests services/api/tests tests/reference`: 112 passed, including five Stage 1 oracle cases and the new Stage 2 objective-1327 oracle.
- The 40-job per-element interval regression found an OPTIMAL or FEASIBLE schedule within its configured five-second solve limit and below the 30-second acceptance bound.
- A maintenance interval ending exactly at the horizon start is treated as expired and does not block the schedule.
- `npm test --prefix apps/web -- --run`: 3 passed; `npm run build --prefix apps/web`: passed; `npm run lint --prefix apps/web`: passed; Prettier check on modified frontend files: passed.
- `ruff check packages/engine services/api`: passed; targeted mypy on optimization engine/API modules with `--ignore-missing-imports`: passed.
- `bash -c 'PYTHON=.venv/Scripts/python.exe ./packages/schema/codegen.sh --check'`: passed; OpenAPI client regeneration and production build passed.
- Browser verification on the source-matched preview prepared a route, ran the optimizer, rendered OPTIMAL status/objective/bound/KPIs, and showed the selected route and element timeline. Browser console had no errors.
- The reference Stage 1 suite remains unchanged and passes. Scenarios/results are request-scoped; no database tables were added.
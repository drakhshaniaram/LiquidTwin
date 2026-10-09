# Feature Specification: Multi-Job Terminal Optimization

**Feature Branch**: `003-multi-job-optimization`

**Created**: 2026-10-09

**Status**: Draft

**Input**: Roadmap Phase 5 and `docs/11-Optimization-Engine.md`: schedule multiple terminal operations together using feasible Stage 1 routes, shared-equipment availability, changeovers, tank stock/ullage, and an explainable objective. The reference scenario targets OPTIMAL with objective 1327 and all four jobs on time.

## Dependencies

- Feature 001 must provide versioned terminal documents, single-job feasible route candidates, equipment availability, and route metrics.
- Advanced pump hydraulics from feature 002 may refine route feasibility and metrics but is not required to define the initial multi-job scheduling behavior.

## User Scenarios & Testing

### User Story 1 - Prepare a set of terminal jobs (Priority: P1)

A planner enters or imports several inbound, outbound, or transfer jobs with endpoints, product, volume, rate, earliest start, and requested completion time, then reviews which jobs have at least one feasible route.

**Why this priority**: Optimization is only useful when it operates on an explicit and validated job set.

**Independent Test**: Load the four reference jobs, verify each has route candidates, and verify a job with no Stage 1 path is identified before scheduling.

**Acceptance Scenarios**:

1. **Given** a valid job set, **When** the planner prepares it, **Then** each job is associated with its feasible route candidates and terminal version.
2. **Given** a job with no feasible route, **When** the job set is prepared, **Then** the job is reported with its route blockers and is not silently omitted.

---

### User Story 2 - Optimize a terminal lineup (Priority: P1)

A planner runs an optimization over the prepared jobs and receives a schedule with selected routes, start/end times, lateness, and an overall objective.

**Why this priority**: The product value of Stage 2 is coordinating jobs that compete for pumps, pipes, tanks, and headers rather than planning each job independently.

**Independent Test**: Run the reference scenario and verify OPTIMAL status, objective 1327, and all four jobs on time.

**Acceptance Scenarios**:

1. **Given** jobs with feasible routes, **When** the planner optimizes them, **Then** every scheduled job uses one feasible route and has a start/end time within the planning horizon.
2. **Given** two jobs share exclusive equipment, **When** they are scheduled, **Then** their use does not overlap and the required product changeover gap is respected.
3. **Given** maintenance windows or limited tank stock/space, **When** jobs are scheduled, **Then** the resulting timeline respects those windows and aggregate tank limits.
4. **Given** competing schedules, **When** the objective is applied, **Then** waiting, lateness, flushing, valve use, and shared-header use are reflected in the configured ranking.

---

### User Story 3 - Understand and inspect a plan (Priority: P2)

A planner reviews the solver status, objective, bound, job timeline, selected routes, and reasons a job set could not be scheduled, then inspects the plan on the terminal graph.

**Why this priority**: Operators need enough evidence to trust, communicate, and act on an optimized schedule.

**Independent Test**: Inspect an optimal reference plan and a deliberately infeasible set; verify the timeline, metrics, and named conflict explanation.

**Acceptance Scenarios**:

1. **Given** an optimal or feasible result, **When** the planner opens it, **Then** each job's route and timing are shown with the objective and solver status.
2. **Given** an infeasible result, **When** the planner inspects it, **Then** the app names the conflicting jobs or equipment where the solver can identify them and never presents an infeasible plan as valid.
3. **Given** a plan result, **When** the planner selects a job, **Then** its route is highlighted on the terminal graph.

### Edge Cases

- A job has no feasible route before optimization begins.
- Jobs have identical start windows and compete for one exclusive element.
- A changeover rule is missing, requires manual cleaning, or has a zero gap.
- Aggregate source stock or destination ullage is insufficient for the full job set.
- The solver reaches its time limit with an incumbent but no proof of optimality.
- No feasible schedule exists within the horizon.
- The same input and solver configuration are rerun for deterministic regression.

## Requirements

### Functional Requirements

- **FR-001**: Each optimization job MUST include an identity, direction, source and destination, product, volume, transfer rate, earliest start, requested completion time, and terminal version.
- **FR-002**: The optimizer MUST consume feasible Stage 1 route candidates; it MUST report jobs with no candidates and their blockers rather than dropping them.
- **FR-003**: The optimizer MUST select exactly one feasible route for each scheduled job.
- **FR-004**: Each job MUST have a start and end time within the configured planning horizon and a reported lateness value.
- **FR-005**: Jobs MUST NOT overlap on exclusive elements; required product changeover time MUST be respected between consecutive uses.
- **FR-006**: The schedule MUST respect equipment maintenance windows and aggregate tank source stock and destination ullage limits.
- **FR-007**: The objective MUST include configurable weights for job waiting, lateness, flush volume, valve count, and shared-header use.
- **FR-008**: Results MUST identify solver status (OPTIMAL, FEASIBLE, INFEASIBLE, NO_ROUTE, or UNKNOWN), objective/bound when available, per-job route/times, KPIs, and an element timeline.
- **FR-009**: A time-limited feasible incumbent MUST be distinguishable from a proven optimum; a time limit without an incumbent MUST be reported as UNKNOWN, and no incomplete result may be represented as optimal.
- **FR-010**: When a job set is infeasible, the system MUST provide the most specific available explanation, mapped to jobs and/or conflicting elements.
- **FR-011**: Identical terminal, jobs, availability, solver parameters, and random seed MUST produce reproducible results.
- **FR-012**: For scale beyond dozens of jobs, the scheduler MUST avoid pairwise job-by-route conflict models and use per-element interval/cumulative constraints.
- **FR-013**: The reference four-job scenario MUST remain regression-compatible with the established Stage 2 oracle.

### Key Entities

- **OptimizationJob**: operation request plus earliest start, requested completion, and candidate routes.
- **OptimizationScenario**: terminal version, job set, horizon, objective weights, seed, and time limit.
- **ScheduledJob**: selected route, start/end, lateness, and status.
- **OptimizationResult**: solver status, objective, bound, KPIs, explanations, and per-element timeline.
- **ElementUseInterval**: scheduled interval for one job's use of an exclusive element, including changeover separation.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The four-job reference scenario returns OPTIMAL with objective 1327 and all jobs on time in 100% of regression runs.
- **SC-002**: Every scheduled job uses one Stage 1 feasible route, and no scheduled pair violates an exclusive element or changeover constraint in 100% of tests.
- **SC-003**: Infeasible job sets are reported as INFEASIBLE or NO_ROUTE; runs without an incumbent are UNKNOWN; neither is shown as a feasible schedule.
- **SC-004**: Repeated reference runs with the same seed and inputs produce identical status, objective, and schedule.
- **SC-005**: The reference scenario completes within the configured 30-second solver limit.

## Assumptions

- Feature 001's Stage 1 route service and availability API are the source of per-job route candidates and blockers.
- The first version uses aggregate tank stock/ullage constraints; time-indexed inventory and dynamic residue sequencing are a later extension unless research proves them necessary for the reference acceptance case.
- Shared route elements are exclusive during scheduled use, with product-pair changeover gaps from the terminal document.
- Solver configuration defaults to a 30-second limit and a fixed seed for reproducible reference validation; planning horizon and objective weights are scenario inputs.
- The established `lineup_cpsat.py` output is the behavioral oracle for the four-job reference scenario.

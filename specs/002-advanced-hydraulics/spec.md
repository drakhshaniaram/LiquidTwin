# Feature Specification: Advanced Pump Hydraulics

**Feature Branch**: `002-advanced-hydraulics`

**Created**: 2026-10-09

**Status**: Draft

**Input**: Roadmap Phase 4 and `docs/10-Hydraulics-Engine.md`: add pump performance curves, operating-point and suction-limit checks, variable-speed operation, and multi-pump arrangements while preserving the Phase 1-3 constant-head behavior.

## User Scenarios & Testing

### User Story 1 - Define pump performance (Priority: P1)

A terminal engineer records the performance envelope of an installed pump so that a route can be evaluated at the requested flow instead of assuming the pump supplies constant head at every rate.

**Why this priority**: Route feasibility depends on available pump head at the requested operating condition.

**Independent Test**: Enter a pump curve with known points, request head at an in-range flow, and compare with the expected curve value. Confirm an out-of-range flow is rejected with the pump named.

**Acceptance Scenarios**:

1. **Given** a pump with a valid performance curve, **When** an engineer saves it, **Then** the curve and operating limits are retained in the terminal version.
2. **Given** a requested flow outside the curve's declared range, **When** a route is evaluated, **Then** the pump is excluded with a specific out-of-range explanation and no extrapolated head is assumed.

---

### User Story 2 - Check the operating point and suction margin (Priority: P1)

A planner requests a route and sees whether the selected pumps can meet the route's system head at the job flow while maintaining the required suction margin.

**Why this priority**: A route that exceeds the pump curve or suction limit is not physically feasible even if the legacy constant-head calculation passes.

**Independent Test**: Use a pump/system pair with a known intersection and a second case with insufficient available suction head; verify the operating point and the named exclusion reason.

**Acceptance Scenarios**:

1. **Given** a pump curve intersecting the route system curve within its operating range, **When** the route is evaluated, **Then** the operating flow and head margin are reported.
2. **Given** available suction head below the pump's required suction head plus the configured margin, **When** the route is evaluated, **Then** the route is rejected and identifies the limiting pump.
3. **Given** an invalid or incomplete curve, **When** the terminal is validated, **Then** the curve is rejected with a field-level issue and cannot be used for routing.

---

### User Story 3 - Evaluate pump trains and variable speed (Priority: P2)

A planner evaluates pumps operating in series or parallel, including an allowed variable-speed range, and receives a feasible combined operating point.

**Why this priority**: Terminals often use pump trains; representing their combined envelope avoids overstating or understating available capacity.

**Independent Test**: Compare series and parallel combinations against hand-calculated reference points, including minimum and maximum permitted speed.

**Acceptance Scenarios**:

1. **Given** compatible pumps in series, **When** a route is evaluated, **Then** their head contributions are combined at the same flow.
2. **Given** compatible pumps in parallel, **When** a route is evaluated, **Then** the combined flow is evaluated at a common head without exceeding individual operating limits.
3. **Given** a variable-speed pump, **When** the requested operating point requires a speed outside the configured range, **Then** the route is rejected with the pump and limiting range named.

### Edge Cases

- A curve has duplicate or decreasing flow samples, negative head, or no valid operating interval.
- A requested rate lies exactly at a declared curve endpoint.
- The pump curve and system curve have no intersection or more than one possible intersection in the declared range.
- A pump is traversed in reverse; one-way direction remains enforced regardless of available head.
- Required suction data is missing or becomes invalid for the requested job.
- A legacy constant-head pump is used with a scenario that does not provide curve data.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST store a pump performance curve and its valid flow range for each curve-based pump.
- **FR-002**: A pump curve MUST be representable as a quadratic curve or as ordered flow/head samples, and validation MUST reject malformed, duplicate-flow, or physically invalid samples.
- **FR-003**: The system MUST evaluate pump head at the requested operating flow and MUST NOT extrapolate outside the declared curve range.
- **FR-004**: The system MUST determine whether a valid operating point exists between the pump/system curves and report the resulting operating flow and head margin.
- **FR-005**: The system MUST accept an operation-specific available suction head for each curve-based pump, compare it with that pump's required suction head plus configured margin, and identify the limiting pump when infeasible. A curve-based pump without an available-suction input MUST be rejected rather than assumed safe.
- **FR-006**: The system MUST support pumps arranged in series or parallel and MUST calculate a combined operating envelope without violating any member pump's limits.
- **FR-007**: The system MUST support a declared variable-speed range and reject operating points that require speed outside that range.
- **FR-008**: Reverse pump traversal MUST remain prohibited, independent of curve head.
- **FR-009**: Existing constant-head pump documents MUST remain readable and MUST preserve their current reference-oracle route results when curve mode is not selected.
- **FR-010**: Hydraulic exclusions MUST include machine-readable reason codes and human-readable text naming the pump and the failed condition.
- **FR-011**: The requested job rate MUST be treated as the minimum required flow; a route is feasible only when its calculated operating point meets or exceeds that rate, and transfer duration MUST use the achieved operating flow.

### Key Entities

- **PumpPerformanceCurve**: pump identity, model kind, ordered flow/head points or quadratic coefficients, valid flow range, and speed range.
- **PumpSuctionRequirement / PumpSuctionInput**: pump identity, pump-specific required suction head and margin, plus operation-specific available suction head keyed by pump ID.
- **PumpTrain**: member pump identities and arrangement (series or parallel).
- **OperatingPoint**: pump/train identity, evaluated flow and head, route system head, suction margin, and feasibility status.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Curve head calculations match independently calculated reference points within 1% across all supported curve representations.
- **SC-002**: No tested route is accepted when its operating point is outside a pump's declared range or violates its suction safety margin.
- **SC-003**: Series and parallel test combinations match their reference head/flow values within 1%.
- **SC-004**: The feature-001 constant-head reference suite remains unchanged when curve mode is not selected.
- **SC-005**: Repeated evaluations for identical terminal versions, job inputs, and curve data produce identical operating points and route decisions.

## Assumptions

- Feature 001 provides the versioned terminal document, product/job inputs, shared directed graph, and route candidate pipeline this feature extends.
- Pump curve and suction-condition units use the terminal's existing units: flow in m3/h and head in metres of the conveyed liquid.
- The engineer/equipment source supplies pump curve and required-suction data on the terminal, while each route request supplies operation-specific available suction head keyed by pump ID. This feature does not connect to a vendor catalog or live sensor feed.
- The legacy constant-head model remains an explicit compatibility mode until all existing terminals are migrated.
- Detailed implementation choices for curve interpolation, intersection solving, and data migration are resolved in the plan from the reference behavior and tests.

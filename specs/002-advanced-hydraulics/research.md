# Research: Advanced Pump Hydraulics

Technical choices are resolved from `docs/10-Hydraulics-Engine.md`, the current Stage 1 engine, and the feature-001 reference tests. No NEEDS CLARIFICATION items remain.

## R1. Pump curve representation
- **Decision**: Keep `head_m` as the legacy constant-head mode. Add an optional pump performance model with either quadratic coefficients (`H(Q) = H0 - a Q^2`) or ordered tabular flow/head points. Require explicit minimum/maximum flow; VFD limits are speed ratios.
- **Rationale**: Supports the two curve forms in the domain document while keeping existing pump documents unchanged. Tabular data represents vendor curves without fitting error; quadratic data remains compact.
- **Alternatives considered**: A single fitted quadratic (can distort vendor data); arbitrary user-supplied formulas (unsafe and non-deterministic); storing a duplicate route-level pump model (violates the single-document principle).

## R2. Curve evaluation and operating point
- **Decision**: Interpolate tabular curves piecewise-linearly and evaluate quadratic curves directly; never extrapolate. Build the route system-head function from per-arc Darcy-Weisbach loss, elevation, and configured minor losses. Find intersections in the common declared flow range using bounded deterministic interval subdivision plus bisection on sign-changing brackets. Evaluate every bracket and choose the highest feasible stable operating flow that meets the request's minimum rate and all velocity/endpoint limits.
- **Rationale**: Bounded search handles the declared interval, avoids unbounded Newton steps, and gives stable results for monotonic pump curves. The accepted FR-011 interpretation is that request rate is a minimum and metrics use achieved operating flow.
- **Alternatives considered**: Extrapolation beyond curve samples (physically unsafe); unconstrained Newton-Raphson (can escape range or miss multiple roots); treating the requested rate as achieved without checking a fixed-speed operating point (overstates feasibility).

## R3. Schema evolution and compatibility
- **Decision**: Bump the authoritative terminal document schema from 1.0 to 1.1 for new optional pump-curve/train/suction fields. Parsers and generated models accept both 1.0 and 1.1; schema 1.0 retains the exact constant-head behavior. Newly authored documents use 1.1, while imported legacy documents remain 1.0 unless curve data is present.
- **Rationale**: Constitution I requires one versioned schema; an additive but behavior-changing model must not be silently represented as the old contract. This keeps old data readable and the oracle behavior stable.
- **Alternatives considered**: Keep schema_version 1.0 for changed semantics (unversioned contract drift); create a second pump schema (two sources of truth); reject legacy documents (unnecessary migration burden).

## R4. Suction checks
- **Decision**: Store pump `npsh_required_m` and nonnegative configurable `npsh_margin_m` on the pump; pass operation-specific `npsh_available_m` in the route request keyed by pump ID. Reject a curve-based candidate if the input is missing or `NPSH_available < NPSH_required + margin`, reporting `PUMP_SUCTION_MARGIN` with pump ID and values.
- **Rationale**: Available suction head can change with operating conditions and is not an immutable pump datasheet value. Feature 002 has no SCADA integration, so it is supplied by the planner for each operation.
- **Alternatives considered**: Persist available suction on the pump (stale across tank levels/operations); infer suction from product names or tank stock without a calibrated model (not authoritative); silently skip a missing input (unsafe).

## R5. Pump trains and VFD
- **Decision**: Represent named `PumpTrain` entries in TerminalDocument, with member pump IDs and `SERIES` or `PARALLEL` arrangement. Series heads sum at equal flow; parallel flows sum at equal head. Use affinity scaling for a selected speed ratio; evaluate the allowed speed range and choose the lowest speed that satisfies requested minimum flow and route head while respecting velocity limits.
- **Rationale**: Makes combined behavior explicit in the single terminal document and gives deterministic VFD selection without exposing a free-form solver setting.
- **Alternatives considered**: Assume every connected pump is in series (incorrect for parallel trains); infer train membership from geometry alone (ambiguous); arbitrary speed optimization (not required for the MVP).

## R6. Route metrics and exclusions
- **Decision**: Preserve existing route metrics and add achieved operating flow, required system head, available pump head, and suction margin. Add closed-set exclusions for invalid/out-of-range curve, no operating point, speed range, and suction margin failures.
- **Rationale**: The route shortlist remains explainable and existing consumers can ignore additive metrics; each infeasible candidate names its physical cause.
- **Alternatives considered**: Return only a boolean feasible flag (not explainable); overload `PUMP_HEAD` for every new failure (loses actionable reason detail).

## R7. Test and oracle strategy
- **Decision**: Add failing unit/property tests for both curve forms, boundaries, multiple roots, VFD scaling, series/parallel aggregation, and suction margin before engine changes. Run the existing Stage 1 oracle suite unchanged for 1.0 constant-head documents, then add a 1.1 curve-based reference fixture.
- **Rationale**: The current oracle contract is non-negotiable; the new mode must be additive and deterministic.
- **Alternatives considered**: Update expected legacy results to match the new solver (masks a regression); test only the numerical helper without route integration (misses filter/ranking effects).

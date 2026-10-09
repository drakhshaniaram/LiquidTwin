# Contract: Advanced Pump Hydraulics

This feature extends feature 001's versioned terminal document and route response; it does not add a separate pump API.

## Terminal document

- New curve/train fields are optional for schema 1.0 and supported in schema 1.1.
- `PUMP.head_m` remains the constant-head compatibility mode only when `performance_curve` is absent.
- `performance_curve.model` is `QUADRATIC` or `TABULAR`; invalid shape/range is rejected by terminal validation.
- Tabular points are ordered by strictly increasing `flow_m3h`; head must be nonnegative and nonincreasing.
- A curve-based pump supplies `npsh_required_m` and optional `npsh_margin_m`.
- Route requests supply operation-specific available suction head as `pump_suction_inputs: [{pump_id, npsh_available_m}]`; missing data for a curve-based pump is not treated as safe.
- A `pump_trains` entry names valid pump element IDs and arrangement `SERIES` or `PARALLEL`.

## Routing behavior

- Route request `rate_m3h` is the minimum required flow.
- Evaluate pump/system operating points only within declared curve and speed ranges; never extrapolate.
- Series members combine head at equal flow; parallel members combine flow at equal head.
- Return the achieved operating flow, pump/system head, head/suction margins, and selected common speed ratio in route metrics.
- Use explicit exclusions: `INVALID_PUMP_CURVE`, `PUMP_FLOW_OUT_OF_RANGE`, `NO_PUMP_SYSTEM_INTERSECTION`, `PUMP_SPEED_OUT_OF_RANGE`, `PUMP_SUCTION_MARGIN`.
- Schema 1.0 constant-head routes continue to match the existing reference oracle.

## Determinism

The same terminal version, route request, availability state, and solver configuration produce the same operating point and route ranking. Curve points are never reordered silently; invalid order is a validation error.

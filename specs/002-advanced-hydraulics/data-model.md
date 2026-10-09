# Data Model: Advanced Pump Hydraulics

This feature extends the single versioned TerminalDocument from feature 001. Units remain flow m3/h and head m. The JSON Schema remains the sole machine-readable source of truth; feature 002 introduces schema version 1.1 while retaining 1.0 parsing.

## Pump Performance Configuration

### Pump Element
Existing fields remain valid:
- `id`, `type=PUMP`, `from`, `to`, `head_m`, `max_flow_m3h`.
- If `performance_curve` is absent, use the existing constant-head `head_m` model with byte-for-byte equivalent Stage 1 metrics for the feature-001 oracle inputs.
- If present, use the curve model and do not fall back to `head_m` when curve validation or range checks fail.

### PerformanceCurve
`model (QUADRATIC|TABULAR), min_flow_m3h, max_flow_m3h, shutoff_head_m?, quadratic_coefficient?, points[]?, speed_ratio_min, speed_ratio_max`.

- `QUADRATIC`: `H(Q) = shutoff_head_m - quadratic_coefficient * Q^2`; `quadratic_coefficient >= 0`.
- `TABULAR`: `points[] = {flow_m3h, head_m}`; at least two points, flow strictly increasing, head nonnegative and nonincreasing. Evaluate by piecewise-linear interpolation only inside the point range.
- `0 < min_flow_m3h < max_flow_m3h`; speed ratios satisfy `0 < speed_ratio_min <= speed_ratio_max <= 1`.
- Applying speed ratio `s` follows affinity scaling: flow scales by `s`, head by `s^2`.

### PumpSuctionRequirement and PumpSuctionInput
Pump element fields: `npsh_required_m >= 0, npsh_margin_m >= 0` (margin defaults to 0.5 m). Operation request field: `pump_suction_inputs[] = {pump_id, npsh_available_m >= 0}`. The available value is keyed by pump because it can change with operating conditions; it is not persisted as a pump property. A curve-based route is not feasible if any required pump lacks a corresponding input or available head is below required head plus margin.

### PumpTrain
`id, arrangement (SERIES|PARALLEL), member_pump_ids[]`.
- Member IDs reference PUMP elements and may belong to only one train.
- A train contains at least two distinct pump members.
- Series: sum member head at a shared flow.
- Parallel: sum member flow at a shared head.
- Invalid/missing members are document validation errors.

## OperatingPoint (derived, not persisted)
For a route candidate: `pump_or_train_id, achieved_flow_m3h, pump_head_m, system_head_m, npsh_available_m?, npsh_required_m?, suction_margin_m?, speed_ratio, feasible, exclusion_reason?`.

The route request's `rate_m3h` is a minimum acceptable flow. A valid operating point must be at or above it. The route request also carries per-pump available suction inputs. The route transfer duration uses achieved flow. Operating points are derived deterministically from the versioned document and request; they are not written back to the terminal document.

## Route metric additions
Add optional metrics to feature-001 `RouteMetrics`: `operating_flow_m3h`, `pump_head_m`, `system_head_m`, `suction_margin_m`, and per-pump/train operating point details. Existing metrics remain unchanged for schema 1.0 constant-head inputs.

## Exclusion reasons
Extend `ExclusionReason` with:
- `INVALID_PUMP_CURVE`
- `PUMP_FLOW_OUT_OF_RANGE`
- `NO_PUMP_SYSTEM_INTERSECTION`
- `PUMP_SPEED_OUT_OF_RANGE`
- `PUMP_SUCTION_MARGIN`

Each reason contains pump/train ID, relevant flow/head/suction values, and a human-readable fix hint.

## Schema version transition
- Schema 1.0: existing document accepted; absent curve fields mean constant-head behavior.
- Schema 1.1: new authored documents may include `performance_curve`, suction conditions, and `pump_trains`.
- JSON and CSV import/export preserve schema version and all curve/train fields. Codegen updates TypeScript and Pydantic models from the versioned schema.

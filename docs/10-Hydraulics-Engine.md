# 10 Hydraulics Engine

## Per-arc quantities
For flow `Q` (m3/h), diameter `D` (m), length `L` (m):

$$A=\frac{\pi D^2}{4},\qquad v=\frac{Q/3600}{A}\cdot k_{inst}$$

`k_inst` is the installation velocity factor from the brief (underground vs aboveground; default 1.0 and configurable).

Friction head (Darcy-Weisbach):

$$h_f = f\,\frac{L}{D}\,\frac{v^2}{2g}$$

Lift: `dz` (m), sign flipped on reverse traversal. Required head `H_req = h_f + dz` (+ valve/fitting minor losses `K v^2/2g`).

The reference uses fixed `f` per product and `g = 9.81` (code constant 19.62 = 2g) and stores heads in decimetres (`10 x m`) for integer CP-SAT use.

## Pump model
- Schema 1.0 and pumps without `performance_curve`: constant head `H_p` (as reference).
- Schema 1.1 curve pumps: quadratic `H(Q) = H0 - a Q^2` or ordered tabular points evaluated by piecewise-linear interpolation. Curves are never extrapolated beyond their declared flow range.
- Operating flow is the highest in-range pump/system intersection that meets the requested minimum rate. Transfer duration uses this achieved flow.
- A route request supplies available NPSH for every curve pump. The route is rejected unless `NPSHa >= NPSHr + configured margin` for each member.
- Series trains add member head at shared flow; parallel trains add member flow at shared head. Declared VFD ranges use affinity scaling (`Q ∝ speed`, `H ∝ speed²`); the solver selects the lowest common permitted speed that meets the route requirement.
- Curve routes report achieved flow, pump/system head, head margin, suction margin, and selected speed ratio. Exclusions identify invalid curves, flow/speed limits, missing operating points, and suction-margin failures.
- The feature-001 schema 1.0 reference suite remains unchanged and is the compatibility gate for constant-head routes.

## Route feasibility
$$\sum_{pumps} H_p - \sum_{arcs} H_{req} \ge 0$$

## Timing
- `fill_min = ceil(L / v / 60)` per arc plus valve operation time.
- Transfer duration `ceil(V * 60 / Q)`.
- Job end `= start + transfer + sum(fill) + sum(flush_time)`.

## Flushing and changeover
- Residue `r` in an element and next product `p`: flush volume `= flush_factor(r, p) * A * L`.
- Flush time `= flush_volume / flush_rate * 60` (reference `FLUSH_RATE = 600 m3/h`).
- Gap between consecutive uses of a shared element: `changeover[(p_prev, p_next)]` minutes.
- `manual_clean_required` pairs are forbidden for automatic routing.

## Velocity limits
`v <= v_max` (reference 3.0 m/s), per product and per element override.

## Validation
Unit tests against closed-form examples; cross-check with the reference numbers (e.g., Jetty1 line).

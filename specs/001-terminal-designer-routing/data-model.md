# Data Model: Terminal Designer, Graph and Quickest-Route Planner

Units: time min, length m, diameter mm, volume m3, flow m3/h, head m. The authoritative machine definition is [contracts/terminal-document.schema.json](contracts/terminal-document.schema.json).

## Entities

### Terminal
| Field | Notes |
|---|---|
| id | UUID |
| name | unique, 1-120 chars |
| current_version | integer, latest TerminalVersion |

### TerminalVersion (append-only)
`terminal_id, version, document (TerminalDocument), created_at, note`.

### TerminalDocument
`schema_version, name, products[], changeover[], nodes[], elements[], tank_groups[], layout{}`.

### Product
`id, name, group, friction_factor (0.005-0.1), max_velocity (m/s, default 3.0), color`.

### ChangeoverRule
`from_product, to_product, gap_min >= 0, flush_factor >= 0, manual_clean_required (bool)`. Same-product pairs default to 0.

### Node (vertex)
Common: `id, type, name, x, y`.
| type | Extra fields |
|---|---|
| TANK | `group_id, product_id (nullable = empty), stock_m3, capacity_m3, min_heel_m3, allow_inbound, allow_outbound, allow_simultaneous` |
| JETTY | `max_rate_m3h, certified_products[]` |
| LOADING_POINT | `max_rate_m3h, certified_products[]` |
| RAIL_PLATFORM | `side_count, cars_per_side` |
| RAIL_CAR | `platform_id, product_id (nullable), stock_m3, capacity_m3` |
| MANIFOLD | `legs[]` |
| JUNCTION | none |

### Element (edge)
Common: `id, type, from, to, length_m, diameter_mm, elevation_delta_m (to minus from), installation (UNDERGROUND|ABOVEGROUND), roughness_mm, certified_products[], dedicated_group_id?, dedicated_product_ids[], residue_product_id?, bidirectional (bool)`.
| type | Extra fields |
|---|---|
| TANK_HEADER | `tank_id` (one tank only) |
| SEGMENT | `tank_id` |
| COMMON_HEADER | none |
| LINE | jetty or loading line |
| PUMP | `head_m, max_flow_m3h, one_way = true` |
| VALVE | `operate_min, state (OPEN|CLOSED)`; length 0 |
Valid combinations: TANK_HEADER and SEGMENT connect exactly one tank on one end; PUMP and VALVE have length 0 or small.

### TankGroup
`id, name, tank_ids[]` (derived membership also stored on Tank).

### AvailabilityWindow (separate table)
`id, terminal_id, element_id, status (AVAILABLE|MAINTENANCE|FLUSHING|CLEANING|OUT_OF_SERVICE), from, to (nullable = open-ended), reason, source, external_ref`.
Unique on `(terminal_id, element_id, source, external_ref)`.

### RouteRequest
`terminal_id, version?, direction (IN|OUT|TRANSFER), product_id, volume_m3, rate_m3h, window_from, window_to, source_ids[], destination_ids[], max_routes (default 5, max 20)`.

### Route
`rank, source_id, destination_id, steps[{element_id, from, to, reversed}], metrics{fill_min, transfer_min, flush_min, flush_volume_m3, total_min, valves, common_headers, head_margin_m, max_velocity_ms}`.

### Exclusion (explanation)
`element_id, reason (ExclusionReason), detail`.
`ExclusionReason`: NOT_CERTIFIED, VELOCITY, RESIDUE, ONE_WAY_PUMP, UNAVAILABLE, DEDICATED_OTHER_GROUP, PUMP_HEAD, ENDPOINT_STOCK, ENDPOINT_SPACE, ENDPOINT_PRODUCT, ENDPOINT_DIRECTION (tank `allow_inbound`/`allow_outbound`/`allow_simultaneous` forbids the operation).

### ValidationIssue
`severity (ERROR|WARNING), code, element_id?, node_id?, message, fix_hint`.

### TerminalGraph (derived, not persisted)
The engine derives this from one `TerminalDocument`; it is not a second source of truth. It contains the terminal's `nodes`, `elements`, directed `arcs`, and validation `issues`. The engine representation also indexes arcs by their source node (`out`) for graph traversal. The API exposes a versioned read-only projection at `GET /terminals/{terminalId}/graph?version=N`.

### GraphArc (engine and API projection)
- Engine fields: `element_id, u, v, reversed`.
- API fields: `id, element_id, from, to, reversed, traversable, restriction?`.
- A forward arc follows the element's `from` to `to`. A reverse arc follows `to` to `from`; its `reversed` flag remains true for explanations and hydraulic sign changes.
- Reverse arcs are generated when the element is bidirectional or is a PUMP. Reverse pump arcs are retained in the projection with `traversable=false` and `restriction=ONE_WAY_PUMP`; routing excludes them even when pump head is zero.
- Parallel physical elements produce distinct arcs with distinct `element_id` values.
- Structural validation errors (`SCHEMA`, `DUPLICATE_ID`, `DANGLING_ELEMENT`, `SELF_LOOP`) prevent projection with HTTP 422. Other validation issues are returned alongside the graph.

### ConfirmedRoute
`id, terminal_id, terminal_version, request (RouteRequest), route (Route), outdated (bool, default false), outdated_reason?, created_at, actor`. Created when the user selects the final route from the shortlist (FR-023). Set `outdated = true` when an availability window overlapping the route's elements and the job window is added or changed (FR-016). `actor` is the anonymous actor in the single-user MVP and reserved for later multi-user use.

## Relationships
- Terminal 1..* TerminalVersion; TerminalVersion embeds one TerminalDocument.
- Node 0..* Element via `from`/`to` (multigraph: several elements may join the same pair).
- Tank 1 TankGroup; TANK_HEADER and SEGMENT reference one Tank.
- Terminal 0..* AvailabilityWindow.
- Terminal 0..* ConfirmedRoute (each references the TerminalVersion it was computed against).
- Multi-user readiness: TerminalVersion is append-only and may later carry a `base_version` check on save; no lock entity exists in this MVP.

## Validation rules
- Ids unique per kind; references resolve; `from != to`.
- `length_m >= 0`, `diameter_mm > 0` (except VALVE), `0 <= stock <= capacity`.
- Tank product must exist; certified product ids must exist.
- TANK_HEADER connects to exactly one TANK node; it is not shared.
- Warnings: isolated node, pump with both ends on a TANK_HEADER, product certified nowhere reachable from any loading point, availability window with `to < from`.
- Import is all-or-nothing: any ERROR rejects the file with per-row messages.

## Graph derivation
Each element yields a forward arc `from->to`. A reverse arc `to->from` is also created when `bidirectional=true` or the element is a PUMP; the reverse pump arc is retained for explanation but is not traversable. Reverse traversal flips the elevation delta sign. The graph is a directed multigraph: parallel elements remain distinct. Job-dependent values (velocity, required head, fill time, flush volume) are computed during routing, not stored in the graph projection.

### K-shortest-path use
`route_job` consumes the same engine `TerminalGraph` used by the graph API projection. It filters arcs for the job, forms a simple directed graph using the lowest-cost eligible arc per node pair, generates up to K=20 shortest simple node paths with NetworkX, then expands parallel element alternatives (bounded to 8 combinations per path) and checks pump head. Feasible routes are ranked by total time, flush volume, valve count, common-header count, then stable element IDs. The HTTP graph response is for inspection and is not reparsed by the router.

## State transitions
- Availability: `AVAILABLE <-> MAINTENANCE | FLUSHING | CLEANING | OUT_OF_SERVICE` by window; a window active at any time in the job window excludes the element.
- Valve state is informational for routing in this feature; opening time is added to fill time.
- Terminal versions only grow; "restore" creates a new version copying an older document.

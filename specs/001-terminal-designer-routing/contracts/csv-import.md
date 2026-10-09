# Contract: CSV Import Bundle

A bundle is a set of UTF-8 CSV files (comma separated, header row required, `.` decimal point, empty cell = unset). Import is all-or-nothing: any error rejects the whole bundle with `ValidationIssue` entries carrying `file` and `row`. Output is the same TerminalDocument as the JSON import ([terminal-document.schema.json](terminal-document.schema.json)).

Lists inside a cell use `;` as separator (for example `P1;P2`). Booleans are `true` or `false`.

## products.csv (required)
| column | required | notes |
|---|---|---|
| id | yes | unique |
| name | yes | |
| group | no | |
| friction_factor | no | default 0.018 |
| max_velocity | no | m/s, default 3.0 |
| color | no | `#RRGGBB` |

## changeover.csv (optional)
`from_product, to_product, gap_min, flush_factor, manual_clean_required`

## nodes.csv (required)
| column | applies to | notes |
|---|---|---|
| id, type, name | all | type: TANK, JETTY, LOADING_POINT, RAIL_PLATFORM, RAIL_CAR, MANIFOLD, JUNCTION |
| x, y | all | optional; auto-layout when all missing |
| max_rate_m3h, certified_products | JETTY, LOADING_POINT | |
| side_count, cars_per_side | RAIL_PLATFORM | |
| platform_id, product_id, stock_m3, capacity_m3 | RAIL_CAR | `platform_id` must reference a RAIL_PLATFORM node |

## tanks.csv (required when nodes contain TANK)
`node_id, group_id, product_id, stock_m3, capacity_m3, min_heel_m3, allow_inbound, allow_outbound, allow_simultaneous`
`node_id` must reference a TANK node. Groups referenced here are created automatically (`group_id` doubles as name unless `groups.csv` is supplied).

## groups.csv (optional)
`id, name`

## elements.csv (required)
| column | notes |
|---|---|
| id, type, from, to | type: TANK_HEADER, SEGMENT, COMMON_HEADER, LINE, PUMP, VALVE |
| length_m, diameter_mm, elevation_delta_m | elevation = to minus from |
| installation | UNDERGROUND or ABOVEGROUND (default ABOVEGROUND) |
| roughness_mm | optional |
| certified_products | list; empty = none certified |
| dedicated_group_id, dedicated_product_ids | optional |
| residue_product_id | optional |
| bidirectional | default true; PUMP is always one-way |
| tank_id | required for TANK_HEADER and SEGMENT |
| head_m, max_flow_m3h | PUMP |
| operate_min, state | VALVE |

## availability.csv (optional)
`element_id, status, from, to, reason, source, external_ref` with ISO-8601 timestamps; imported as availability windows, not as part of the document.

## Rules
- Unknown columns are rejected (typo protection) unless prefixed with `x_`, which are ignored.
- Foreign keys must resolve (nodes, products, tanks, groups).
- Numbers outside schema ranges are rejected with the row number.
- A CSV bundle and JSON file describing the same terminal MUST produce identical TerminalDocuments (order-normalized by id); this is a contract test.
- Export to CSV produces the same file set and round-trips.

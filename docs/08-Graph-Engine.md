# 08 Graph Engine

## Representation
Directed multigraph `G = (V, A)`. Every physical element `e = (a, b)` yields two arcs `a->b` (forward) and `b->a` (reverse), unless `bidirectional=false`. Pumps are forward-only (the reference "one-way pump rule": reverse flow through a pump is forbidden).

Parallel elements between the same node pair are **kept** (the reference keeps only the cheaper one). Implementation: arc key = `(u, v, element_id)`; for shortest-path queries use the cheapest per pair for pruning, and expand all parallel alternatives in Stage 1 enumeration.

## Node/arc attributes
Arc: `element_id, direction, length, diameter, dz (sign flipped on reverse), type, residue, certified, availability windows, cost fields`. Node: `type, tank state`.

## Build pipeline
1. Parse and validate document.
2. Collapse zero-length valves into arcs with operation time (valve stays an element for exclusivity).
3. Derive `snapshot(t)`: remove elements unavailable at time `t` (hard-excluded for the entire job window if overlap, see [11](11-Optimization-Engine.md)).
4. Build per-job filtered view (certification, velocity, residue, dedication, one-way pump rule).

## Algorithms
- Connected components and reachability matrix for fast infeasibility detection.
- Dominator-like "must-pass" detection (articulation elements) to explain bottlenecks.
- Reverse index: element -> routes that use it.

## Explainability
Each removed arc stores `reason_code` in `{NOT_CERTIFIED, VELOCITY, RESIDUE, ONE_WAY_PUMP, UNAVAILABLE, DEDICATED_OTHER_GROUP}`.

## Scale
1k nodes / 6k arcs: graph build < 200 ms; incremental update on availability change < 20 ms by flagging arcs rather than rebuilding.

## API (internal)
`build_graph(doc) -> Graph`, `view_for_job(graph, job, t) -> JobGraph`, `explain(job_graph, element) -> reason`.

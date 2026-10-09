# Research: Terminal Designer, Graph and Quickest-Route Planner

All Technical Context items are resolved; no NEEDS CLARIFICATION remain.

## R1. Rendering technology
- **Decision**: PixiJS v8 (2D WebGL) for the designer and route overlay; three.js deferred to the optional 3D/simulation feature.
- **Rationale**: Schematic terminal views are 2D. Pixi handles tens of thousands of sprites and lines with touch support and smooth animation. SVG/DOM libraries (React Flow) slow down beyond about 1-2k elements, below the 5,000-pipe target.
- **Alternatives**: React Flow / SVG (too slow at scale); Canvas 2D (no batching, weaker animation); three.js (3D overhead and UX not needed for schematics); Konva (adequate to ~5k objects, smaller ecosystem for LOD and shaders).

## R2. Backend language and framework
- **Decision**: Python 3.12 with FastAPI and Pydantic v2.
- **Rationale**: OR-Tools CP-SAT (next feature) is first-class in Python; the reference script is Python; engine code can be shared. Routing time is dominated by graph algorithms, not language overhead.
- **Alternatives**: .NET (good for D365 integration but weaker OR-Tools tooling and would rewrite the reference); Node/TypeScript (no CP-SAT); Rust/rustworkx core (premature, kept as optimization path).

## R3. Graph library and k-shortest paths
- **Decision**: networkx `shortest_simple_paths` (Yen) over a per-job filtered `DiGraph`, with parallel elements expanded after path search; switch to rustworkx if the benchmark misses the 1 s budget.
- **Rationale**: Matches the reference behaviour exactly (oracle comparison), simple API, adequate for 6k arcs and K=20.
- **Alternatives**: igraph (fast but different API and tie-breaking); custom Yen (more code, no benefit yet); keeping only the cheapest parallel edge as the reference does (rejected: spec requires parallel lines as alternatives, so parallels are expanded post-search).

## R4. Hydraulics model for MVP
- **Decision**: Darcy-Weisbach friction head with a per-product friction factor, lift from elevation change, constant-head pumps, velocity from flow and diameter times an installation factor, as in the reference. Pump curves and Colebrook are later (doc 10).
- **Rationale**: Reproduces the reference results; keeps the first slice testable.
- **Alternatives**: Full pump curve and operating point now (not needed for oracle, adds risk).

## R5. Terminal document format and codegen
- **Decision**: JSON Schema (2020-12) is the source of truth; generate TypeScript with `json-schema-to-typescript` and Pydantic models with `datamodel-code-generator` in CI; fail CI on drift.
- **Rationale**: Constitution I; one definition for UI forms, API validation and import.
- **Alternatives**: Pydantic as source (TS drift risk); Protobuf (poor fit for hand-edited and CSV-imported documents).

## R6. CSV import
- **Decision**: A bundle of CSV files (`nodes.csv`, `elements.csv`, `tanks.csv`, `products.csv`, `changeover.csv`, `availability.csv`) with documented columns; parsed in the browser (Papa Parse) into a TerminalDocument and also accepted server-side through the same engine function so both paths give identical results.
- **Rationale**: Spec FR-003/SC-005; per-row error reporting; no partial import.
- **Alternatives**: Single wide CSV (cannot express tank properties and changeover pairs cleanly); Excel (later).

## R7. Auto-layout for imports without coordinates
- **Decision**: elkjs layered layout run in a Web Worker; user can then edit.
- **Rationale**: Handles large graphs, orthogonal edge routing suits pipelines.
- **Alternatives**: dagre (weaker orthogonal routing), force layout (unstable, unreadable for pipelines).

## R8. Persistence and versioning
- **Decision**: PostgreSQL; table `terminal` plus append-only `terminal_version(document JSONB, created_at, note)`; availability windows in their own table keyed by terminal and element id.
- **Rationale**: Version history (FR-017) is append-only; JSONB keeps the document intact and queryable.
- **Alternatives**: SQLite (no concurrent editors), document stores (less operational familiarity).

## R9. Availability model
- **Decision**: Availability is separate from the document: windows (element, status, from, to, reason, source) are evaluated at route time against the job window; external updates via `POST /terminals/{id}/availability`, idempotent by `(element_id, source, external_ref)`.
- **Rationale**: Availability changes daily and must not create new terminal versions; idempotency suits retried feeds.
- **Alternatives**: Store as element attributes (version churn).

## R10. Explanations
- **Decision**: Each arc removed by a filter records a reason code from a closed set (`NOT_CERTIFIED`, `VELOCITY`, `RESIDUE`, `ONE_WAY_PUMP`, `UNAVAILABLE`, `DEDICATED_OTHER_GROUP`, `PUMP_HEAD`, `ENDPOINT_STOCK`, `ENDPOINT_SPACE`, `ENDPOINT_PRODUCT`, `ENDPOINT_DIRECTION`); no-route responses include the cheapest blocked path and its blockers.
- **Rationale**: Constitution II; spec FR-014.

## R11. Authentication
- **Decision**: None in this feature (spec FR-019); a single FastAPI dependency `current_actor()` returns an anonymous actor so OIDC can be dropped in later.
- **Rationale**: Product decision; recorded as a justified constitution deviation.

## R12. Mobile / PWA
- **Decision**: Vite PWA plugin, responsive layout with bottom-sheet panels on narrow screens, pointer events for gestures, read/query as the primary phone workflow and editing on tablets.
- **Alternatives**: Native wrappers (not needed).

## R13. Testing strategy for correctness
- **Decision**: Reference-oracle test compares Stage 1 candidate routes and metrics on the sample terminal to `lineup_cpsat.py` output; property tests (hypothesis) assert filtered arcs never appear in returned routes; Playwright mobile-viewport smoke test for pan/zoom and route request.

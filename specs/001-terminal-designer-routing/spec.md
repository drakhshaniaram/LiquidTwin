# Feature Specification: Terminal Designer, Graph and Quickest-Route Planner

**Feature Branch**: `001-terminal-designer-routing` (no branch created; no git hook registered)

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Web application, mobile-friendly, where a user designs an oil/liquid-bulk terminal visually or by importing JSON/CSV (tank groups, tanks, tank headers, common headers, segments, pumps, valves, manifolds, jetties, loading points, rail), sees it as a precise connected graph, and, given a source, destination, product, volume, rate and time, receives the quickest feasible route for an inbound or outbound operation with explanations. Equipment availability (maintenance, flushing, cleaning) is updated from outside and changes the result. Source material: docs/00-12, lineup_cpsat.py reference."

## Clarifications

### Session 2026-10-08

- Q: What should happen when two people edit and save the same terminal at the same time? → A: Out of scope for this MVP (single user). Saves stay append-only versions so locking or conflict detection can be added later without changing stored data.
- Q: What does "quickest route" mean when ranking routes? → A: Route selection is a pipeline: (1) generate the k shortest paths, (2) rule out those that fail the availability and feasibility criteria to leave a shortlist of best routes, (3) if more than one route remains the user chooses the final one in the MVP; the system will choose automatically in a later version. Shortlist is ordered by total time, then flush volume, valve count and shared-header use.
- Q: Which stock level should be used when checking that a source has enough product and a destination has enough space? → A: Current stock values stored in the terminal; stock forecasting is part of the later multi-job optimization feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Design or import a terminal (Priority: P1)

An engineer builds a terminal by dragging equipment onto a canvas and connecting it, or imports a JSON or CSV file that describes the same equipment and its interconnections. The user edits properties (dimensions, elevation, installation, product certification, dedication, changeover costs) and sees validation problems as they work.

**Why this priority**: Nothing else works without a terminal model; it is the foundation for routing, optimization and simulation.

**Independent Test**: Import the sample terminal from JSON and from CSV; both produce an identical terminal. Build a small terminal by hand and save it.

**Acceptance Scenarios**:

1. **Given** an empty project, **When** the user places tanks, pipes, a pump, valves and a jetty and connects them, **Then** the terminal is saved and reloaded unchanged.
2. **Given** a JSON file and a CSV bundle describing the same terminal, **When** both are imported, **Then** the resulting terminals are identical.
3. **Given** a pipe attached to no equipment, **When** the user views validation, **Then** a clear message identifies the pipe and suggests a fix.
4. **Given** a file without positions, **When** imported, **Then** the terminal is laid out automatically and remains editable.

---

### User Story 2 - Find the quickest route for one operation (Priority: P1)

A planner selects a source and a destination (for example a jetty and a tank, or a tank and a loading point), a product, volume, rate and time window, and chooses inbound or outbound. The app shows the quickest feasible route highlighted on the terminal, with its time, flush volume, valve count and common-header use, plus alternatives.

**Why this priority**: This is the core value stated in the brief: the quickest route for inbound and outbound operations.

**Independent Test**: On the sample terminal, request jobs from the reference scenario; each returns a route consistent with the reference routes.

**Acceptance Scenarios**:

1. **Given** a valid terminal, **When** the planner requests a route for a product, **Then** a shortlist of feasible routes is shown ordered by total time, the best is highlighted, and the planner confirms the final route when more than one remains.
2. **Given** a path that is blocked because a pipe is not certified for the product, runs too fast, or would need a pump in reverse, **When** a route is requested, **Then** the route avoids it and the explanation names the pipe and the reason.
3. **Given** no feasible route, **When** requested, **Then** the app states the blocking reasons (for example "all paths pass element E7, in maintenance").
4. **Given** the destination tank lacks free space or the source lacks stock, **When** requested, **Then** that tank is excluded with a reason.

---

### User Story 3 - Keep equipment availability current (Priority: P2)

An operator marks equipment as in maintenance, flushing or cleaning for a time window, manually or via an external feed. Routes reflect it immediately; open results are flagged as outdated.

**Why this priority**: Availability changes daily and invalidates plans; required by the brief but builds on Stories 1 and 2.

**Independent Test**: Mark a pipe unavailable for a window; request the same route inside and outside the window and compare results.

**Acceptance Scenarios**:

1. **Given** a route using pipe P, **When** P is marked unavailable for the job window, **Then** the route changes and the explanation names P.
2. **Given** the window ends, **When** a route is requested after it, **Then** P is usable again.
3. **Given** an external update arrives, **When** it is processed, **Then** the terminal view shows the new status and previously computed routes using that equipment are flagged outdated.

---

### User Story 4 - Use it on a phone or tablet (Priority: P2)

A supervisor opens the app on a phone, views the terminal, pans and zooms with touch, requests a route and reads the explanation.

**Why this priority**: The brief requires a mobile-friendly application; read-and-query use is more important than full editing on small screens.

**Independent Test**: On a mid-range phone, open the large synthetic terminal, pan/zoom and request a route.

**Acceptance Scenarios**:

1. **Given** a phone screen, **When** the user opens a terminal, **Then** the layout adapts and touch pan/zoom work smoothly.
2. **Given** a tablet, **When** the user edits properties, **Then** the controls are usable by touch.

---

### Edge Cases

- Parallel pipes between the same two points: all are retained and offered as alternatives.
- A pipe used for several products in sequence: the route reports flush volume and time for the product change.
- Pipe that is one-way (pump direction) or dedicated to a tank group or product group.
- Underground versus aboveground pipes: velocity differs by a configurable factor.
- Source equals destination, or a tank that is both source and destination candidate.
- Import with duplicate ids, missing references, or unknown units: rejected with a per-row message; nothing partially imported.
- Very large terminals (hundreds of tanks, thousands of pipes): remains responsive.
- Availability update for equipment that does not exist: reported and ignored without failing the feed.
- Two people editing the same terminal: not supported in this MVP (single user); each save is an append-only version, so the later save is the current one and earlier ones remain in version history.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to create a terminal visually by placing, moving, connecting, grouping and deleting equipment, with undo and redo.
- **FR-002**: The system MUST support these equipment types: tank groups, tanks, tank headers, common headers, segments, pumps, valves, manifolds, jetties, loading points, rail platforms and rail cars.
- **FR-003**: Users MUST be able to import a terminal from JSON and from a set of CSV files, and export to both, with identical results for equivalent content.
- **FR-004**: Each pipe MUST record length, diameter, elevation change, underground or aboveground installation, certified products, optional dedication to a tank group or product group, and optional one-way restriction.
- **FR-005**: Tanks MUST record product, stock, capacity, and whether inbound, outbound and simultaneous operation are allowed.
- **FR-006**: The system MUST store product changeover time and flush factors for each ordered pair of products.
- **FR-007**: The system MUST validate the terminal continuously and list problems with location and suggested fix.
- **FR-008**: The system MUST derive a connected graph of the terminal and show it as the same terminal the user designed.
- **FR-009**: Users MUST be able to request a route by choosing source, destination, product, volume, rate, time window and direction (inbound or outbound).
- **FR-010**: Route search MUST exclude equipment that is uncertified for the product, exceeds the velocity limit, violates a one-way pump rule, is dedicated to another group, or is unavailable in the window.
- **FR-011**: Route search MUST exclude sources without enough stock and destinations without enough free space or with an incompatible product, using the current stock values stored in the terminal (no forecasting).
- **FR-012**: Routes MUST be rejected when the pumps on the path cannot cover friction loss plus lift.
- **FR-013**: For each route the system MUST report total time, flush volume and time, valve count and common-header use, and order the shortlist by total time, then flush volume, valve count and shared-header use.
- **FR-023**: Route selection MUST work as a pipeline: generate the k shortest paths, rule out those failing availability and feasibility criteria to form a shortlist, and when more than one route remains let the user choose the final route (automatic choice is out of scope for this feature).
- **FR-014**: When no route exists, or an expected pipe is excluded, the system MUST explain why, naming the equipment and the reason.
- **FR-015**: Users MUST be able to set equipment availability (available, maintenance, flushing, cleaning, out of service) for a time window, and an external system MUST be able to submit the same updates.
- **FR-016**: Availability changes MUST affect subsequent route requests and flag confirmed routes that use the changed equipment as outdated.
- **FR-017**: The terminal MUST be saved with version history so earlier versions can be restored.
- **FR-018**: The application MUST be usable on phones and tablets (reference device: Pixel 5 class) with touch gestures and adapt its layout to screen size.
- **FR-019**: For this feature the application MUST be usable without sign-in by a single user. The design MUST NOT preclude adding sign-in, roles and multiple concurrent users later.
- **FR-020**: The system MUST handle terminals of at least 500 tanks, 5,000 pipes, 100 loading points, 500 valves and 50 jetties.

### Key Entities

- **Terminal**: a named, versioned collection of equipment, products and changeover rules.
- **Tank Group / Tank**: storage with product, stock, capacity and operating modes.
- **Pipe**: a connection with length, diameter, elevation, installation, certification, dedication and role (tank header, common header, segment, jetty or loading line).
- **Pump / Valve / Manifold**: equipment that adds head, switches flow or joins several lines.
- **Jetty / Loading Point / Rail Platform**: endpoints for inbound and outbound operations.
- **Product**: name, group, friction and velocity limits, colour.
- **Changeover Rule**: time gap and flush factor for a pair of products.
- **Availability Window**: equipment, status, start, end, reason, source.
- **Route Request / Route**: the operation asked for and the equipment sequence offered with its metrics and explanations.
- **Confirmed Route**: the route a user selected for a request, with the request details, the terminal version used and an outdated flag.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can import a terminal from a file and see it ready for routing in under 1 minute.
- **SC-002**: A user can request and read a route in under 30 seconds from opening a terminal.
- **SC-003**: A route request returns in under 1 second for a terminal of 500 tanks and 5,000 pipes.
- **SC-004**: For the reference sample terminal, route results match the reference solution in 100% of the sample jobs.
- **SC-005**: JSON and CSV imports of the same terminal produce identical terminals in 100% of test cases.
- **SC-006**: Marking equipment unavailable changes the affected route and names the equipment in 100% of tested cases.
- **SC-007**: The large terminal can be panned and zoomed smoothly (at least 30 frames per second) on a reference mid-range phone (Pixel 5 class, checked on one real device).
- **SC-008**: In usability testing, at least 90% of planners complete a route request on a phone on the first attempt.

## Assumptions

- This feature covers designer, graph, availability and single-operation quickest route. Multi-job optimization, full simulation, and live SCADA/D365 connections are separate later features (see `docs/03-Product-Roadmap.md`).
- Technical choices (languages, libraries, services) are decided in the plan; see `docs/05-System-Architecture.md` and the constitution.
- The sample terminal and its four reference jobs from the reference script are the acceptance data set.
- Availability updates arrive as discrete events or manual input; continuous real-time streaming is out of scope here.
- Units are fixed (minutes, metres, millimetres, cubic metres, cubic metres per hour) and converted only for display.
- Users have a modern browser and intermittent connectivity is tolerated for viewing, not for saving.
- Single user in this MVP: no locking or concurrent-edit handling. Multi-user is anticipated: versions are append-only and every request passes through an actor seam, so locks, optimistic version checks and roles can be added later.
- Jetty and loading-point rate limits and manifold leg rules are not enforced in routing for this feature.
- No authentication in this feature (clarified); this conflicts with the constitution's OIDC security constraint and must be recorded as a justified deviation in the plan (deployment limited to trusted networks until sign-in is added).

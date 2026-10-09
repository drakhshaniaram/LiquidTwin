<!--
Sync Impact Report (temporary; remove before commit)
Version change: template (unversioned) -> 1.0.0
Modified principles: none (initial adoption)
Added sections: Core Principles I-VII, Technology & Domain Constraints, Development Workflow & Quality Gates, Governance
Removed sections: none
Deferred TODOs: none
-->
# LiquidTwin Constitution

## Core Principles

### I. Single Terminal Document
The terminal is described by one versioned, schema-validated TerminalDocument (JSON Schema is the
source of truth; TypeScript and Pydantic types are generated from it). The designer, graph, router,
optimizer and simulator MUST consume this document and MUST NOT hard-code terminal data. CSV import
MUST produce a document identical to the equivalent JSON import.

### II. Physics-Aware and Explainable
Velocity, friction, lift, pump head, installation (underground/aboveground), flushing and changeover
MUST be modeled explicitly. Every rejected arc, route or job MUST carry a machine-readable reason
code and a human-readable explanation. Units are fixed (min, m, mm, m3, m3/h, head m) and converted
only at the UI boundary.

### III. Reference-Oracle Regression (NON-NEGOTIABLE)
`lineup_cpsat.py` is the behavioural oracle for the optimizer: on the sample terminal the service
MUST return status OPTIMAL, objective 1327, all jobs on time. The AnyLogic "Oil Terminal - Version 14"
is the oracle for the simulation (KPI deviation within the agreed tolerance). Changes that break an
oracle MUST be justified in the spec and the oracle updated in the same change.

### IV. Test-First
Tests MUST be written and observed failing before implementation of engines (graph, routing,
hydraulics, optimization, simulation). Each engine MUST be a library with no UI or network dependency
and with contract tests on its public API.

### V. Deterministic and Reproducible
Solver runs and simulations MUST accept a seed and produce identical results for identical inputs and
versions. Results record the document version, solver version, parameters and seed.

### VI. Performance Budgets
Targets are binding acceptance criteria: single-job route under 1 s and graph load under 200 ms on a
1k-node/6k-arc terminal; 30 fps rendering of 300 tanks / 3000 pipes on a mid-range phone; solver time
limit configurable with incumbent progress streaming. Pairwise O(J^2 R^2) conflict modeling MUST NOT
be used beyond dozens of jobs; per-element interval modeling is required for scale.

### VII. Mobile-First, Simple by Default
UI MUST work with touch and responsive layouts (PWA). Start with the simplest design that meets a
requirement (YAGNI); added complexity MUST be justified in the plan's complexity table.

## Technology & Domain Constraints

- Backend: Python 3.12, FastAPI, Pydantic v2, OR-Tools CP-SAT, networkx (rustworkx when profiling
  demands it). Alternatives require a documented decision.
- Frontend: TypeScript, React, Vite, PixiJS (2D); three.js only for the optional 3D view.
- Simulation core: TypeScript discrete-event engine in a Web Worker, shared by browser and tests.
- Persistence: PostgreSQL (JSONB for versioned documents); Redis for job queueing.
- Security: OIDC authentication, role-based access, no secrets in the repository, input validated
  at every API boundary (OWASP Top 10 applies).
- Integrations (D365, SCADA) MUST sit behind adapter interfaces so core engines stay independent.

## Development Workflow & Quality Gates

- Work follows Spec Kit: specify, clarify, plan, tasks, implement; one spec per MVP phase.
- Every plan MUST include a Constitution Check against these principles.
- A change merges only when tests pass, oracles hold, schema changes are versioned, and docs in
  `docs/` that describe the changed behaviour are updated.
- Structured logging and OpenTelemetry traces are required for API and solver workers.

## Governance

This constitution supersedes other practices. Amendments require a written proposal, update of the
Sync Impact Report, a version bump per semantic versioning (MAJOR for incompatible principle
changes, MINOR for added or expanded principles, PATCH for clarifications), and a migration note for
affected specs and plans. All reviews MUST verify compliance; deviations MUST be recorded in the
plan's complexity table with justification. Runtime guidance lives in `docs/README.md`.

**Version**: 1.0.0 | **Ratified**: 2026-10-08 | **Last Amended**: 2026-10-08

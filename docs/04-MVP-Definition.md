# 04 MVP Definition

## In scope
1. Designer: drag/drop of all equipment types, property panel, undo/redo, validation, JSON + CSV import/export.
2. Graph build with validation report.
3. Single-job routing (Stage 1) with explanations and route highlight.
4. Multi-job optimization (Stage 1 + Stage 2) reproducing the reference sample (objective 1327).
5. Availability updates by REST (manual form + JSON upload).
6. Gantt + schematic playback of the plan.
7. Responsive layout, installable PWA, touch gestures.

## Out of scope for MVP
D365/SCADA live adapters, 3D view, AnyLogic-equivalent full simulation (Phase 7), AI features.

## Acceptance
| ID | Criterion |
|---|---|
| MVP-1 | Reference sample loaded from JSON; solver returns status OPTIMAL, objective 1327, all jobs on time |
| MVP-2 | A 300-tank / 3000-pipe synthetic terminal loads and renders at >= 30 fps on a mid-range phone |
| MVP-3 | Single-job route returned in < 1 s on that terminal |
| MVP-4 | Marking a pipe unavailable changes the route and the explanation names the pipe |
| MVP-5 | CSV and JSON import of the same terminal give identical graphs |

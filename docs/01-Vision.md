# 01 Vision

## Vision statement
Any terminal operator can draw or import their terminal in minutes and immediately get trustworthy, explainable, optimal line-ups and a simulation they can show to management.

## Principles
1. **Data-driven, not hard-coded.** The reference script hard-codes its terminal; LiquidTwin loads everything from a design document.
2. **Physics-aware.** Velocity, friction, lift, pump head, flushing and changeover are first-class.
3. **Explainable.** Every rejected pipe or route reports the reason (certification, velocity, residue, pump head, maintenance, stock).
4. **One model, three consumers.** Designer, optimizer and simulator share the same terminal document.
5. **Mobile-first, desktop-capable.** Touch gestures, responsive panels, PWA.
6. **Reproducible.** Fixed seeds, versioned documents, regression oracle (objective 1327).

## Personas
| Persona | Needs |
|---|---|
| Terminal planner | Quick route for a job, what-if on maintenance |
| Operations supervisor (mobile) | See live line-ups, availability, approve plan |
| Engineer | Design/import terminal, tune hydraulics and changeover |
| Manager | Simulation and KPIs |

## Requirement traceability
| Brief point | Covered in |
|---|---|
| 1 Visual design / import, equipment types, pipe attributes, changeover | 06, 07, 14 |
| 2 Availability updates | 14, 15, 16, 17 |
| 3 Precise graph, shortest route | 08, 09 |
| 4 Scale, line-up algorithm, ins and outs | 09, 10, 11, 18 |
| 5 Oil terminal simulation | 12 |
| 6 AnyLogic replication, same or better quality | 12, 13 |
| 7 Routing planner for inbound/outbound | 09, 15, 13 |

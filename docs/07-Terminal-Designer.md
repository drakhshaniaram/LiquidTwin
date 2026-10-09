# 07 Terminal Designer

## Goals
Draw or import a terminal of ~1000 nodes and ~5000 edges, edit it comfortably on desktop and tablet, and validate it continuously.

## Modes
1. **Manual:** palette -> drag onto canvas -> connect by dragging from a port.
2. **Import:** JSON (canonical) or CSV bundle ([14](14-Data-Model.md)); auto-layout when no coordinates are given.
3. **Hybrid:** import, then edit.

## Canvas
- PixiJS stage with pan (drag/two-finger), zoom (wheel/pinch), box select, snap-to-grid, orthogonal routing of pipes (editable waypoints), minimap.
- Level-of-detail: at far zoom draw tank groups and aggregated common headers; at near zoom draw valves, pumps, labels.
- Layers (toggle): tanks, pipes, valves, pumps, jetties, rail, availability overlay, product color overlay, elevation overlay.
- Pipe styling: underground dashed, aboveground solid, thickness by diameter, color by residue/product.

## Interactions
| Action | Desktop | Touch |
|---|---|---|
| Place item | drag from palette | long-press palette, tap to place |
| Connect | drag port to port | tap port, tap target |
| Multi-select | shift/box | two-finger lasso mode |
| Edit properties | right panel | bottom sheet |
| Undo/redo | Ctrl+Z/Y | buttons |
| Groups | Ctrl+G | action menu |
| Bulk edit | table view with filter | table view |

## Property panels
Typed forms from JSON Schema (single source of truth). Computed read-only fields: cross-section area, volume, velocity at design rate.

## Validation (live, non-blocking)
Dangling pipe; tank without header; header attached to more than one tank; duplicate ids; unit sanity (diameter, length); product not certified anywhere on a path to a loading point; pump direction conflicts; isolated components. Output is a list of `{severity, element_id, code, message, fix_hint}`.

## Features
Templates (tank farm, jetty manifold), copy/paste with id remap, auto-layout (ELK layered), version history with diff, import mapping wizard for CSV columns, export PNG/SVG/JSON/CSV.

## Acceptance
Place 1000 nodes and 5000 edges with <100 ms interaction latency; import of the sample terminal reproduces graph exactly; undo/redo depth >= 200.

# 00 Executive Summary

## Product
LiquidTwin is a mobile-friendly web application in which a user (1) designs an oil/liquid-bulk terminal visually or by import, (2) gets a precise graph of the terminal, (3) requests the quickest feasible route (line-up) for an inbound or outbound operation, (4) optimizes many concurrent jobs, and (5) replays the result in a high-fidelity simulation.

## Source material and what each drives
| Source | Drives |
|---|---|
| User brief (7 points) | Scope, domain model, designer, availability feed |
| `lineup_cpsat.py` (reference) | Docs 08-11. Two-stage optimizer. Reference result: objective **1327**, all 4 jobs on time. It is the regression oracle |
| AnyLogic "Oil Terminal - Version 14" | Doc 12. Behavioural reference for the simulation |
| `LiquidScheduler-sim.html` | Visual/animation baseline (to be exceeded) |

## Key decisions
| Topic | Decision | Reason |
|---|---|---|
| Solver backend | **Python 3.12 + FastAPI + OR-Tools CP-SAT** | OR-Tools' reference API is Python; the reference script is already Python; solver time dominates, not language |
| Graph library | networkx for MVP, rustworkx for scale | Same API shape, 10-100x faster on k-shortest paths |
| Frontend | **TypeScript + React + Vite + PixiJS (2D WebGL)**; three.js for optional 3D view | See doc 13 |
| Simulation | Deterministic discrete-event engine in TypeScript, running in a Web Worker | Must run in the browser, replicate AnyLogic |
| Import | Canonical JSON (JSON Schema) + CSV bundle | Doc 14 |
| Persistence | PostgreSQL (JSONB for design documents) | Doc 14 |
| Availability feed | REST/webhook, D365 and SCADA adapters | Docs 16, 17 |

## Scale targets
Hundreds of tanks, thousands of pipelines, 50-100 loading points, hundreds of valves, about 50 jetties; dozens (later hundreds) of concurrent jobs.

## Document map
See [README](README.md). Every requirement in the brief is traced in the matrix at the end of [01-Vision](01-Vision.md).

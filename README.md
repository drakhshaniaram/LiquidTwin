# LiquidTwin — Liquid Bulk Jetty Terminal Digital Twin

Interactive liquid bulk terminal scheduler simulation with berth / channel / tug / loading-arm / pipeline / tank-inventory constrained schedule optimization.

**Live demo:** open `LiquidScheduler-sim.html` (or `index.html`) in a browser — no build step required. Or serve locally:

```bash
npm run serve
# → http://localhost:8790
```

## Features

- **Berth-constrained scheduling** — 4–5 berths with LOA / draft / rate / product-family compatibility
- **Tidal channel windows** — UKC-gated draft windows from M2 tide model + channel depth
- **Tug fleet dispatch** — 1–2 tugs per move depending on vessel size, with turnaround
- **Loading arms & headers** — family-dedicated arms, flush/pigging changeover matrices
- **Tank inventory coupling** — per-product tank farm with shore in/out flows, heated black products
- **Optimizers** — FCFS baseline, greedy dispatch (EST + cost look-ahead), simulated annealing, genetic algorithm + local search
- **Objective presets** — balanced / idle / throughput / demurrage-cost weightings
- **Domain config** — all constants in [`src/config.js`](src/config.js): products, vessel classes, berths, ops durations, defaults

## Project layout

| File | Purpose |
|---|---|
| `LiquidScheduler-sim.html` | Self-contained interactive simulation (main artifact) |
| `index.html` | Copy of the sim for static hosting (e.g. GitHub Pages) |
| `src/config.js` | Domain constants: products, vessels, berths, ops, algorithm + objective presets |
| `package.json` | `serve` (local HTTP) and `test` scripts |

## Usage

1. Open `LiquidScheduler-sim.html` in any modern browser.
2. Tune vessels, berths, tugs, tide, pipeline mode, arrival pattern, objective weights.
3. Run FCFS / Greedy / SA / GA and compare idle time, throughput, and demurrage cost.

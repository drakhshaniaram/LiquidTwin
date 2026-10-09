# 12 Simulation Engine

## Goal
Replicate the AnyLogic "Oil Terminal - Version 14" behaviour in the browser, with equal or better fidelity and visuals. The same engine later replays optimizer plans on user-designed terminals.

## What the AnyLogic model contains (extracted from `Oil Terminal.alp`)
Agent classes: `Main`, `Train`, `RailCar`, `Tanker`, `TankOfTanker`, `TugBoat`, `Platform`, `TrainMoveAndUnload`, `OilStorage`, `Piping`.

| AnyLogic element | Role | Web equivalent |
|---|---|---|
| `trainSource`, `trainDispose`, `trainMoveToExit` | Train arrivals (rate/interarrival, car count, capacity, per-type oil) and exit | `TrainSource` process |
| `railroadEntry`, `seizeEntry`, `platformsPool`, `seizePlatform`, `releasePlatforms` | Platform allocation by oil type | Resource pool with type-keyed queue |
| `dieselFuelPlatform`, `petrolPlatform`, `fuelOilPlatform`, `crudeOilPlatform` (`TrainMoveAndUnload`: `trainMoveTo`, `oilDropoff`, `releaseTrack`, `timeMeasureStart/End`) | Move train to track, discharge oil, release track, measure unload time | `PlatformUnload` process |
| `OilStorage` (`tank`, `pipeInput`, `pipeOutput`, `valveIn`, `valveOut`) | Tank with in/out pipes and valves | `StorageTank` entity (valves as gates) |
| `Piping` (`fluidSplit`, `oilMerge`, `pipeInput1-4`, `pipeOutput1-4`, `tank1-4`, `connectToTankerTank`, `disconnectTank`) | Per-farm loading and discharging piping systems | `PipingSystem` subgraph |
| `dieselFuelPiping`, `petrolPiping`, `fuelOilPiping`, `crudeOilPiping` | Four tank farms | Four farm instances |
| `tankerSource`, `arrival`, `mooring`, `seizeTugsIn`, `tugsPool`, `pushing`, `getTowRopes`, `releaseTugs` | Tanker arrival, towing in by 3 tugs, mooring | `TankerArrival` + tug resource (capacity 3) |
| `tankerLoadingStart/End`, `loading`, `connectTankerToPipings`, `startLoading`, `finishLoading`, `calculateAvailableAmountOfOil` | Load each carried tank from the matching farm | `TankerLoading` process |
| `unmooring`, `seizeTugsOut`, `towingOut`, `releaseTugsOut`, `departure`, `tankerDispose` | Pull-out and departure | `TankerDeparture` |
| `restrictedAreaStart/End`, `selectOutput5`, `hold*` | Exclusion zone and gating | Zone mutex |
| `toggleStorm`, `switchCamera`, `getBatchColor`, `resetStatistics` | Storm effect, cameras, batch coloring, stats reset | UI features |
| 3D assets (`tankcar`, `locomotive`, `oil_tanker_2`, `tug`, `fence`, ...) | Visuals | glTF conversion for three.js view |

## Behavioural spec (from the brief)
- Two two-sided platforms (light, black); 4 trains discharge simultaneously; each train carries one oil type; arrives at the platform for its type.
- Four tank farms (diesel, petrol, fuel oil, crude); each tank holds one oil type; each farm has separate loading and discharging piping.
- Tanker berths with 3 tugs, stays until all carried tanks are filled (each tank one oil type), is pulled out, departs.
- Runtime-editable: train capacity and interarrival time, tanker tank count and tank capacity.

## Engine design
- **Discrete-event core** (`packages/sim-core`): priority-queue calendar, seeded PRNG, processes as generators/async state machines, resources with queues, continuous flow integrated in time steps for fluid (tank levels = integral of in/out flow; events on level thresholds).
- **Runs in a Web Worker**; main thread receives snapshots at 30 Hz (interpolated).
- Speed control 0.1x-1000x, pause, step, reset, scenario save/load, deterministic replay.
- **Statistics:** tank utilization, platform utilization, train unload time, tanker berth time, tug utilization, throughput per oil type, queue lengths; charts and CSV export.
- **Fluid model:** tank, pipe flow rate = min(pump capacity, source rate, sink acceptance); valves gate flows.

## Scenario modes
1. `oil-terminal-ref`: AnyLogic reference scenario, fixed layout.
2. `designed-terminal`: any TerminalDocument with jobs from an optimizer plan or arrival generators.

## Validation against AnyLogic
Run AnyLogic with the same seed-independent deterministic inputs (fixed arrivals); compare KPIs (unload times, tanker berth time, tank levels over time). Accept deviation <= 2% on means over 30 runs. Export AnyLogic statistics as CSV for golden files.

## Better than the reference
Higher visual fidelity (see [13](13-Visualization-Engine.md)), mobile support, scenario comparison, optimizer-driven operations, what-if with availability, shareable URLs.

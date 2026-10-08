// Domain constants. Units: hours, m³, m³/h, metres, USD.

export const FAMILIES = ["light", "middle", "black"];

export const PRODUCTS = [
  { id: "GAS", name: "Gasoline 95", family: "light", color: "#22c55e", roof: "EFR", shoreRate: 2600, netFlow: 340, tanks: [42000, 42000, 36000] },
  { id: "NAP", name: "Naphtha", family: "light", color: "#a855f7", roof: "EFR", shoreRate: 2200, netFlow: 210, tanks: [32000, 32000] },
  { id: "JET", name: "Jet A-1", family: "middle", color: "#38bdf8", roof: "IFR", shoreRate: 1800, netFlow: -240, tanks: [30000, 30000] },
  { id: "ULSD", name: "Diesel ULSD", family: "middle", color: "#f59e0b", roof: "CR", shoreRate: 2600, netFlow: 280, tanks: [42000, 42000, 36000] },
  { id: "HSFO", name: "Fuel oil 3.5%S", family: "black", color: "#a8a29e", roof: "CR", shoreRate: 1500, netFlow: 110, tanks: [34000, 34000], heated: true },
];

// Arm drain/flush hours when an arm switches product [from][to] (same family only; arms are family-dedicated).
export const ARM_FLUSH = {
  GAS: { GAS: 0, NAP: 1.0 },
  NAP: { NAP: 0, GAS: 2.0 },
  JET: { JET: 0, ULSD: 1.0 },
  ULSD: { ULSD: 0, JET: 4.0 },
  HSFO: { HSFO: 0 },
};

// Line displacement / pigging hours on a shared family header [from][to].
export const LINE_PIG = {
  GAS: { GAS: 0, NAP: 2.5 },
  NAP: { NAP: 0, GAS: 3.5 },
  JET: { JET: 0, ULSD: 2.5 },
  ULSD: { ULSD: 0, JET: 6.0 },
  HSFO: { HSFO: 0 },
};

export const VESSEL_CLASSES = [
  { id: "COASTER", name: "Coastal tanker", loa: 105, beam: 17.2, depth: 9.0, ballastDraft: 3.8, maxDraft: 7.2, cargo: 9500, pump: 750, laytime: 24, demDay: 12000, tugs: 1, weight: 0.24 },
  { id: "HANDY", name: "Handysize tanker", loa: 146, beam: 24.0, depth: 13.0, ballastDraft: 5.0, maxDraft: 9.8, cargo: 23000, pump: 1300, laytime: 30, demDay: 18000, tugs: 1, weight: 0.3 },
  { id: "MR", name: "MR tanker", loa: 183, beam: 32.2, depth: 19.0, ballastDraft: 6.4, maxDraft: 12.2, cargo: 46000, pump: 2100, laytime: 36, demDay: 24000, tugs: 2, weight: 0.34 },
  { id: "LR1", name: "LR1 tanker", loa: 228, beam: 32.2, depth: 20.5, ballastDraft: 7.2, maxDraft: 13.6, cargo: 68000, pump: 2800, laytime: 48, demDay: 32000, tugs: 2, weight: 0.12 },
];

export const BERTH_TEMPLATES = [
  { id: "B1", name: "Berth 1", maxLoa: 240, maxDraft: 14.5, maxRate: 3000, families: ["light", "middle"] },
  { id: "B2", name: "Berth 2", maxLoa: 200, maxDraft: 12.8, maxRate: 2600, families: ["light", "middle", "black"] },
  { id: "B3", name: "Berth 3", maxLoa: 160, maxDraft: 10.5, maxRate: 1800, families: ["middle", "black"] },
  { id: "B4", name: "Berth 4", maxLoa: 125, maxDraft: 8.2, maxRate: 1200, families: ["light", "middle", "black"] },
  { id: "B5", name: "Berth 5", maxLoa: 250, maxDraft: 15.0, maxRate: 3200, families: ["light", "middle"] },
];

// Operational durations (h).
export const OPS = {
  inbound: { small: 1.3, large: 1.7 },  // anchorage → all-fast transit + tug-assisted berthing
  outbound: { small: 1.0, large: 1.3 }, // let go → channel exit
  moor: 0.7,          // lines, gangway, all fast
  connect: 1.3,       // arm connection, ship/shore safety checklist, sampling
  disconnect: 1.2,    // drain, disconnect, ullage + documents
  tugTurnaround: 0.6, // tug return / re-position after a job
  norToLaytime: 6,    // laytime starts NOR + 6 h or all fast, whichever first
  largeLoa: 170,
};

export const DEFAULT_SETTINGS = {
  seed: 7,
  nVessels: 22,
  horizon: 168,
  nBerths: 4,
  tugs: 3,
  channelDepth: 13.4,  // below MSL
  tideAmp: 1.6,        // M2 amplitude, m
  ukc: 0.10,           // under-keel clearance fraction of draft
  pipeline: "dedicated", // dedicated | shared | twin
  rateScale: 1.0,
  arrival: "bunched",  // uniform | bunched
  startHour: 6,        // clock time at t = 0
};

export const OBJECTIVE_PRESETS = {
  balanced: { idle: 5, throughput: 5, demurrage: 5 },
  idle: { idle: 10, throughput: 2, demurrage: 3 },
  throughput: { idle: 2, throughput: 10, demurrage: 2 },
  cost: { idle: 2, throughput: 2, demurrage: 10 },
};

export const ALGORITHMS = [
  { id: "fcfs", name: "FCFS baseline", short: "FCFS", color: "#94a3b8" },
  { id: "greedy", name: "Greedy dispatch (EST + cost look-ahead)", short: "Greedy", color: "#f59e0b" },
  { id: "sa", name: "Simulated annealing", short: "SA", color: "#22d3ee" },
  { id: "ga", name: "Genetic algorithm + local search", short: "GA", color: "#a78bfa" },
];

export const PRODUCT_BY_ID = Object.fromEntries(PRODUCTS.map((p) => [p.id, p]));
export const CLASS_BY_ID = Object.fromEntries(VESSEL_CLASSES.map((c) => [c.id, c]));

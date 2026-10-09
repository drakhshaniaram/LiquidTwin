"""No-route explanation: name the equipment that blocks the cheapest unfiltered path."""
from __future__ import annotations

import networkx as nx

from .types import Exclusion, ExclusionReason, NoRoute


def explain_no_route(unfiltered: nx.DiGraph, sources: list[str], destinations: list[str],
                     arc_exclusions: dict[tuple[str, bool], Exclusion], endpoint_exclusions: list[Exclusion],
                     pump_head_failed: bool) -> NoRoute:
    if not sources or not destinations:
        side = "source" if not sources else "destination"
        return NoRoute(f"No usable {side}: every candidate was excluded", list(endpoint_exclusions))
    best: list[str] | None = None
    for s in sources:
        for t in destinations:
            if s == t or s not in unfiltered or t not in unfiltered:
                continue
            try:
                p = nx.shortest_path(unfiltered, s, t, weight="weight")
            except nx.NetworkXNoPath:
                continue
            if best is None or len(p) < len(best):
                best = p
    if best is None:
        return NoRoute("Source and destination are not connected in the terminal", [])
    blockers: list[Exclusion] = []
    seen: set[str] = set()
    for u, v in zip(best, best[1:]):
        el_id = unfiltered[u][v]["element_id"]
        ex = arc_exclusions.get((el_id, unfiltered[u][v]["reversed"]))
        if ex is not None and el_id not in seen:
            seen.add(el_id)
            blockers.append(ex)
    if not blockers and pump_head_failed:
        blockers.append(Exclusion(ExclusionReason.PUMP_HEAD, "Available pumps cannot cover friction plus lift on any path"))
    msg = "No feasible route; the shortest physical path is blocked by the listed equipment" if blockers \
        else "No feasible route"
    return NoRoute(msg, blockers)

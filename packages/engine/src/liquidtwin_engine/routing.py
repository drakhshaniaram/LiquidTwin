"""Stage 1 routing: arc filtering, k shortest simple paths, pump head check, metrics, ranking, explanations."""
from __future__ import annotations

import itertools
from collections.abc import Sequence
from itertools import islice

import networkx as nx

from . import __version__
from .document import Element, Terminal, natural_key
from .explain import explain_no_route
from .graph import Arc, TerminalGraph
from .hydraulics import ArcMetrics, HydraulicsConfig, arc_metrics, transfer_minutes
from .types import AvailabilityWindow, Exclusion, Route, RouteMetrics, RouteRequest, RouteResult, RouteStep
from .types import ExclusionReason as R

ENGINE_VERSION = __version__
K_DEFAULT = 20
MAX_PARALLEL_COMBOS = 8
MAX_EXCLUSIONS = 500


def _unavailable_ids(windows: Sequence[AvailabilityWindow], t0: float, t1: float) -> dict[tuple[str, str], AvailabilityWindow]:
    out: dict[tuple[str, str], AvailabilityWindow] = {}
    for w in windows:
        if w.status == "AVAILABLE":
            continue
        if w.start_min < t1 and (w.end_min is None or w.end_min > t0):
            out.setdefault((w.kind, w.element_id), w)
    return out


def _arc_reason(t: Terminal, el: Element, arc: Arc, m: ArcMetrics, product, unavailable) -> Exclusion | None:
    pid = product.id
    if ("ELEMENT", el.id) in unavailable:
        w = unavailable[("ELEMENT", el.id)]
        return Exclusion(R.UNAVAILABLE, f"{el.id} is {w.status.lower().replace('_', ' ')} during the job window", el.id)
    if pid not in el.certified_products:
        return Exclusion(R.NOT_CERTIFIED, f"{el.id} is not certified for product {pid}", el.id)
    if el.dedicated_product_ids and pid not in el.dedicated_product_ids:
        return Exclusion(R.DEDICATED_OTHER_GROUP, f"{el.id} is dedicated to other products", el.id)
    if arc.reversed and el.type == "PUMP":
        return Exclusion(R.ONE_WAY_PUMP, f"{el.id} is a pump and cannot be traversed in reverse", el.id)
    if m.velocity > product.max_velocity:
        return Exclusion(R.VELOCITY, f"{el.id} velocity {m.velocity:.2f} m/s exceeds {product.max_velocity} m/s", el.id)
    res = el.residue_product_id
    if res is not None and res != pid:
        rule = t.changeover.get((res, pid))
        if rule is not None and rule.manual_clean_required:
            return Exclusion(R.RESIDUE, f"{el.id} holds residue of {res}; manual cleaning required before {pid}", el.id)
    return None


def _endpoints(t: Terminal, req: RouteRequest, unavailable) -> tuple[list[str], list[str], list[Exclusion]]:
    ex: list[Exclusion] = []
    srcs: list[str] = []
    dsts: list[str] = []
    for n in req.source_ids:
        node = t.nodes.get(n)
        if node is None:
            ex.append(Exclusion(R.ENDPOINT_PRODUCT, f"Unknown source {n}", node_id=n))
        elif ("NODE", n) in unavailable:
            ex.append(Exclusion(R.UNAVAILABLE, f"{n} is unavailable during the job window", node_id=n))
        elif node.type == "TANK":
            if node.product_id != req.product_id:
                ex.append(Exclusion(R.ENDPOINT_PRODUCT, f"Tank {n} holds {node.product_id}, not {req.product_id}", node_id=n))
            elif node.stock_m3 < req.volume_m3:
                ex.append(Exclusion(R.ENDPOINT_STOCK, f"Tank {n} stock {node.stock_m3} < {req.volume_m3} m3", node_id=n))
            elif not node.allow_outbound:
                ex.append(Exclusion(R.ENDPOINT_DIRECTION, f"Tank {n} does not allow outbound operations", node_id=n))
            else:
                srcs.append(n)
        else:
            srcs.append(n)
    for n in req.destination_ids:
        node = t.nodes.get(n)
        if node is None:
            ex.append(Exclusion(R.ENDPOINT_PRODUCT, f"Unknown destination {n}", node_id=n))
        elif ("NODE", n) in unavailable:
            ex.append(Exclusion(R.UNAVAILABLE, f"{n} is unavailable during the job window", node_id=n))
        elif node.type == "TANK":
            if node.product_id not in (None, req.product_id):
                ex.append(Exclusion(R.ENDPOINT_PRODUCT, f"Tank {n} holds {node.product_id}, not {req.product_id}", node_id=n))
            elif node.capacity_m3 - node.stock_m3 < req.volume_m3:
                ex.append(Exclusion(R.ENDPOINT_SPACE, f"Tank {n} free space {node.capacity_m3 - node.stock_m3} < {req.volume_m3} m3", node_id=n))
            elif not node.allow_inbound:
                ex.append(Exclusion(R.ENDPOINT_DIRECTION, f"Tank {n} does not allow inbound operations", node_id=n))
            else:
                dsts.append(n)
        else:
            dsts.append(n)
    return srcs, dsts, ex


def route_job(graph: TerminalGraph, req: RouteRequest, availability: Sequence[AvailabilityWindow] = (),
              cfg: HydraulicsConfig | None = None, k: int = K_DEFAULT) -> RouteResult:
    t = graph.terminal
    cfg = cfg or HydraulicsConfig()
    product = t.products.get(req.product_id)
    if product is None:
        raise ValueError(f"Unknown product {req.product_id}")
    transfer = transfer_minutes(req.volume_m3, req.rate_m3h)
    t0 = req.window_from_min
    t1 = req.window_to_min if req.window_to_min is not None else t0 + transfer
    unavailable = _unavailable_ids(availability, t0, t1)

    G = nx.DiGraph()        # filtered, cheapest arc per node pair (reference behaviour)
    U = nx.DiGraph()        # unfiltered by reason, for no-route explanation
    alts: dict[tuple[str, str], list[tuple[float, Arc, ArcMetrics]]] = {}
    arc_ex: dict[tuple[str, bool], Exclusion] = {}
    for arc in graph.arcs:
        el = t.elements[arc.element_id]
        m = arc_metrics(t, el, arc.reversed, product, req.rate_m3h, cfg)
        cost = m.fill_min + m.flush_min + 1
        if not U.has_edge(arc.u, arc.v) or U[arc.u][arc.v]["weight"] > el.length_m + 1:
            U.add_edge(arc.u, arc.v, weight=el.length_m + 1, element_id=el.id, reversed=arc.reversed)
        reason = _arc_reason(t, el, arc, m, product, unavailable)
        if reason is not None:
            arc_ex.setdefault((el.id, arc.reversed), reason)
            continue
        alts.setdefault((arc.u, arc.v), []).append((cost, arc, m))
        if not G.has_edge(arc.u, arc.v) or G[arc.u][arc.v]["weight"] > cost:
            G.add_edge(arc.u, arc.v, weight=cost)

    srcs, dsts, ep_ex = _endpoints(t, req, unavailable)
    candidates: list[tuple[str, str, list[tuple[Arc, ArcMetrics]]]] = []
    pump_head_failed = False
    for s in srcs:
        for d in dsts:
            if s == d or s not in G or d not in G:
                continue
            try:
                paths = list(islice(nx.shortest_simple_paths(G, s, d, weight="weight"), k))
            except nx.NetworkXNoPath:
                continue
            for p in paths:
                hops = [sorted(alts[(a, b)], key=lambda x: (x[0], natural_key(x[1].element_id)))
                        for a, b in zip(p, p[1:])]
                for combo in islice(itertools.product(*hops), MAX_PARALLEL_COMBOS):
                    chosen = [(arc, m) for _, arc, m in combo]
                    if sum(m.pump_dm - m.need_dm for _, m in chosen) < 0:
                        pump_head_failed = True
                        continue
                    if not _group_ok(t, chosen, s, d, arc_ex):
                        continue
                    candidates.append((s, d, chosen))

    routes = [_make_route(t, s, d, chosen, transfer) for s, d, chosen in candidates]
    routes.sort(key=lambda r: (r.metrics.total_min, r.metrics.flush_volume_m3, r.metrics.valves,
                               r.metrics.common_headers, [natural_key(x) for x in r.element_ids]))
    limit = max(1, req.max_routes)
    ranked = [Route(i + 1, r.source_id, r.destination_id, r.steps, r.metrics) for i, r in enumerate(routes[:limit])]

    exclusions: list[Exclusion] = []
    seen_el: set[str] = set()
    for (el_id, _rev), ex in arc_ex.items():
        if el_id not in seen_el:
            seen_el.add(el_id)
            exclusions.append(ex)
    exclusions = exclusions[:MAX_EXCLUSIONS] + ep_ex
    result = RouteResult(routes=ranked, exclusions=exclusions)
    if not ranked:
        result.no_route = explain_no_route(U, srcs or [], dsts or [], arc_ex, ep_ex, pump_head_failed)
    return result


def _group_ok(t: Terminal, chosen, s: str, d: str, arc_ex: dict[tuple[str, bool], Exclusion]) -> bool:
    groups = {t.nodes[n].group_id for n in (s, d) if n in t.nodes and t.nodes[n].type == "TANK"}
    groups.discard(None)
    ok = True
    for arc, _ in chosen:
        el = t.elements[arc.element_id]
        if el.dedicated_group_id and groups and el.dedicated_group_id not in groups:
            arc_ex.setdefault((el.id, arc.reversed), Exclusion(R.DEDICATED_OTHER_GROUP,
                                               f"{el.id} is dedicated to tank group {el.dedicated_group_id}", el.id))
            ok = False
    return ok


def _make_route(t: Terminal, s: str, d: str, chosen, transfer: int) -> Route:
    steps = tuple(RouteStep(a.element_id, a.u, a.v, a.reversed) for a, _ in chosen)
    fill = sum(m.fill_min for _, m in chosen)
    ft = sum(m.flush_min for _, m in chosen)
    fv = sum(m.flush_volume for _, m in chosen)
    types = [t.elements[a.element_id].type for a, _ in chosen]
    metrics = RouteMetrics(
        fill_min=fill, transfer_min=transfer, flush_min=ft, flush_volume_m3=fv, total_min=transfer + fill + ft,
        valves=types.count("VALVE"), common_headers=types.count("COMMON_HEADER"),
        head_margin_m=sum(m.pump_dm - m.need_dm for _, m in chosen) / 10,
        max_velocity_ms=max((m.velocity for _, m in chosen), default=0.0))
    return Route(0, s, d, steps, metrics)

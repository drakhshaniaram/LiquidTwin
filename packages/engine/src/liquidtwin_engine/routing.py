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
from .hydraulics import (
    ArcMetrics,
    HydraulicsConfig,
    OperatingPoint,
    TWO_G,
    area_m2,
    arc_metrics,
    find_operating_point_from_functions,
    pump_train_head,
    transfer_minutes,
    velocity_ms,
)
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


def _curve_route_metrics(
    t: Terminal,
    chosen: list[tuple[Arc, ArcMetrics]],
    req: RouteRequest,
    product,
    cfg: HydraulicsConfig,
) -> tuple[list[tuple[Arc, ArcMetrics]], OperatingPoint | None, float | None, Exclusion | None]:
    path_pump_ids = {
        arc.element_id
        for arc, _ in chosen
        if t.elements[arc.element_id].type == "PUMP"
        and t.elements[arc.element_id].performance_curve is not None
    }
    if not path_pump_ids:
        return chosen, None, None, None

    trains_by_member = {
        member_id: train
        for train in t.pump_trains.values()
        for member_id in train.member_pump_ids
    }
    stages: list[tuple[str, list[dict]]] = []
    stage_ids: set[str] = set()
    curve_pumps_by_id: dict[str, Element] = {}
    curves_by_pump_id: dict[str, dict] = {}
    for arc, _ in chosen:
        element = t.elements[arc.element_id]
        train = trains_by_member.get(element.id)
        if train is not None:
            if train.id in stage_ids:
                continue
            members = [t.elements[member_id] for member_id in train.member_pump_ids]
            member_curves = [member.performance_curve for member in members]
            if any(curve is None for curve in member_curves):
                return chosen, None, None, Exclusion(
                    R.INVALID_PUMP_CURVE,
                    f"Pump train {train.id} contains a member without a performance curve",
                    train.id,
                )
            curves = [curve for curve in member_curves if curve is not None]
            if train.arrangement == "SERIES" and not set(train.member_pump_ids) <= path_pump_ids:
                return chosen, None, None, Exclusion(
                    R.PUMP_FLOW_OUT_OF_RANGE,
                    f"Series pump train {train.id} is incomplete on this route",
                    train.id,
                )
            if train.arrangement == "PARALLEL" and len({(m.from_node, m.to_node) for m in members}) != 1:
                return chosen, None, None, Exclusion(
                    R.INVALID_PUMP_CURVE,
                    f"Parallel pump train {train.id} members must share the same directed endpoints",
                    train.id,
                )
            stages.append((train.arrangement, curves))
            stage_ids.add(train.id)
            curve_pumps_by_id.update({member.id: member for member in members})
            curves_by_pump_id.update({member.id: curve for member, curve in zip(members, curves)})
        elif element.performance_curve is not None:
            stages.append(("SERIES", [element.performance_curve]))
            curve_pumps_by_id[element.id] = element
            curves_by_pump_id[element.id] = element.performance_curve

    suction_inputs = dict(req.pump_suction_inputs)
    suction_margins: list[float] = []
    for pump in curve_pumps_by_id.values():
        available = suction_inputs.get(pump.id)
        required = pump.npsh_required_m
        margin = pump.npsh_margin_m
        if available is None or required is None:
            detail = (
                f"{pump.id} needs a required suction head and an available suction input; "
                f"provided {available if available is not None else 'none'}"
            )
            return chosen, None, None, Exclusion(R.PUMP_SUCTION_MARGIN, detail, pump.id)
        required_with_margin = required + margin
        if available < required_with_margin:
            detail = (
                f"{pump.id} needs available suction head >= {required_with_margin:.2f} m; "
                f"provided {available:.2f} m"
            )
            return chosen, None, None, Exclusion(R.PUMP_SUCTION_MARGIN, detail, pump.id)
        suction_margins.append(available - required_with_margin)

    stage_flow_ranges: list[tuple[float, float]] = []
    for arrangement, curves in stages:
        if arrangement == "SERIES":
            stage_minimum = max(curve["min_flow_m3h"] for curve in curves)
            stage_maximum = min(curve["max_flow_m3h"] for curve in curves)
        else:
            stage_minimum = sum(curve["min_flow_m3h"] for curve in curves)
            stage_maximum = sum(curve["max_flow_m3h"] for curve in curves)
        stage_flow_ranges.append((stage_minimum, stage_maximum))
    minimum_speed = max(
        curve["speed_ratio_min"] for curve in curves_by_pump_id.values()
    )
    maximum_speed = min(
        curve["speed_ratio_max"] for curve in curves_by_pump_id.values()
    )
    limiting_pump_id = min(
        curves_by_pump_id, key=lambda pump_id: curves_by_pump_id[pump_id]["max_flow_m3h"]
    )
    if minimum_speed > maximum_speed:
        return chosen, None, None, Exclusion(
            R.PUMP_SPEED_OUT_OF_RANGE,
            "Pump train members have no common permitted speed ratio",
            limiting_pump_id,
        )

    fixed_head = sum(
        element.head_m
        for arc, _ in chosen
        if (element := t.elements[arc.element_id]).type == "PUMP"
        and element.performance_curve is None
        and not arc.reversed
    )
    maximum_line_flow = float("inf")
    for arc, _ in chosen:
        element = t.elements[arc.element_id]
        if element.type == "PUMP" and element.max_flow_m3h is not None:
            if element.max_flow_m3h < maximum_line_flow:
                maximum_line_flow = element.max_flow_m3h
                limiting_pump_id = element.id
        if element.diameter_mm > 0:
            install_factor = cfg.installation_factor.get(element.installation, 1.0)
            max_velocity_flow = product.max_velocity * area_m2(element.diameter_mm) * 3600 / install_factor
            maximum_line_flow = min(maximum_line_flow, max_velocity_flow)

    def pump_head(flow: float, speed_ratio: float) -> float | None:
        total = fixed_head
        for arrangement, curves in stages:
            head = pump_train_head(curves, arrangement, flow, speed_ratio)
            if head is None:
                return None
            total += head
        return total

    def system_head(flow: float) -> float:
        total = 0.0
        for arc, _ in chosen:
            element = t.elements[arc.element_id]
            velocity = velocity_ms(flow, element.diameter_mm, element.installation, cfg)
            elevation = -element.elevation_delta_m if arc.reversed else element.elevation_delta_m
            total += (
                product.friction_factor
                * element.length_m
                / (element.diameter_mm / 1000)
                * velocity**2
                / TWO_G
                + elevation
            )
        return total

    def operating_at_speed(speed_ratio: float) -> OperatingPoint | None:
        minimum_flow = max(
            req.rate_m3h,
            *(minimum * speed_ratio for minimum, _ in stage_flow_ranges),
        )
        maximum_flow = min(
            maximum_line_flow,
            *(maximum * speed_ratio for _, maximum in stage_flow_ranges),
        )
        if minimum_flow > maximum_flow:
            return None
        return find_operating_point_from_functions(
            lambda flow: pump_head(flow, speed_ratio), system_head, minimum_flow, maximum_flow
        )

    operating_point = operating_at_speed(minimum_speed)
    speed_ratio = minimum_speed
    if operating_point is None:
        operating_point = operating_at_speed(maximum_speed)
        if operating_point is None:
            minimum_flow = max(
                req.rate_m3h,
                *(minimum * maximum_speed for minimum, _ in stage_flow_ranges),
            )
            maximum_flow = min(
                maximum_line_flow,
                *(maximum * maximum_speed for _, maximum in stage_flow_ranges),
            )
            if minimum_flow > maximum_flow:
                return chosen, None, None, Exclusion(
                    R.PUMP_FLOW_OUT_OF_RANGE,
                    f"Requested minimum flow {req.rate_m3h:g} m3/h exceeds the usable pump/line range ending at {maximum_flow:.2f} m3/h",
                    limiting_pump_id,
                )
            return chosen, None, None, Exclusion(
                R.NO_PUMP_SYSTEM_INTERSECTION,
                f"No pump/system operating point meets the minimum {req.rate_m3h:g} m3/h within the declared flow and speed ranges",
                limiting_pump_id,
            )
        low, high = minimum_speed, maximum_speed
        for _ in range(40):
            candidate_speed = (low + high) / 2
            candidate = operating_at_speed(candidate_speed)
            if candidate is None:
                low = candidate_speed
            else:
                high = candidate_speed
                operating_point = candidate
        speed_ratio = high

    if operating_point is None:
        return chosen, None, None, Exclusion(
            R.PUMP_FLOW_OUT_OF_RANGE,
            f"Requested minimum flow {req.rate_m3h:g} m3/h exceeds the usable pump/line range ending at {maximum_line_flow:.2f} m3/h",
            limiting_pump_id,
        )
    operating_point = OperatingPoint(
        operating_point.flow_m3h,
        pump_head(operating_point.flow_m3h, speed_ratio) or 0.0,
        operating_point.system_head_m,
        speed_ratio,
    )
    operating_arcs = [
        (arc, arc_metrics(t, t.elements[arc.element_id], arc.reversed, product, operating_point.flow_m3h, cfg))
        for arc, _ in chosen
    ]
    return operating_arcs, operating_point, min(suction_margins), None


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
    candidates: list[tuple[str, str, list[tuple[Arc, ArcMetrics]], int, OperatingPoint | None, float | None]] = []
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
                    has_curve_pump = any(
                        t.elements[arc.element_id].performance_curve is not None
                        for arc, _ in chosen
                    )
                    if not has_curve_pump and sum(m.pump_dm - m.need_dm for _, m in chosen) < 0:
                        pump_head_failed = True
                        continue
                    if not _group_ok(t, chosen, s, d, arc_ex):
                        continue
                    route_arcs = chosen
                    operating_point = None
                    suction_margin = None
                    route_transfer = transfer
                    if has_curve_pump:
                        route_arcs, operating_point, suction_margin, curve_exclusion = _curve_route_metrics(
                            t, chosen, req, product, cfg
                        )
                        if curve_exclusion is not None:
                            arc_ex.setdefault((curve_exclusion.element_id or "", False), curve_exclusion)
                            continue
                        if operating_point is not None:
                            route_transfer = transfer_minutes(req.volume_m3, operating_point.flow_m3h)
                    candidates.append((s, d, route_arcs, route_transfer, operating_point, suction_margin))

    routes = [
        _make_route(t, s, d, chosen, route_transfer, operating_point, suction_margin)
        for s, d, chosen, route_transfer, operating_point, suction_margin in candidates
    ]
    routes.sort(key=lambda r: (r.metrics.total_min, r.metrics.flush_volume_m3, r.metrics.valves,
                               r.metrics.common_headers, [natural_key(x) for x in r.element_ids]))
    limit = max(1, req.max_routes)
    ranked = [Route(i + 1, r.source_id, r.destination_id, r.steps, r.metrics) for i, r in enumerate(routes[:limit])]

    exclusions: list[Exclusion] = []
    seen_exclusions: set[tuple[str, R]] = set()
    for (el_id, _rev), ex in arc_ex.items():
        exclusion_key = (el_id, ex.reason)
        if exclusion_key not in seen_exclusions:
            seen_exclusions.add(exclusion_key)
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


def _make_route(
    t: Terminal,
    s: str,
    d: str,
    chosen,
    transfer: int,
    operating_point: OperatingPoint | None = None,
    suction_margin: float | None = None,
) -> Route:
    steps = tuple(RouteStep(a.element_id, a.u, a.v, a.reversed) for a, _ in chosen)
    fill = sum(m.fill_min for _, m in chosen)
    ft = sum(m.flush_min for _, m in chosen)
    fv = sum(m.flush_volume for _, m in chosen)
    types = [t.elements[a.element_id].type for a, _ in chosen]
    metrics = RouteMetrics(
        fill_min=fill, transfer_min=transfer, flush_min=ft, flush_volume_m3=fv, total_min=transfer + fill + ft,
        valves=types.count("VALVE"), common_headers=types.count("COMMON_HEADER"),
        head_margin_m=(operating_point.pump_head_m - operating_point.system_head_m) if operating_point else
        sum(m.pump_dm - m.need_dm for _, m in chosen) / 10,
        max_velocity_ms=max((m.velocity for _, m in chosen), default=0.0),
        operating_flow_m3h=operating_point.flow_m3h if operating_point else None,
        pump_head_m=operating_point.pump_head_m if operating_point else None,
        system_head_m=operating_point.system_head_m if operating_point else None,
        suction_margin_m=suction_margin,
        pump_speed_ratio=operating_point.speed_ratio if operating_point else None)
    return Route(0, s, d, steps, metrics)

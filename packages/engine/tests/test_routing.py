import pytest

from liquidtwin_engine.document import parse_document
from liquidtwin_engine.graph import build_graph
from liquidtwin_engine.routing import route_job
from liquidtwin_engine.types import ExclusionReason as R
from liquidtwin_engine.types import RouteRequest


def req(**kw):
    base = dict(direction="IN", product_id="1", volume_m3=4000, rate_m3h=1000, window_from_min=0,
                source_ids=("1",), destination_ids=("7", "9"), max_routes=20)
    base.update(kw)
    return RouteRequest(**base)


def run(sample, request=None, **kw):
    return route_job(build_graph(parse_document(sample)), request or req(), **kw)


def reasons(res):
    return {(e.element_id or e.node_id, e.reason) for e in res.exclusions}


def test_best_route_is_first_and_ordered_by_total_time(sample):
    res = run(sample)
    assert res.routes and res.no_route is None
    totals = [r.metrics.total_min for r in res.routes]
    assert totals == sorted(totals)
    assert [r.rank for r in res.routes] == list(range(1, len(res.routes) + 1))


def test_not_certified_pipe_is_avoided_and_named(sample):
    res = run(sample, req(product_id="2", source_ids=("13",), destination_ids=("10",), volume_m3=500, rate_m3h=250))
    assert ("13", R.NOT_CERTIFIED) in reasons(res)
    assert res.routes == [] and res.no_route is not None
    assert any(b.element_id == "13" and b.reason == R.NOT_CERTIFIED for b in res.no_route.blockers)


def test_velocity_limit(sample):
    res = run(sample, req(rate_m3h=5000))
    assert any(r == R.VELOCITY for _, r in reasons(res))
    for route in res.routes:
        assert route.metrics.max_velocity_ms <= 3.0


def test_one_way_pump_reverse_is_excluded(sample):
    res = run(sample, req(source_ids=("4",), destination_ids=("1",)))
    assert ("3", R.ONE_WAY_PUMP) in reasons(res)
    assert all("3" not in r.element_ids or not r.steps[r.element_ids.index("3")].reversed for r in res.routes)


def test_zero_head_pump_is_still_one_way(sample):
    next(e for e in sample["elements"] if e["id"] == "3")["head_m"] = 0
    res = run(sample, req(source_ids=("4",), destination_ids=("1",)))
    assert ("3", R.ONE_WAY_PUMP) in reasons(res)
    assert all("3" not in r.element_ids or not r.steps[r.element_ids.index("3")].reversed for r in res.routes)


def test_dedication_to_other_group(sample):
    next(e for e in sample["elements"] if e["id"] == "8")["dedicated_group_id"] = "G2"
    res = run(sample, req(destination_ids=("7",)))
    assert res.routes == []
    assert ("8", R.DEDICATED_OTHER_GROUP) in reasons(res)


def test_pump_head_insufficient(sample):
    next(e for e in sample["elements"] if e["id"] == "3")["head_m"] = 1
    res = run(sample)
    assert res.routes == []
    assert res.no_route and any(b.reason == R.PUMP_HEAD for b in res.no_route.blockers)


@pytest.mark.parametrize("tank,field,value,reason", [
    ("7", "stock_m3", 7000, R.ENDPOINT_SPACE),
    ("7", "allow_inbound", False, R.ENDPOINT_DIRECTION),
    ("7", "product_id", "2", R.ENDPOINT_PRODUCT),
])
def test_destination_endpoint_exclusions(sample, tank, field, value, reason):
    next(n for n in sample["nodes"] if n["id"] == tank)[field] = value
    res = run(sample, req(destination_ids=("7",)))
    assert res.routes == []
    assert ("7", reason) in reasons(res)


def test_source_endpoint_stock_and_direction(sample):
    out = req(direction="OUT", product_id="1", volume_m3=3000, rate_m3h=300, source_ids=("7",), destination_ids=("10",))
    assert ("7", R.ENDPOINT_STOCK) in reasons(run(sample, out))
    next(n for n in sample["nodes"] if n["id"] == "7")["allow_outbound"] = False
    out2 = req(direction="OUT", product_id="1", volume_m3=600, rate_m3h=300, source_ids=("7",), destination_ids=("10",))
    assert ("7", R.ENDPOINT_DIRECTION) in reasons(run(sample, out2))


def test_source_equals_destination_gives_no_route(sample):
    res = run(sample, req(source_ids=("7",), destination_ids=("7",), volume_m3=100, rate_m3h=100))
    assert res.routes == []


def test_unknown_product_raises(sample):
    with pytest.raises(ValueError):
        run(sample, req(product_id="99"))


def test_max_routes_limits_output(sample):
    assert len(run(sample, req(max_routes=2)).routes) == 2


def test_parallel_elements_offered_as_alternatives(sample):
    dup = dict(next(e for e in sample["elements"] if e["id"] == "4"), id="4b", length_m=950)
    sample["elements"].append(dup)
    res = run(sample, req(max_routes=50))
    used = {e for r in res.routes for e in r.element_ids}
    assert {"4", "4b"} <= used


def test_deterministic(sample):
    a, b = run(sample), run(sample)
    assert [r.element_ids for r in a.routes] == [r.element_ids for r in b.routes]


def add_curve_to_first_pump(sample, max_flow=1000):
    sample["schema_version"] = "1.1"
    pump = next(element for element in sample["elements"] if element["id"] == "3")
    pump["performance_curve"] = {
        "model": "TABULAR",
        "min_flow_m3h": 100,
        "max_flow_m3h": max_flow,
        "points": [
            {"flow_m3h": 100, "head_m": 60},
            {"flow_m3h": max_flow, "head_m": 10},
        ],
        "speed_ratio_min": 0.5,
        "speed_ratio_max": 1.0,
    }
    pump["npsh_required_m"] = 2.0
    pump["npsh_margin_m"] = 0.5


def test_curve_pump_route_reports_operating_flow_and_suction_margin(sample):
    add_curve_to_first_pump(sample)
    request = req(rate_m3h=400, destination_ids=("7",), pump_suction_inputs=(("3", 4.0),))

    result = run(sample, request)

    assert result.routes
    metrics = result.routes[0].metrics
    assert 400 <= metrics.operating_flow_m3h <= 1000
    assert metrics.suction_margin_m == pytest.approx(1.5)
    assert metrics.pump_head_m == pytest.approx(metrics.system_head_m, abs=0.01)


def test_curve_pump_requires_operation_specific_suction_input(sample):
    add_curve_to_first_pump(sample)
    request = req(rate_m3h=400, destination_ids=("7",))

    result = run(sample, request)

    assert result.routes == []
    assert R.PUMP_SUCTION_MARGIN in {reason for _, reason in reasons(result)}


def test_curve_pump_rejects_requested_rate_above_curve_range(sample):
    add_curve_to_first_pump(sample, max_flow=300)
    request = req(rate_m3h=400, destination_ids=("7",), pump_suction_inputs=(("3", 4.0),))

    result = run(sample, request)

    assert result.routes == []
    assert R.PUMP_FLOW_OUT_OF_RANGE in {reason for _, reason in reasons(result)}


def test_curve_pump_rejects_route_without_system_intersection(sample):
    add_curve_to_first_pump(sample)
    next(element for element in sample["elements"] if element["id"] == "4")["elevation_delta_m"] = 1000
    request = req(rate_m3h=400, destination_ids=("7",), pump_suction_inputs=(("3", 4.0),))

    result = run(sample, request)

    assert result.routes == []
    assert R.NO_PUMP_SYSTEM_INTERSECTION in {reason for _, reason in reasons(result)}


def test_parallel_pump_train_combines_member_curves_for_route(sample):
    sample["schema_version"] = "1.1"
    sample["pump_trains"] = [
        {"id": "parallel-1", "arrangement": "PARALLEL", "member_pump_ids": ["3", "12"]}
    ]
    curve = {
        "model": "TABULAR",
        "min_flow_m3h": 100,
        "max_flow_m3h": 1000,
        "points": [
            {"flow_m3h": 100, "head_m": 60},
            {"flow_m3h": 1000, "head_m": 10},
        ],
        "speed_ratio_min": 0.5,
        "speed_ratio_max": 1.0,
    }
    for pump_id in ("3", "12"):
        pump = next(element for element in sample["elements"] if element["id"] == pump_id)
        pump.update(
            from_="3",
            to="12",
            diameter_mm=400,
            elevation_delta_m=50,
            performance_curve=curve,
            npsh_required_m=2.0,
            npsh_margin_m=0.5,
        )
        pump["from"] = pump.pop("from_")
    request = req(
        rate_m3h=400,
        source_ids=("3",),
        destination_ids=("12",),
        pump_suction_inputs=(("3", 4.0), ("12", 4.0)),
    )

    result = run(sample, request)

    assert result.routes
    assert result.routes[0].metrics.operating_flow_m3h >= 400
    assert 0.5 < result.routes[0].metrics.pump_speed_ratio < 1.0

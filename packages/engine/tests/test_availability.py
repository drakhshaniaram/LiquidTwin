import pytest

from liquidtwin_engine.document import parse_document
from liquidtwin_engine.graph import build_graph
from liquidtwin_engine.routing import route_job
from liquidtwin_engine.types import AvailabilityWindow, RouteRequest
from liquidtwin_engine.types import ExclusionReason as R

REQ = RouteRequest("IN", "1", 4000, 1000, 0, ("1",), ("7", "9"), max_routes=20)


@pytest.fixture
def graph(sample):
    return build_graph(parse_document(sample))


def test_each_best_route_element_down_changes_result_and_is_named(graph):
    best = route_job(graph, REQ).routes[0]
    for el in best.element_ids:
        res = route_job(graph, REQ, [AvailabilityWindow(el, "MAINTENANCE", 0, 1000)])
        if res.routes:
            assert el not in res.routes[0].element_ids
        else:
            assert res.no_route and any(b.element_id == el and b.reason == R.UNAVAILABLE for b in res.no_route.blockers)
        assert (el, R.UNAVAILABLE) in {(e.element_id, e.reason) for e in res.exclusions}


def test_window_ended_before_job_is_ignored(graph):
    best = route_job(graph, REQ).routes[0]
    w = [AvailabilityWindow(e, "MAINTENANCE", 0, 120) for e in best.element_ids]
    later = RouteRequest("IN", "1", 4000, 1000, 130, ("1",), ("7", "9"), max_routes=20)
    assert route_job(graph, later, w).routes[0].element_ids == best.element_ids


def test_open_ended_window_blocks(graph):
    best = route_job(graph, REQ).routes[0]
    w = [AvailabilityWindow(best.element_ids[0], "OUT_OF_SERVICE", 0, None)]
    later = RouteRequest("IN", "1", 4000, 1000, 5000, ("1",), ("7", "9"), max_routes=20)
    res = route_job(graph, later, w)
    assert not res.routes or best.element_ids[0] not in res.routes[0].element_ids


def test_available_status_window_has_no_effect(graph):
    best = route_job(graph, REQ).routes[0]
    w = [AvailabilityWindow(e, "AVAILABLE", 0, 1000) for e in best.element_ids]
    assert route_job(graph, REQ, w).routes[0].element_ids == best.element_ids


def test_unavailable_tank_endpoint(graph):
    res = route_job(graph, REQ, [AvailabilityWindow("7", "MAINTENANCE", 0, 1000, kind="NODE")])
    assert ("7", R.UNAVAILABLE) in {(e.node_id, e.reason) for e in res.exclusions}
    assert all(r.destination_id != "7" for r in res.routes)

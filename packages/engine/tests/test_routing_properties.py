import json

from conftest import SAMPLE
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from liquidtwin_engine.document import parse_document
from liquidtwin_engine.graph import build_graph
from liquidtwin_engine.routing import route_job
from liquidtwin_engine.types import AvailabilityWindow, RouteRequest

GRAPH = build_graph(parse_document(json.loads(SAMPLE.read_text(encoding="utf-8"))))
ELEMENTS = list(GRAPH.terminal.elements)


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(down=st.sets(st.sampled_from(ELEMENTS), max_size=6), rate=st.sampled_from([100, 500, 1000, 3000]),
       product=st.sampled_from(["1", "2"]))
def test_excluded_elements_never_appear_in_routes(down, rate, product):
    windows = [AvailabilityWindow(e, "MAINTENANCE", 0, 10_000) for e in down]
    req = RouteRequest("IN", product, 500, rate, 100, ("1", "2"), ("7", "8", "9"), max_routes=50)
    res = route_job(GRAPH, req, windows)
    excluded = {e.element_id for e in res.exclusions if e.element_id and e.reason.value != "ONE_WAY_PUMP"}
    for r in res.routes:
        assert not (set(r.element_ids) & down)
        assert not (set(r.element_ids) & excluded)
    again = route_job(GRAPH, req, windows)
    assert [r.element_ids for r in res.routes] == [r.element_ids for r in again.routes]

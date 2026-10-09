"""Independent schema 1.1 operating-point reference for a quadratic pump curve."""
import json
import math
from pathlib import Path

import pytest

from liquidtwin_engine.document import parse_document
from liquidtwin_engine.graph import build_graph
from liquidtwin_engine.routing import route_job
from liquidtwin_engine.types import RouteRequest

HERE = Path(__file__).parent


def test_quadratic_curve_route_matches_closed_form_intersection():
    document = json.loads((HERE / "pump-curve-terminal.json").read_text(encoding="utf-8"))
    graph = build_graph(parse_document(document))
    request = RouteRequest(
        direction="IN",
        product_id="P1",
        volume_m3=100,
        rate_m3h=400,
        window_from_min=0,
        source_ids=("source",),
        destination_ids=("destination",),
        pump_suction_inputs=(("pump-1", 4.0),),
    )

    first = route_job(graph, request).routes[0]
    second = route_job(graph, request).routes[0]
    expected_flow = math.sqrt((60 - 20) / 0.0001)

    assert first.metrics.operating_flow_m3h == pytest.approx(expected_flow, rel=0.01)
    assert first.metrics.pump_head_m == pytest.approx(20, abs=0.01)
    assert first.metrics.operating_flow_m3h == second.metrics.operating_flow_m3h
    assert first.metrics.transfer_min == second.metrics.transfer_min
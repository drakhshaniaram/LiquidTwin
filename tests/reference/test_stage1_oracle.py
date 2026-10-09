"""Reference oracle: Stage 1 candidate routes and metrics must match lineup_cpsat.py (constitution III)."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import lineup_cpsat as ref
from liquidtwin_engine.document import parse_document
from liquidtwin_engine.graph import build_graph
from liquidtwin_engine.routing import route_job
from liquidtwin_engine.types import RouteRequest


@pytest.fixture(scope="module")
def graph():
    data = json.loads((HERE / "sample-terminal.json").read_text(encoding="utf-8"))
    return build_graph(parse_document(data))


def _ours(graph, job):
    req = RouteRequest(direction="IN", product_id=str(job["prod"]), volume_m3=job["vol"], rate_m3h=job["rate"],
                       window_from_min=job["eta"], source_ids=tuple(str(n) for n in job["src"]),
                       destination_ids=tuple(str(n) for n in job["dst"]), max_routes=1000)
    res = route_job(graph, req)
    return {(int(r.source_id), int(r.destination_id), tuple(int(e) for e in r.element_ids),
             r.metrics.fill_min, r.metrics.flush_min, r.metrics.flush_volume_m3, r.metrics.valves,
             r.metrics.common_headers) for r in res.routes}


def _theirs(job):
    return {(r["src"], r["dst"], tuple(r["elems"]), r["fill"], r["ft"], r["fv"], r["valves"], r["common"])
            for r in ref.routes_for(job)}


@pytest.mark.parametrize("job", ref.JOBS, ids=lambda j: f"job{j['id']}")
def test_stage1_matches_reference(graph, job):
    ours, theirs = _ours(graph, job), _theirs(job)
    assert ours == theirs


def test_reference_candidate_counts(graph):
    assert [len(_theirs(j)) for j in ref.JOBS] == [6, 7, 3, 4]
    assert [len(_ours(graph, j)) for j in ref.JOBS] == [6, 7, 3, 4]

from liquidtwin_engine.document import parse_document
from liquidtwin_engine.graph import build_graph


def test_two_arcs_per_element_and_pump_reverse_flagged(sample):
    g = build_graph(parse_document(sample))
    assert len(g.arcs) == 30
    pump = [a for a in g.arcs if a.element_id == "3"]
    assert [a.reversed for a in pump] == [False, True]


def test_one_way_non_pump_has_single_arc(sample):
    next(e for e in sample["elements"] if e["id"] == "5")["bidirectional"] = False
    g = build_graph(parse_document(sample))
    assert len([a for a in g.arcs if a.element_id == "5"]) == 1


def test_parallel_elements_are_kept(sample):
    dup = dict(next(e for e in sample["elements"] if e["id"] == "5"), id="5b")
    sample["elements"].append(dup)
    g = build_graph(parse_document(sample))
    assert {a.element_id for a in g.out["3"] if a.v == "4"} == {"5", "5b"}


def test_element_order_is_stable_natural(sample):
    t = parse_document(sample)
    assert list(t.elements)[:3] == ["1", "2", "3"] and list(t.elements)[-1] == "15"

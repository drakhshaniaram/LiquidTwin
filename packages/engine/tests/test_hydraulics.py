import math

from liquidtwin_engine.document import parse_document
from liquidtwin_engine.hydraulics import HydraulicsConfig, arc_metrics, area_m2, transfer_minutes, velocity_ms


def test_area_and_velocity():
    cfg = HydraulicsConfig()
    assert math.isclose(area_m2(400), math.pi * 0.04, rel_tol=1e-12)
    v = velocity_ms(1000, 400, "ABOVEGROUND", cfg)
    assert math.isclose(v, 1000 / 3600 / (math.pi * 0.04), rel_tol=1e-12)


def test_underground_factor_changes_velocity():
    cfg = HydraulicsConfig()
    above = velocity_ms(1000, 400, "ABOVEGROUND", cfg)
    under = velocity_ms(1000, 400, "UNDERGROUND", cfg)
    assert math.isclose(under, above * 0.9)


def test_friction_lift_and_reverse_sign(sample):
    t = parse_document(sample)
    el = t.elements["13"]  # dz = +3, D250, L500
    p = t.products["1"]
    fwd = arc_metrics(t, el, False, p, 250, HydraulicsConfig())
    rev = arc_metrics(t, el, True, p, 250, HydraulicsConfig())
    assert fwd.need_dm > rev.need_dm            # uphill needs more head than downhill
    assert fwd.pump_dm == 0 and rev.pump_dm == 0


def test_pump_head_forward_only(sample):
    t = parse_document(sample)
    p = t.products["1"]
    assert arc_metrics(t, t.elements["3"], False, p, 1000, HydraulicsConfig()).pump_dm == 600
    assert arc_metrics(t, t.elements["3"], True, p, 1000, HydraulicsConfig()).pump_dm == 0


def test_flush_volume_and_time_for_residue_change(sample):
    t = parse_document(sample)
    m = arc_metrics(t, t.elements["1"], False, t.products["2"], 1000, HydraulicsConfig())  # residue 1, job product 2
    expected = 1.5 * math.pi * 0.04 * 400
    assert m.flush_volume == round(expected)
    assert m.flush_min == math.ceil(expected / 600 * 60)
    same = arc_metrics(t, t.elements["1"], False, t.products["1"], 1000, HydraulicsConfig())
    assert same.flush_volume == 0 and same.flush_min == 0


def test_valve_adds_operation_time(sample):
    t = parse_document(sample)
    m = arc_metrics(t, t.elements["15"], False, t.products["1"], 1000, HydraulicsConfig())
    assert m.fill_min == 3


def test_transfer_minutes():
    assert transfer_minutes(4000, 1000) == 240
    assert transfer_minutes(500, 250) == 120

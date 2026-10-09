from __future__ import annotations

from copy import deepcopy
import math

import pytest

from liquidtwin_engine.hydraulics import (
    find_operating_point,
    find_pump_train_operating_point,
    pump_curve_head,
    pump_train_head,
)
from liquidtwin_engine.validation import validate_document


def pump_document(sample, performance_curve):
    document = deepcopy(sample)
    document["schema_version"] = "1.1"
    pump = next(element for element in document["elements"] if element["type"] == "PUMP")
    pump["performance_curve"] = performance_curve
    pump["npsh_required_m"] = 2.0
    pump["npsh_margin_m"] = 0.5
    return document, pump


def codes(issues):
    return {issue.code for issue in issues if issue.severity == "ERROR"}


def tabular_curve():
    return {
        "model": "TABULAR",
        "min_flow_m3h": 100,
        "max_flow_m3h": 1000,
        "points": [
            {"flow_m3h": 100, "head_m": 60},
            {"flow_m3h": 500, "head_m": 52},
            {"flow_m3h": 1000, "head_m": 40},
        ],
        "speed_ratio_min": 0.5,
        "speed_ratio_max": 1.0,
    }


def test_valid_tabular_pump_curve_is_accepted(sample):
    document, _ = pump_document(sample, tabular_curve())

    assert codes(validate_document(document)) == set()


def test_tabular_curve_rejects_duplicate_or_unsorted_flow(sample):
    curve = tabular_curve()
    curve["points"][1]["flow_m3h"] = 100
    document, pump = pump_document(sample, curve)

    issues = validate_document(document)

    assert "INVALID_PUMP_CURVE" in codes(issues)
    assert any(issue.element_id == pump["id"] for issue in issues)


def test_tabular_curve_rejects_increasing_head_and_out_of_range_points(sample):
    curve = tabular_curve()
    curve["points"][1]["head_m"] = 65
    curve["points"][2]["flow_m3h"] = 1200
    document, pump = pump_document(sample, curve)

    issues = validate_document(document)

    assert "INVALID_PUMP_CURVE" in codes(issues)
    assert any(issue.element_id == pump["id"] for issue in issues)


def test_curve_rejects_speed_range_inverted(sample):
    curve = tabular_curve()
    curve["speed_ratio_min"] = 0.9
    curve["speed_ratio_max"] = 0.5
    document, pump = pump_document(sample, curve)

    issues = validate_document(document)

    assert "INVALID_PUMP_CURVE" in codes(issues)
    assert any(issue.element_id == pump["id"] for issue in issues)


def test_quadratic_curve_requires_all_coefficients(sample):
    curve = {
        "model": "QUADRATIC",
        "min_flow_m3h": 100,
        "max_flow_m3h": 1000,
        "shutoff_head_m": 60,
        "speed_ratio_min": 0.5,
        "speed_ratio_max": 1.0,
    }
    document, _ = pump_document(sample, curve)

    assert "INVALID_PUMP_CURVE" in codes(validate_document(document))


def test_pump_train_members_must_reference_distinct_pump_elements(sample):
    document, pump = pump_document(sample, tabular_curve())
    document["pump_trains"] = [
        {"id": "train-1", "arrangement": "SERIES", "member_pump_ids": [pump["id"], "missing-pump"]}
    ]

    issues = validate_document(document)

    assert "BAD_PUMP_TRAIN" in codes(issues)
    assert any("missing-pump" in issue.message for issue in issues)


def test_pump_train_requires_at_least_two_members(sample):
    document, pump = pump_document(sample, tabular_curve())
    document["pump_trains"] = [
        {"id": "train-1", "arrangement": "SERIES", "member_pump_ids": [pump["id"]]}
    ]

    assert "BAD_PUMP_TRAIN" in codes(validate_document(document))


@pytest.mark.parametrize(
    "flow,expected",
    [(100, 60), (300, 56), (500, 52), (1000, 40)],
)
def test_tabular_curve_interpolates_in_range(flow, expected):
    assert pump_curve_head(tabular_curve(), flow) == pytest.approx(expected, abs=1e-9)


def test_curve_evaluation_applies_affinity_speed_scaling():
    curve = tabular_curve()
    assert pump_curve_head(curve, 150, speed_ratio=0.5) == pytest.approx(14.0, abs=1e-9)


def test_curve_evaluation_never_extrapolates():
    assert pump_curve_head(tabular_curve(), 99) is None
    assert pump_curve_head(tabular_curve(), 1001) is None


def test_quadratic_curve_matches_closed_form():
    curve = {
        "model": "QUADRATIC",
        "min_flow_m3h": 100,
        "max_flow_m3h": 1000,
        "shutoff_head_m": 60,
        "quadratic_coefficient": 0.00001,
        "speed_ratio_min": 1.0,
        "speed_ratio_max": 1.0,
    }
    assert pump_curve_head(curve, 1000) == pytest.approx(50.0, abs=1e-9)


def test_operating_point_finds_highest_in_range_intersection():
    curve = {
        "model": "QUADRATIC",
        "min_flow_m3h": 100,
        "max_flow_m3h": 1000,
        "shutoff_head_m": 60,
        "quadratic_coefficient": 0.0001,
        "speed_ratio_min": 1.0,
        "speed_ratio_max": 1.0,
    }
    operating = find_operating_point(
        curve,
        lambda flow: 20 + 0.00002 * flow * flow,
        minimum_flow_m3h=100,
    )

    assert operating is not None
    assert operating.flow_m3h == pytest.approx(math.sqrt(40 / 0.00012), abs=0.01)
    assert operating.pump_head_m == pytest.approx(operating.system_head_m, abs=0.001)


def test_operating_point_selects_highest_of_multiple_intersections():
    curve = {
        "model": "QUADRATIC",
        "min_flow_m3h": 100,
        "max_flow_m3h": 1000,
        "shutoff_head_m": 100,
        "quadratic_coefficient": 0.00005,
        "speed_ratio_min": 1.0,
        "speed_ratio_max": 1.0,
    }

    operating = find_operating_point(
        curve,
        lambda flow: pump_curve_head(curve, flow) + 0.00005 * (flow - 200) * (flow - 800),
        minimum_flow_m3h=100,
    )

    assert operating is not None
    assert operating.flow_m3h == pytest.approx(800, abs=1)


def test_operating_point_rejects_missing_intersection_and_rate_below_request():
    curve = {
        "model": "QUADRATIC",
        "min_flow_m3h": 100,
        "max_flow_m3h": 1000,
        "shutoff_head_m": 60,
        "quadratic_coefficient": 0.0001,
        "speed_ratio_min": 1.0,
        "speed_ratio_max": 1.0,
    }
    assert find_operating_point(curve, lambda _flow: 100, minimum_flow_m3h=100) is None
    assert find_operating_point(curve, lambda flow: 20 + 0.00002 * flow * flow, minimum_flow_m3h=700) is None


def test_series_train_adds_member_heads_at_shared_flow():
    first = tabular_curve()
    second = tabular_curve()
    second["points"] = [
        {"flow_m3h": 100, "head_m": 50},
        {"flow_m3h": 500, "head_m": 42},
        {"flow_m3h": 1000, "head_m": 30},
    ]

    assert pump_train_head([first, second], "SERIES", 500) == pytest.approx(94.0)


def test_parallel_train_adds_unequal_member_flows_at_shared_head():
    first = tabular_curve()
    second = tabular_curve()
    second["points"] = [
        {"flow_m3h": 100, "head_m": 50},
        {"flow_m3h": 500, "head_m": 42},
        {"flow_m3h": 1000, "head_m": 30},
    ]

    assert pump_train_head([first, second], "PARALLEL", 1141.6666667) == pytest.approx(45.0, abs=0.01)


def test_train_operating_point_selects_lowest_allowed_feasible_speed():
    curve = {
        "model": "QUADRATIC",
        "min_flow_m3h": 100,
        "max_flow_m3h": 1000,
        "shutoff_head_m": 60,
        "quadratic_coefficient": 0.0001,
        "speed_ratio_min": 0.5,
        "speed_ratio_max": 1.0,
    }

    operating = find_pump_train_operating_point(
        [curve], "SERIES", lambda _flow: 30, minimum_flow_m3h=300
    )

    assert operating is not None
    point, speed_ratio = operating
    assert point.flow_m3h >= 300
    assert speed_ratio == pytest.approx(math.sqrt(0.65), abs=0.002)

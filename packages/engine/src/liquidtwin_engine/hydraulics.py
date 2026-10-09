"""Hydraulics for Stage 1 routing (mirrors arc_data() of the reference line-up script)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from collections.abc import Callable

from .document import Element, Product, Terminal

TWO_G = 19.62  # 2 * 9.81


@dataclass(frozen=True)
class HydraulicsConfig:
    flush_rate_m3h: float = 600.0
    # velocity multiplier by installation type (spec: underground vs aboveground changes velocity)
    installation_factor: dict[str, float] = field(default_factory=lambda: {"UNDERGROUND": 0.9, "ABOVEGROUND": 1.0})


@dataclass(frozen=True)
class ArcMetrics:
    velocity: float
    need_dm: int  # required head, decimetres (reference convention)
    pump_dm: int
    fill_min: int
    flush_volume: int
    flush_min: int


@dataclass(frozen=True)
class OperatingPoint:
    flow_m3h: float
    pump_head_m: float
    system_head_m: float
    speed_ratio: float = 1.0


def area_m2(diameter_mm: float) -> float:
    return math.pi * (diameter_mm / 1000) ** 2 / 4


def velocity_ms(rate_m3h: float, diameter_mm: float, installation: str, cfg: HydraulicsConfig) -> float:
    v = rate_m3h / 3600 / area_m2(diameter_mm)
    return v * cfg.installation_factor.get(installation, 1.0)


def arc_metrics(t: Terminal, el: Element, reverse: bool, product: Product, rate_m3h: float,
                cfg: HydraulicsConfig) -> ArcMetrics:
    L, D = el.length_m, el.diameter_mm
    v = velocity_ms(rate_m3h, D, el.installation, cfg)
    dz = -el.elevation_delta_m if reverse else el.elevation_delta_m
    need = 10 * (product.friction_factor * L / (D / 1000) * v * v / TWO_G + dz)
    fill = math.ceil(L / v / 60) + (int(el.operate_min) if el.type == "VALVE" else 0)
    res = el.residue_product_id
    fv = 0.0
    if res is not None and res != product.id:
        rule = t.changeover.get((res, product.id))
        fv = (rule.flush_factor if rule else 0.0) * area_m2(D) * L
    return ArcMetrics(velocity=v, need_dm=round(need), pump_dm=0 if reverse else round(10 * el.head_m),
                      fill_min=fill, flush_volume=round(fv), flush_min=math.ceil(fv / cfg.flush_rate_m3h * 60))


def transfer_minutes(volume_m3: float, rate_m3h: float) -> int:
    return math.ceil(volume_m3 * 60 / rate_m3h)


def pump_curve_head(curve: dict, flow_m3h: float, speed_ratio: float = 1.0) -> float | None:
    """Evaluate a pump curve at a physical flow; return None outside declared limits."""
    if flow_m3h < 0 or speed_ratio <= 0:
        return None
    if speed_ratio < curve["speed_ratio_min"] or speed_ratio > curve["speed_ratio_max"]:
        return None
    rated_flow = flow_m3h / speed_ratio
    if rated_flow < curve["min_flow_m3h"] or rated_flow > curve["max_flow_m3h"]:
        return None

    if curve["model"] == "QUADRATIC":
        head = curve["shutoff_head_m"] - curve["quadratic_coefficient"] * rated_flow**2
    elif curve["model"] == "TABULAR":
        points = curve["points"]
        head = None
        for point in points:
            if rated_flow == point["flow_m3h"]:
                head = point["head_m"]
                break
        if head is None:
            for left, right in zip(points, points[1:]):
                if left["flow_m3h"] <= rated_flow <= right["flow_m3h"]:
                    fraction = (rated_flow - left["flow_m3h"]) / (right["flow_m3h"] - left["flow_m3h"])
                    head = left["head_m"] + fraction * (right["head_m"] - left["head_m"])
                    break
        if head is None:
            return None
    else:
        return None

    scaled_head = head * speed_ratio**2
    return scaled_head if scaled_head >= 0 else None


def find_operating_point(
    curve: dict,
    system_head_m: Callable[[float], float],
    minimum_flow_m3h: float,
    speed_ratio: float = 1.0,
    samples: int = 128,
    tolerance_m: float = 1e-7,
) -> OperatingPoint | None:
    """Find the highest in-range pump/system intersection meeting the requested minimum flow."""
    if samples < 1 or minimum_flow_m3h < 0:
        return None
    low = max(curve["min_flow_m3h"] * speed_ratio, minimum_flow_m3h)
    high = curve["max_flow_m3h"] * speed_ratio
    if low > high or pump_curve_head(curve, low, speed_ratio) is None:
        return None

    def difference(flow: float) -> float | None:
        pump_head = pump_curve_head(curve, flow, speed_ratio)
        if pump_head is None:
            return None
        return pump_head - system_head_m(flow)

    roots: list[float] = []
    previous_flow = low
    previous_difference = difference(previous_flow)
    if previous_difference is None:
        return None
    if abs(previous_difference) <= tolerance_m:
        roots.append(previous_flow)

    for index in range(1, samples + 1):
        current_flow = low + (high - low) * index / samples
        current_difference = difference(current_flow)
        if current_difference is None:
            previous_flow, previous_difference = current_flow, current_difference
            continue
        if abs(current_difference) <= tolerance_m:
            roots.append(current_flow)
        if previous_difference is not None and previous_difference * current_difference < 0:
            left, right = previous_flow, current_flow
            left_difference = previous_difference
            for _ in range(64):
                middle = (left + right) / 2
                middle_difference = difference(middle)
                if middle_difference is None:
                    break
                if abs(middle_difference) <= tolerance_m:
                    left = right = middle
                    break
                if left_difference * middle_difference <= 0:
                    right = middle
                else:
                    left = middle
                    left_difference = middle_difference
            roots.append((left + right) / 2)
        previous_flow, previous_difference = current_flow, current_difference

    feasible_roots = [flow for flow in roots if flow >= minimum_flow_m3h]
    if not feasible_roots:
        return None
    flow = max(feasible_roots)
    pump_head = pump_curve_head(curve, flow, speed_ratio)
    if pump_head is None:
        return None
    return OperatingPoint(flow, pump_head, system_head_m(flow))


def find_operating_point_from_functions(
    pump_head_m: Callable[[float], float | None],
    system_head_m: Callable[[float], float],
    minimum_flow_m3h: float,
    maximum_flow_m3h: float,
    samples: int = 128,
    tolerance_m: float = 1e-7,
) -> OperatingPoint | None:
    """Find the highest intersection for a composed series/train pump curve."""
    if samples < 1 or minimum_flow_m3h < 0 or maximum_flow_m3h < minimum_flow_m3h:
        return None

    def difference(flow: float) -> float | None:
        pump_head = pump_head_m(flow)
        return None if pump_head is None else pump_head - system_head_m(flow)

    roots: list[float] = []
    previous_flow = minimum_flow_m3h
    previous_difference = difference(previous_flow)
    if previous_difference is None:
        return None
    if abs(previous_difference) <= tolerance_m:
        roots.append(previous_flow)

    for index in range(1, samples + 1):
        current_flow = minimum_flow_m3h + (maximum_flow_m3h - minimum_flow_m3h) * index / samples
        current_difference = difference(current_flow)
        if current_difference is None:
            previous_flow, previous_difference = current_flow, current_difference
            continue
        if abs(current_difference) <= tolerance_m:
            roots.append(current_flow)
        if previous_difference is not None and previous_difference * current_difference < 0:
            left, right = previous_flow, current_flow
            left_difference = previous_difference
            for _ in range(64):
                middle = (left + right) / 2
                middle_difference = difference(middle)
                if middle_difference is None:
                    break
                if abs(middle_difference) <= tolerance_m:
                    left = right = middle
                    break
                if left_difference * middle_difference <= 0:
                    right = middle
                else:
                    left = middle
                    left_difference = middle_difference
            roots.append((left + right) / 2)
        previous_flow, previous_difference = current_flow, current_difference

    if not roots:
        return None
    flow = max(roots)
    pump_head = pump_head_m(flow)
    if pump_head is None:
        return None
    return OperatingPoint(flow, pump_head, system_head_m(flow))


def _curve_flow_at_head(curve: dict, head_m: float, speed_ratio: float) -> float | None:
    minimum_flow = curve["min_flow_m3h"] * speed_ratio
    maximum_flow = curve["max_flow_m3h"] * speed_ratio
    head_at_minimum = pump_curve_head(curve, minimum_flow, speed_ratio)
    head_at_maximum = pump_curve_head(curve, maximum_flow, speed_ratio)
    if head_at_minimum is None or head_at_maximum is None:
        return None
    if head_m > head_at_minimum or head_m < head_at_maximum:
        return None
    if math.isclose(head_m, head_at_minimum, abs_tol=1e-10):
        return minimum_flow
    if math.isclose(head_m, head_at_maximum, abs_tol=1e-10):
        return maximum_flow

    rated_head = head_m / speed_ratio**2
    if curve["model"] == "QUADRATIC":
        coefficient = curve["quadratic_coefficient"]
        if coefficient == 0:
            return minimum_flow if math.isclose(rated_head, curve["shutoff_head_m"]) else None
        rated_flow = math.sqrt((curve["shutoff_head_m"] - rated_head) / coefficient)
        return rated_flow * speed_ratio if curve["min_flow_m3h"] <= rated_flow <= curve["max_flow_m3h"] else None

    points = curve["points"]
    for left, right in zip(points, points[1:]):
        if left["head_m"] >= rated_head >= right["head_m"]:
            head_span = left["head_m"] - right["head_m"]
            if head_span == 0:
                return left["flow_m3h"] * speed_ratio
            fraction = (left["head_m"] - rated_head) / head_span
            return (left["flow_m3h"] + fraction * (right["flow_m3h"] - left["flow_m3h"])) * speed_ratio
    return None


def pump_train_head(
    curves: list[dict], arrangement: str, flow_m3h: float, speed_ratio: float = 1.0
) -> float | None:
    """Evaluate a series or parallel train inside every member's declared curve range."""
    if not curves or flow_m3h < 0:
        return None
    if arrangement == "SERIES":
        heads = [pump_curve_head(curve, flow_m3h, speed_ratio) for curve in curves]
        if any(head is None for head in heads):
            return None
        return sum(head for head in heads if head is not None)
    if arrangement != "PARALLEL":
        return None

    member_min_heads = [
        pump_curve_head(curve, curve["min_flow_m3h"] * speed_ratio, speed_ratio)
        for curve in curves
    ]
    member_max_heads = [
        pump_curve_head(curve, curve["max_flow_m3h"] * speed_ratio, speed_ratio)
        for curve in curves
    ]
    if any(head is None for head in (*member_min_heads, *member_max_heads)):
        return None
    valid_min_heads = [head for head in member_min_heads if head is not None]
    valid_max_heads = [head for head in member_max_heads if head is not None]
    low_head = max(valid_max_heads)
    high_head = min(valid_min_heads)
    if low_head > high_head:
        return None

    minimum_train_flow = sum(curve["min_flow_m3h"] * speed_ratio for curve in curves)
    maximum_train_flow = sum(curve["max_flow_m3h"] * speed_ratio for curve in curves)
    if flow_m3h < minimum_train_flow or flow_m3h > maximum_train_flow:
        return None

    for _ in range(48):
        middle_head = (low_head + high_head) / 2
        member_flows = [
            _curve_flow_at_head(curve, middle_head, speed_ratio) for curve in curves
        ]
        if any(flow is None for flow in member_flows):
            return None
        total_flow = sum(flow for flow in member_flows if flow is not None)
        if total_flow > flow_m3h:
            low_head = middle_head
        else:
            high_head = middle_head
    return (low_head + high_head) / 2


def find_pump_train_operating_point(
    curves: list[dict],
    arrangement: str,
    system_head_m: Callable[[float], float],
    minimum_flow_m3h: float,
    samples: int = 128,
) -> tuple[OperatingPoint, float] | None:
    """Find the minimum common allowed speed ratio that meets route demand."""
    if not curves or arrangement not in {"SERIES", "PARALLEL"}:
        return None
    minimum_speed = max(curve["speed_ratio_min"] for curve in curves)
    maximum_speed = min(curve["speed_ratio_max"] for curve in curves)
    if minimum_speed > maximum_speed:
        return None

    def at_speed(speed_ratio: float) -> OperatingPoint | None:
        if arrangement == "SERIES":
            minimum_curve_flow = max(curve["min_flow_m3h"] * speed_ratio for curve in curves)
            maximum_curve_flow = min(curve["max_flow_m3h"] * speed_ratio for curve in curves)
        else:
            minimum_curve_flow = sum(curve["min_flow_m3h"] * speed_ratio for curve in curves)
            maximum_curve_flow = sum(curve["max_flow_m3h"] * speed_ratio for curve in curves)
        lower = max(minimum_flow_m3h, minimum_curve_flow)
        return find_operating_point_from_functions(
            lambda flow: pump_train_head(curves, arrangement, flow, speed_ratio),
            system_head_m,
            lower,
            maximum_curve_flow,
            samples=min(samples, 32),
        )

    point = at_speed(minimum_speed)
    if point is not None:
        return point, minimum_speed
    point = at_speed(maximum_speed)
    if point is None:
        return None

    low, high = minimum_speed, maximum_speed
    for _ in range(24):
        middle = (low + high) / 2
        candidate = at_speed(middle)
        if candidate is None:
            low = middle
        else:
            high = middle
            point = candidate
    return point, high

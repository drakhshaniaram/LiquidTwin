"""Hydraulics for Stage 1 routing (mirrors arc_data() of the reference line-up script)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

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

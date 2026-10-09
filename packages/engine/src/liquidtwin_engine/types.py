"""Shared engine types (match specs/001-terminal-designer-routing/data-model.md and openapi.yaml)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ExclusionReason(str, Enum):
    NOT_CERTIFIED = "NOT_CERTIFIED"
    VELOCITY = "VELOCITY"
    RESIDUE = "RESIDUE"
    ONE_WAY_PUMP = "ONE_WAY_PUMP"
    UNAVAILABLE = "UNAVAILABLE"
    DEDICATED_OTHER_GROUP = "DEDICATED_OTHER_GROUP"
    PUMP_HEAD = "PUMP_HEAD"
    ENDPOINT_STOCK = "ENDPOINT_STOCK"
    ENDPOINT_SPACE = "ENDPOINT_SPACE"
    ENDPOINT_PRODUCT = "ENDPOINT_PRODUCT"
    ENDPOINT_DIRECTION = "ENDPOINT_DIRECTION"
    INVALID_PUMP_CURVE = "INVALID_PUMP_CURVE"
    PUMP_FLOW_OUT_OF_RANGE = "PUMP_FLOW_OUT_OF_RANGE"
    NO_PUMP_SYSTEM_INTERSECTION = "NO_PUMP_SYSTEM_INTERSECTION"
    PUMP_SPEED_OUT_OF_RANGE = "PUMP_SPEED_OUT_OF_RANGE"
    PUMP_SUCTION_MARGIN = "PUMP_SUCTION_MARGIN"


@dataclass(frozen=True)
class Exclusion:
    reason: ExclusionReason
    detail: str
    element_id: str | None = None
    node_id: str | None = None


@dataclass(frozen=True)
class ValidationIssue:
    severity: str  # ERROR | WARNING
    code: str
    message: str
    fix_hint: str = ""
    element_id: str | None = None
    node_id: str | None = None
    row: int | None = None
    file: str | None = None


@dataclass(frozen=True)
class RouteStep:
    element_id: str
    from_node: str
    to_node: str
    reversed: bool


@dataclass(frozen=True)
class RouteMetrics:
    fill_min: float
    transfer_min: float
    flush_min: float
    flush_volume_m3: float
    total_min: float
    valves: int
    common_headers: int
    head_margin_m: float
    max_velocity_ms: float
    operating_flow_m3h: float | None = None
    pump_head_m: float | None = None
    system_head_m: float | None = None
    suction_margin_m: float | None = None
    pump_speed_ratio: float | None = None


@dataclass(frozen=True)
class Route:
    rank: int
    source_id: str
    destination_id: str
    steps: tuple[RouteStep, ...]
    metrics: RouteMetrics

    @property
    def element_ids(self) -> list[str]:
        return [s.element_id for s in self.steps]


@dataclass(frozen=True)
class RouteRequest:
    direction: str  # IN | OUT | TRANSFER
    product_id: str
    volume_m3: float
    rate_m3h: float
    window_from_min: float
    source_ids: tuple[str, ...]
    destination_ids: tuple[str, ...]
    window_to_min: float | None = None
    max_routes: int = 5
    pump_suction_inputs: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class AvailabilityWindow:
    element_id: str  # element or node id
    status: str  # AVAILABLE | MAINTENANCE | FLUSHING | CLEANING | OUT_OF_SERVICE
    start_min: float
    end_min: float | None = None
    reason: str = ""
    kind: str = "ELEMENT"  # ELEMENT | NODE (element and node ids may coincide)


@dataclass
class NoRoute:
    message: str
    blockers: list[Exclusion] = field(default_factory=list)


@dataclass
class RouteResult:
    routes: list[Route]
    exclusions: list[Exclusion]
    no_route: NoRoute | None = None

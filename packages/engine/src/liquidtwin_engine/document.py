"""Parse and normalize a TerminalDocument into plain dataclasses (stable id order, schema defaults applied)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .schema_models import TerminalDocument

_NAT = re.compile(r"(\d+)")


def natural_key(s: str) -> list[Any]:
    return [int(p) if p.isdigit() else p for p in _NAT.split(s)]


@dataclass
class Product:
    id: str
    name: str
    friction_factor: float = 0.018
    max_velocity: float = 3.0
    group: str | None = None
    color: str | None = None


@dataclass
class ChangeoverRule:
    from_product: str
    to_product: str
    gap_min: float = 0.0
    flush_factor: float = 0.0
    manual_clean_required: bool = False


@dataclass
class Node:
    id: str
    type: str
    name: str | None = None
    x: float | None = None
    y: float | None = None
    group_id: str | None = None
    product_id: str | None = None
    stock_m3: float = 0.0
    capacity_m3: float = 0.0
    min_heel_m3: float = 0.0
    allow_inbound: bool = True
    allow_outbound: bool = True
    allow_simultaneous: bool = False
    max_rate_m3h: float | None = None
    certified_products: tuple[str, ...] = ()
    platform_id: str | None = None


@dataclass
class Element:
    id: str
    type: str
    from_node: str
    to_node: str
    length_m: float = 0.0
    diameter_mm: float = 0.0
    elevation_delta_m: float = 0.0
    installation: str = "ABOVEGROUND"
    certified_products: frozenset[str] = frozenset()
    dedicated_group_id: str | None = None
    dedicated_product_ids: frozenset[str] = frozenset()
    residue_product_id: str | None = None
    bidirectional: bool = True
    tank_id: str | None = None
    head_m: float = 0.0
    operate_min: float = 0.0
    state: str | None = None


@dataclass
class Terminal:
    name: str
    products: dict[str, Product] = field(default_factory=dict)
    changeover: dict[tuple[str, str], ChangeoverRule] = field(default_factory=dict)
    nodes: dict[str, Node] = field(default_factory=dict)
    elements: dict[str, Element] = field(default_factory=dict)
    tank_groups: dict[str, list[str]] = field(default_factory=dict)


def _s(v: Any) -> str | None:
    return None if v is None else str(v)


def parse_document(data: dict[str, Any]) -> Terminal:
    """Validate against the schema models, then build the normalized Terminal."""
    doc = TerminalDocument.model_validate(data)
    d = doc.model_dump(mode="json", by_alias=True)
    t = Terminal(name=d["name"])
    for p in sorted(d["products"], key=lambda p: natural_key(p["id"])):
        t.products[p["id"]] = Product(
            id=p["id"], name=p["name"], group=p.get("group"), color=p.get("color"),
            friction_factor=0.018 if p.get("friction_factor") is None else p["friction_factor"],
            max_velocity=3.0 if p.get("max_velocity") is None else p["max_velocity"])
    for c in d.get("changeover") or []:
        t.changeover[(c["from_product"], c["to_product"])] = ChangeoverRule(
            c["from_product"], c["to_product"], c.get("gap_min") or 0.0, c.get("flush_factor") or 0.0,
            bool(c.get("manual_clean_required")))
    for n in sorted(d["nodes"], key=lambda n: natural_key(n["id"])):
        t.nodes[n["id"]] = Node(
            id=n["id"], type=n["type"], name=n.get("name"), x=n.get("x"), y=n.get("y"),
            group_id=_s(n.get("group_id")), product_id=_s(n.get("product_id")),
            stock_m3=n.get("stock_m3") or 0.0, capacity_m3=n.get("capacity_m3") or 0.0,
            min_heel_m3=n.get("min_heel_m3") or 0.0,
            allow_inbound=True if n.get("allow_inbound") is None else n["allow_inbound"],
            allow_outbound=True if n.get("allow_outbound") is None else n["allow_outbound"],
            allow_simultaneous=bool(n.get("allow_simultaneous")), max_rate_m3h=n.get("max_rate_m3h"),
            certified_products=tuple(n.get("certified_products") or ()), platform_id=_s(n.get("platform_id")))
    for e in sorted(d["elements"], key=lambda e: natural_key(e["id"])):
        t.elements[e["id"]] = Element(
            id=e["id"], type=e["type"], from_node=e["from"], to_node=e["to"],
            length_m=e.get("length_m") or 0.0, diameter_mm=e.get("diameter_mm") or 0.0,
            elevation_delta_m=e.get("elevation_delta_m") or 0.0, installation=e.get("installation") or "ABOVEGROUND",
            certified_products=frozenset(e.get("certified_products") or ()),
            dedicated_group_id=_s(e.get("dedicated_group_id")),
            dedicated_product_ids=frozenset(e.get("dedicated_product_ids") or ()),
            residue_product_id=_s(e.get("residue_product_id")),
            bidirectional=True if e.get("bidirectional") is None else e["bidirectional"],
            tank_id=_s(e.get("tank_id")), head_m=e.get("head_m") or 0.0,
            operate_min=e.get("operate_min") or 0.0, state=e.get("state"))
    for g in d.get("tank_groups") or []:
        t.tank_groups[g["id"]] = list(g.get("tank_ids") or [])
    return t

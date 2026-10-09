"""Terminal validation: schema errors first, then semantic rules from data-model.md."""
from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import ValidationError

from .schema_models import TerminalDocument
from .types import ValidationIssue


def _issue(sev: str, code: str, msg: str, hint: str = "", **kw: Any) -> ValidationIssue:
    return ValidationIssue(sev, code, msg, hint, **kw)


def validate_document(data: dict[str, Any]) -> list[ValidationIssue]:
    try:
        TerminalDocument.model_validate(data)
    except ValidationError as e:
        return [_issue("ERROR", "SCHEMA", f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}",
                       "Fix the value to match the terminal schema") for err in e.errors()]
    issues: list[ValidationIssue] = []
    products = {p["id"] for p in data["products"]}
    nodes = {n["id"]: n for n in data["nodes"]}
    groups = {g["id"] for g in data.get("tank_groups") or []}

    for kind, items in (("product", data["products"]), ("node", data["nodes"]), ("element", data["elements"])):
        for i, c in Counter(x["id"] for x in items).items():
            if c > 1:
                issues.append(_issue("ERROR", "DUPLICATE_ID", f"Duplicate {kind} id {i}", "Make ids unique"))
    for n in data["nodes"]:
        nid = n["id"]
        if n["type"] == "TANK":
            cap, stock = n.get("capacity_m3"), n.get("stock_m3") or 0
            if cap is not None and stock > cap:
                issues.append(_issue("ERROR", "STOCK_OVER_CAPACITY", f"Tank {nid} stock {stock} exceeds capacity {cap}",
                                     "Lower the stock or raise the capacity", node_id=nid))
            if n.get("product_id") and n["product_id"] not in products:
                issues.append(_issue("ERROR", "UNKNOWN_PRODUCT", f"Tank {nid} references unknown product {n['product_id']}",
                                     "Add the product or pick an existing one", node_id=nid))
            if n.get("group_id") and n["group_id"] not in groups and groups:
                issues.append(_issue("WARNING", "UNKNOWN_GROUP", f"Tank {nid} references unknown group {n['group_id']}",
                                     "Create the tank group", node_id=nid))
        if n["type"] == "RAIL_CAR":
            p = n.get("platform_id")
            if p is None or nodes.get(p, {}).get("type") != "RAIL_PLATFORM":
                issues.append(_issue("ERROR", "BAD_PLATFORM", f"Rail car {nid} must reference a RAIL_PLATFORM node",
                                     "Set platform_id to a rail platform", node_id=nid))
        for pid in n.get("certified_products") or []:
            if pid not in products:
                issues.append(_issue("ERROR", "UNKNOWN_PRODUCT", f"{nid} certifies unknown product {pid}", "", node_id=nid))
    for c in data.get("changeover") or []:
        for pid in (c["from_product"], c["to_product"]):
            if pid not in products:
                issues.append(_issue("ERROR", "UNKNOWN_PRODUCT", f"Changeover references unknown product {pid}", ""))

    touched: set[str] = set()
    header_tanks: Counter[str] = Counter()
    for e in data["elements"]:
        eid = e["id"]
        for end in ("from", "to"):
            if e[end] not in nodes:
                issues.append(_issue("ERROR", "DANGLING_ELEMENT", f"Element {eid} {end} references unknown node {e[end]}",
                                     "Connect the pipe to existing equipment", element_id=eid))
        if e["from"] == e["to"]:
            issues.append(_issue("ERROR", "SELF_LOOP", f"Element {eid} connects a node to itself", "", element_id=eid))
        touched.update((e["from"], e["to"]))
        for pid in e.get("certified_products") or []:
            if pid not in products:
                issues.append(_issue("ERROR", "UNKNOWN_PRODUCT", f"Element {eid} certifies unknown product {pid}", "",
                                     element_id=eid))
        res = e.get("residue_product_id")
        if res and res not in products:
            issues.append(_issue("ERROR", "UNKNOWN_PRODUCT", f"Element {eid} residue references unknown product {res}", "",
                                 element_id=eid))
        if e["type"] in ("TANK_HEADER", "SEGMENT"):
            tid = e.get("tank_id")
            if tid not in nodes or nodes[tid]["type"] != "TANK":
                issues.append(_issue("ERROR", "BAD_TANK_REF", f"Element {eid} must reference an existing tank in tank_id",
                                     "Set tank_id to a tank node", element_id=eid))
            elif e["type"] == "TANK_HEADER":
                header_tanks[tid] += 1
    for n in data["nodes"]:
        if n["id"] not in touched and n["type"] != "RAIL_CAR":
            issues.append(_issue("WARNING", "ISOLATED_NODE", f"Node {n['id']} has no connected pipes",
                                 "Connect it or remove it", node_id=n["id"]))
    for tid, c in header_tanks.items():
        if c > 1:
            issues.append(_issue("WARNING", "MULTI_HEADER", f"Tank {tid} is served by {c} tank headers",
                                 "A tank header should serve one tank; use a common header for shared lines", node_id=tid))
    return issues

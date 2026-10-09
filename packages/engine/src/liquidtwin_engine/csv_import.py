"""CSV bundle import (see specs/001-terminal-designer-routing/contracts/csv-import.md). All-or-nothing."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any

from .types import ValidationIssue
from .validation import validate_document

NUM, INT, BOOL, STR, LIST, NUM_LIST = "num", "int", "bool", "str", "list", "numlist"

PRODUCTS = {"id": STR, "name": STR, "group": STR, "friction_factor": NUM, "max_velocity": NUM, "color": STR}
CHANGEOVER = {"from_product": STR, "to_product": STR, "gap_min": NUM, "flush_factor": NUM,
              "manual_clean_required": BOOL}
GROUPS = {"id": STR, "name": STR}
NODES = {"id": STR, "type": STR, "name": STR, "x": NUM, "y": NUM, "max_rate_m3h": NUM, "certified_products": LIST,
         "side_count": INT, "cars_per_side": INT, "platform_id": STR, "product_id": STR, "stock_m3": NUM,
         "capacity_m3": NUM}
TANKS = {"node_id": STR, "group_id": STR, "product_id": STR, "stock_m3": NUM, "capacity_m3": NUM, "min_heel_m3": NUM,
         "allow_inbound": BOOL, "allow_outbound": BOOL, "allow_simultaneous": BOOL}
ELEMENTS = {"id": STR, "type": STR, "from": STR, "to": STR, "length_m": NUM, "diameter_mm": NUM,
            "elevation_delta_m": NUM, "installation": STR, "roughness_mm": NUM, "certified_products": LIST,
            "dedicated_group_id": STR, "dedicated_product_ids": LIST, "residue_product_id": STR, "bidirectional": BOOL,
            "tank_id": STR, "head_m": NUM, "max_flow_m3h": NUM, "operate_min": NUM, "state": STR,
            "curve_model": STR, "curve_min_flow_m3h": NUM, "curve_max_flow_m3h": NUM,
            "curve_shutoff_head_m": NUM, "curve_quadratic_coefficient": NUM, "curve_flow_points": NUM_LIST,
            "curve_head_points": NUM_LIST, "speed_ratio_min": NUM, "speed_ratio_max": NUM,
            "npsh_required_m": NUM, "npsh_margin_m": NUM}
PUMP_TRAINS = {"id": STR, "arrangement": STR, "member_pump_ids": LIST}
TERMINAL_META = {"schema_version": STR}
AVAIL = {"element_id": STR, "status": STR, "from": STR, "to": STR, "reason": STR, "source": STR, "external_ref": STR}
REQUIRED = {"products.csv": ("id", "name"), "nodes.csv": ("id", "type"), "elements.csv": ("id", "type", "from", "to")}


@dataclass
class CsvImportResult:
    document: dict[str, Any] | None
    availability: list[dict[str, Any]] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)


def _err(issues: list[ValidationIssue], file: str, row: int | None, code: str, msg: str) -> None:
    issues.append(ValidationIssue("ERROR", code, msg, "", row=row, file=file))


def _convert(raw: str, kind: str) -> Any:
    raw = raw.strip()
    if raw == "":
        return None
    if kind == NUM:
        return float(raw)
    if kind == INT:
        return int(raw)
    if kind == BOOL:
        if raw.lower() not in ("true", "false"):
            raise ValueError("expected true or false")
        return raw.lower() == "true"
    if kind == LIST:
        return [p for p in (x.strip() for x in raw.split(";")) if p]
    if kind == NUM_LIST:
        return [float(value.strip()) for value in raw.split(";") if value.strip()]
    return raw


def _read(files: dict[str, str], name: str, spec: dict[str, str], issues: list[ValidationIssue],
          required: bool) -> list[tuple[int, dict[str, Any]]]:
    if name not in files:
        if required:
            _err(issues, name, None, "MISSING_FILE", f"Required file {name} is missing")
        return []
    reader = csv.DictReader(io.StringIO(files[name].lstrip("\ufeff")))
    header = reader.fieldnames or []
    for col in header:
        if col not in spec and not col.startswith("x_"):
            _err(issues, name, 1, "UNKNOWN_COLUMN", f"Unknown column '{col}' (prefix with x_ to ignore)")
    for col in REQUIRED.get(name, ()):
        if col not in header:
            _err(issues, name, 1, "MISSING_COLUMN", f"Required column '{col}' is missing")
    rows: list[tuple[int, dict[str, Any]]] = []
    for i, rec in enumerate(reader, start=2):
        out: dict[str, Any] = {}
        for col, raw in rec.items():
            if col in spec and raw is not None:
                try:
                    v = _convert(raw, spec[col])
                except ValueError as ex:
                    _err(issues, name, i, "BAD_VALUE", f"Column '{col}': {ex} (got '{raw}')")
                    continue
                if v is not None:
                    out[col] = v
        for col in REQUIRED.get(name, ()):
            if col in header and col not in out:
                _err(issues, name, i, "MISSING_VALUE", f"Column '{col}' is empty")
        rows.append((i, out))
    return rows


def import_csv_bundle(files: dict[str, str], name: str) -> CsvImportResult:
    issues: list[ValidationIssue] = []
    terminal_rows = _read(files, "terminal.csv", TERMINAL_META, issues, False)
    products = [r for _, r in _read(files, "products.csv", PRODUCTS, issues, True)]
    changeover = [r for _, r in _read(files, "changeover.csv", CHANGEOVER, issues, False)]
    groups = [r for _, r in _read(files, "groups.csv", GROUPS, issues, False)]
    node_rows = _read(files, "nodes.csv", NODES, issues, True)
    tank_rows = _read(files, "tanks.csv", TANKS, issues, False)
    element_rows = _read(files, "elements.csv", ELEMENTS, issues, True)
    pump_trains = [r for _, r in _read(files, "pump_trains.csv", PUMP_TRAINS, issues, False)]
    avail = [r for _, r in _read(files, "availability.csv", AVAIL, issues, False)]
    if len(terminal_rows) > 1:
        _err(issues, "terminal.csv", 3, "TOO_MANY_ROWS", "terminal.csv must contain exactly one data row")

    nodes = {r["id"]: dict(r) for _, r in node_rows if "id" in r}
    group_members: dict[str, list[str]] = {}
    for i, t in tank_rows:
        nid = t.get("node_id")
        if nid not in nodes or nodes[nid].get("type") != "TANK":
            _err(issues, "tanks.csv", i, "BAD_TANK_REF", f"node_id '{nid}' is not a TANK node in nodes.csv")
            continue
        nodes[nid].update({k: v for k, v in t.items() if k != "node_id"})
        if t.get("group_id"):
            group_members.setdefault(t["group_id"], []).append(nid)
    group_docs = []
    named = {g["id"]: g.get("name", g["id"]) for g in groups if "id" in g}
    for gid in sorted(set(named) | set(group_members)):
        group_docs.append({"id": gid, "name": named.get(gid, gid), "tank_ids": group_members.get(gid, [])})

    if any(i.severity == "ERROR" for i in issues):
        return CsvImportResult(None, avail, issues)
    doc: dict[str, Any] = {
        "schema_version": (terminal_rows[0][1].get("schema_version") if terminal_rows else None) or "1.0",
        "name": name, "products": products, "changeover": changeover,
        "tank_groups": group_docs, "nodes": list(nodes.values()), "elements": [r for _, r in element_rows]}
    if pump_trains:
        doc["pump_trains"] = pump_trains
    for element in doc["elements"]:
        model = element.pop("curve_model", None)
        if model:
            element["performance_curve"] = {
                "model": model,
                "min_flow_m3h": element.pop("curve_min_flow_m3h", None),
                "max_flow_m3h": element.pop("curve_max_flow_m3h", None),
                "speed_ratio_min": element.pop("speed_ratio_min", None),
                "speed_ratio_max": element.pop("speed_ratio_max", None),
            }
            curve = element["performance_curve"]
            if model == "QUADRATIC":
                curve["shutoff_head_m"] = element.pop("curve_shutoff_head_m", None)
                curve["quadratic_coefficient"] = element.pop("curve_quadratic_coefficient", None)
            else:
                flows = element.pop("curve_flow_points", [])
                heads = element.pop("curve_head_points", [])
                if len(flows) != len(heads):
                    _err(issues, "elements.csv", None, "BAD_PUMP_CURVE", f"Curve flow/head point counts differ for {element['id']}")
                curve["points"] = [
                    {"flow_m3h": flow, "head_m": head}
                    for flow, head in zip(flows, heads)
                ]
        else:
            for column in (
                "curve_min_flow_m3h", "curve_max_flow_m3h", "curve_shutoff_head_m",
                "curve_quadratic_coefficient", "curve_flow_points", "curve_head_points",
                "speed_ratio_min", "speed_ratio_max",
            ):
                element.pop(column, None)
    if any(i.severity == "ERROR" for i in issues):
        return CsvImportResult(None, avail, issues)
    sem = validate_document(doc)
    issues.extend(sem)
    if any(i.severity == "ERROR" for i in issues):
        return CsvImportResult(None, avail, issues)
    return CsvImportResult(doc, avail, issues)

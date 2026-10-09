"""Export a terminal document to JSON text or a CSV bundle (round-trips with csv_import)."""
from __future__ import annotations

import csv
import io
import json
from typing import Any


def to_json(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=False) + "\n"


def _b(v: Any) -> str:
    return "" if v is None else ("true" if v else "false")


def _l(v: Any) -> str:
    return ";".join(v) if v else ""


def _v(v: Any) -> str:
    return "" if v is None else str(v)


def to_csv_bundle(doc: dict[str, Any]) -> dict[str, str]:
    def write(header: list[str], rows: list[list[str]]) -> str:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
        return buf.getvalue()

    files: dict[str, str] = {}
    files["terminal.csv"] = write(["schema_version"], [[doc.get("schema_version", "1.0")]])
    files["products.csv"] = write(
        ["id", "name", "group", "friction_factor", "max_velocity", "color"],
        [[p["id"], p["name"], _v(p.get("group")), _v(p.get("friction_factor")), _v(p.get("max_velocity")),
          _v(p.get("color"))] for p in doc["products"]])
    files["changeover.csv"] = write(
        ["from_product", "to_product", "gap_min", "flush_factor", "manual_clean_required"],
        [[c["from_product"], c["to_product"], _v(c.get("gap_min")), _v(c.get("flush_factor")),
          _b(c.get("manual_clean_required"))] for c in doc.get("changeover") or []])
    files["groups.csv"] = write(["id", "name"], [[g["id"], g["name"]] for g in doc.get("tank_groups") or []])
    node_cols = ["id", "type", "name", "x", "y", "max_rate_m3h", "certified_products", "side_count", "cars_per_side",
                 "platform_id"]
    files["nodes.csv"] = write(node_cols, [
        [_l(n.get(c)) if c == "certified_products" else _v(n.get(c)) for c in node_cols] for n in doc["nodes"]])
    tank_cols = ["group_id", "product_id", "stock_m3", "capacity_m3", "min_heel_m3"]
    files["tanks.csv"] = write(
        ["node_id", *tank_cols, "allow_inbound", "allow_outbound", "allow_simultaneous"],
        [[n["id"], *[_v(n.get(c)) for c in tank_cols], _b(n.get("allow_inbound")), _b(n.get("allow_outbound")),
          _b(n.get("allow_simultaneous"))] for n in doc["nodes"] if n["type"] == "TANK"])
    el_cols = ["id", "type", "from", "to", "length_m", "diameter_mm", "elevation_delta_m", "installation", "roughness_mm",
               "certified_products", "dedicated_group_id", "dedicated_product_ids", "residue_product_id",
               "bidirectional", "tank_id", "head_m", "max_flow_m3h", "operate_min", "state"]
    lists, bools = {"certified_products", "dedicated_product_ids"}, {"bidirectional"}
    curve_cols = [
        "curve_model", "curve_min_flow_m3h", "curve_max_flow_m3h", "curve_shutoff_head_m",
        "curve_quadratic_coefficient", "curve_flow_points", "curve_head_points",
        "speed_ratio_min", "speed_ratio_max", "npsh_required_m", "npsh_margin_m",
    ]
    rows = []
    for element in doc["elements"]:
        curve = element.get("performance_curve") or {}
        base = [
            _l(element.get(column)) if column in lists else _b(element.get(column)) if column in bools else _v(element.get(column))
            for column in el_cols
        ]
        points = curve.get("points") or []
        curve_values = [
            _v(curve.get("model")),
            _v(curve.get("min_flow_m3h")),
            _v(curve.get("max_flow_m3h")),
            _v(curve.get("shutoff_head_m")),
            _v(curve.get("quadratic_coefficient")),
            _l([_v(point.get("flow_m3h")) for point in points]),
            _l([_v(point.get("head_m")) for point in points]),
            _v(curve.get("speed_ratio_min")),
            _v(curve.get("speed_ratio_max")),
            _v(element.get("npsh_required_m")),
            _v(element.get("npsh_margin_m")),
        ]
        rows.append(base + curve_values)
    files["elements.csv"] = write([*el_cols, *curve_cols], rows)
    files["pump_trains.csv"] = write(
        ["id", "arrangement", "member_pump_ids"],
        [[train["id"], train["arrangement"], _l(train.get("member_pump_ids"))] for train in doc.get("pump_trains") or []],
    )
    return files

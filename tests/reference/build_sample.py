"""Builds tests/reference/sample-terminal.json and the CSV bundle from the reference script data.

Run from the repo root: python tests/reference/build_sample.py
The reference script (lineup_cpsat.py) stays the single source of the sample numbers.
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import lineup_cpsat as ref

TYPE_MAP = {"JETTY": "LINE", "COMMON": "COMMON_HEADER", "TH": "TANK_HEADER", "SEG": "SEGMENT",
            "LOAD": "LINE", "PUMP": "PUMP", "VALVE": "VALVE"}
# tank headers in the sample feed junctions; the tank each one serves (reference "TH" elements)
TH_TANK = {6: "7", 7: "9"}
SEG_TANK = {8: "7", 9: "8", 10: "8", 11: "9"}
POS = {1: (0, 100), 2: (0, 200), 3: (150, 150), 12: (250, 150), 4: (350, 150), 5: (500, 100), 6: (500, 200),
       7: (650, 60), 8: (650, 150), 9: (650, 240), 13: (350, 320), 10: (200, 400), 11: (500, 400)}
NODE_TYPE = {1: "JETTY", 2: "JETTY", 7: "TANK", 8: "TANK", 9: "TANK", 10: "LOADING_POINT", 11: "LOADING_POINT"}
NAMES = {1: "Jetty1", 2: "Jetty2", 7: "T7", 8: "T8", 9: "T9", 10: "Load1", 11: "Load2"}


def pid(p):
    return None if p == 0 else str(p)


def build():
    nodes = []
    for n in sorted(POS):
        node = {"id": str(n), "type": NODE_TYPE.get(n, "JUNCTION"), "name": NAMES.get(n, f"J{n}"),
                "x": POS[n][0], "y": POS[n][1]}
        if n in ref.TANKS:
            t = ref.TANKS[n]
            node.update(group_id="G1", product_id=pid(t["prod"]), stock_m3=t["stock"], capacity_m3=t["cap"],
                        allow_inbound=True, allow_outbound=True, allow_simultaneous=False)
        if node["type"] in ("JETTY", "LOADING_POINT"):
            node.update(max_rate_m3h=2000, certified_products=["1", "2"])
        nodes.append(node)
    elements = []
    for e, (a, b, typ, length, diam, dz, pump, res, cert) in sorted(ref.E.items()):
        el = {"id": str(e), "type": TYPE_MAP[typ], "from": str(a), "to": str(b), "length_m": length,
              "diameter_mm": diam, "elevation_delta_m": dz, "installation": "ABOVEGROUND",
              "certified_products": [str(c) for c in sorted(cert)], "residue_product_id": pid(res),
              "bidirectional": typ != "PUMP"}
        if typ == "TH":
            el["tank_id"] = TH_TANK[e]
        if typ == "SEG":
            el["tank_id"] = SEG_TANK[e]
        if typ == "PUMP":
            el["head_m"] = pump
        if typ == "VALVE":
            el["operate_min"] = ref.VALVE_OP
            el["state"] = "OPEN"
        elements.append(el)
    products = [{"id": str(p), "name": f"Product {p}", "friction_factor": ref.FRIC[p], "max_velocity": ref.VMAX,
                 "color": "#E4572E" if p == 1 else "#2E86AB"} for p in (1, 2)]
    changeover = [{"from_product": str(a), "to_product": str(b), "gap_min": gap,
                   "flush_factor": ref.FLUSH_FACTOR.get((a, b), 0), "manual_clean_required": False}
                  for (a, b), gap in sorted(ref.CHANGEOVER.items())]
    return {"schema_version": "1.0", "name": "Reference sample terminal", "products": products,
            "changeover": changeover, "tank_groups": [{"id": "G1", "name": "Tank farm", "tank_ids": ["7", "8", "9"]}],
            "nodes": nodes, "elements": elements}


def write_csv(doc):
    out = HERE / "csv"
    out.mkdir(exist_ok=True)

    def w(name, header, rows):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(header)
            wr.writerows(rows)

    def j(v):
        return ";".join(v) if v else ""

    def b(v):
        return "true" if v else "false"

    w("products.csv", ["id", "name", "group", "friction_factor", "max_velocity", "color"],
      [[p["id"], p["name"], "", p["friction_factor"], p["max_velocity"], p["color"]] for p in doc["products"]])
    w("changeover.csv", ["from_product", "to_product", "gap_min", "flush_factor", "manual_clean_required"],
      [[c["from_product"], c["to_product"], c["gap_min"], c["flush_factor"], b(c["manual_clean_required"])]
       for c in doc["changeover"]])
    w("groups.csv", ["id", "name"], [[g["id"], g["name"]] for g in doc["tank_groups"]])
    w("nodes.csv", ["id", "type", "name", "x", "y", "max_rate_m3h", "certified_products"],
      [[n["id"], n["type"], n["name"], n["x"], n["y"], n.get("max_rate_m3h", ""), j(n.get("certified_products"))]
       for n in doc["nodes"]])
    w("tanks.csv", ["node_id", "group_id", "product_id", "stock_m3", "capacity_m3", "min_heel_m3", "allow_inbound",
                    "allow_outbound", "allow_simultaneous"],
      [[n["id"], n["group_id"], n["product_id"] or "", n["stock_m3"], n["capacity_m3"], "", b(n["allow_inbound"]),
        b(n["allow_outbound"]), b(n["allow_simultaneous"])] for n in doc["nodes"] if n["type"] == "TANK"])
    w("elements.csv", ["id", "type", "from", "to", "length_m", "diameter_mm", "elevation_delta_m", "installation",
                       "roughness_mm", "certified_products", "dedicated_group_id", "dedicated_product_ids",
                       "residue_product_id", "bidirectional", "tank_id", "head_m", "max_flow_m3h", "operate_min",
                       "state"],
      [[e["id"], e["type"], e["from"], e["to"], e["length_m"], e["diameter_mm"], e["elevation_delta_m"],
        e["installation"], "", j(e["certified_products"]), "", "", e["residue_product_id"] or "",
        b(e["bidirectional"]), e.get("tank_id", ""), e.get("head_m", ""), "", e.get("operate_min", ""),
        e.get("state", "")] for e in doc["elements"]])


if __name__ == "__main__":
    document = build()
    (HERE / "sample-terminal.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    write_csv(document)
    print("wrote sample-terminal.json and csv/")

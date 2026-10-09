from __future__ import annotations

from copy import deepcopy

from liquidtwin_engine.document import parse_document
from liquidtwin_engine.schema_models import TerminalDocument


def test_schema_10_constant_head_documents_remain_readable(sample):
    terminal = parse_document(sample)
    pump = next(element for element in terminal.elements.values() if element.type == "PUMP")
    assert pump.head_m > 0
    assert pump.performance_curve is None
    assert terminal.pump_trains == {}


def test_schema_11_pump_curve_and_train_fields_round_trip(sample):
    document = deepcopy(sample)
    document["schema_version"] = "1.1"
    pump = next(element for element in document["elements"] if element["type"] == "PUMP")
    pump["performance_curve"] = {
        "model": "TABULAR",
        "min_flow_m3h": 100,
        "max_flow_m3h": 1000,
        "points": [
            {"flow_m3h": 100, "head_m": 60},
            {"flow_m3h": 1000, "head_m": 40},
        ],
        "speed_ratio_min": 0.5,
        "speed_ratio_max": 1.0,
    }
    pump["npsh_required_m"] = 2.0
    pump["npsh_margin_m"] = 0.5
    pump_ids = [element["id"] for element in document["elements"] if element["type"] == "PUMP"]
    document["pump_trains"] = [{"id": "train-1", "arrangement": "SERIES", "member_pump_ids": pump_ids}]

    parsed = TerminalDocument.model_validate(document).model_dump(mode="json", by_alias=True)
    terminal = parse_document(parsed)

    assert terminal.elements[pump["id"]].performance_curve["model"] == "TABULAR"
    assert terminal.elements[pump["id"]].npsh_required_m == 2.0
    assert terminal.pump_trains["train-1"].member_pump_ids == tuple(pump_ids)

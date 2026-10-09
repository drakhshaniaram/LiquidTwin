"""JSON and CSV import of the same terminal must give identical documents (SC-005)."""
import json
from pathlib import Path

HERE = Path(__file__).parent

from liquidtwin_engine.csv_import import import_csv_bundle
from liquidtwin_engine.document import parse_document


def test_import_equivalence():
    json_doc = json.loads((HERE / "sample-terminal.json").read_text(encoding="utf-8"))
    files = {p.name: p.read_text(encoding="utf-8") for p in (HERE / "csv").glob("*.csv")}
    res = import_csv_bundle(files, json_doc["name"])
    assert res.document is not None, res.issues
    assert parse_document(res.document) == parse_document(json_doc)

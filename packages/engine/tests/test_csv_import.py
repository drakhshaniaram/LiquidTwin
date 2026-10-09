from pathlib import Path

from liquidtwin_engine.csv_import import import_csv_bundle
from liquidtwin_engine.export import to_csv_bundle

CSV_DIR = Path(__file__).resolve().parents[3] / "tests" / "reference" / "csv"


def bundle():
    return {p.name: p.read_text(encoding="utf-8") for p in CSV_DIR.glob("*.csv")}


def test_reference_bundle_imports_cleanly():
    res = import_csv_bundle(bundle(), "x")
    assert res.document is not None, res.issues
    assert not [i for i in res.issues if i.severity == "ERROR"]


def test_unknown_column_rejected():
    files = bundle()
    files["nodes.csv"] = files["nodes.csv"].replace("max_rate_m3h", "max_rate_typo", 1)
    res = import_csv_bundle(files, "x")
    assert res.document is None
    assert any(i.code == "UNKNOWN_COLUMN" and i.file == "nodes.csv" and i.row == 1 for i in res.issues)


def test_x_columns_are_ignored():
    files = bundle()
    files["nodes.csv"] = files["nodes.csv"].replace("max_rate_m3h", "x_note", 1)
    assert import_csv_bundle(files, "x").document is not None


def test_bad_number_reports_row():
    files = bundle()
    lines = files["elements.csv"].splitlines()
    lines[2] = lines[2].replace(",350,", ",abc,", 1)
    files["elements.csv"] = "\n".join(lines) + "\n"
    res = import_csv_bundle(files, "x")
    assert res.document is None
    assert any(i.code == "BAD_VALUE" and i.file == "elements.csv" and i.row == 3 for i in res.issues)


def test_missing_required_file():
    files = bundle()
    del files["products.csv"]
    res = import_csv_bundle(files, "x")
    assert res.document is None and any(i.code == "MISSING_FILE" for i in res.issues)


def test_foreign_key_failure_is_all_or_nothing():
    files = bundle()
    files["elements.csv"] = files["elements.csv"].replace(",1,3,", ",1,99,", 1)
    res = import_csv_bundle(files, "x")
    assert res.document is None and any(i.code == "DANGLING_ELEMENT" for i in res.issues)


def test_export_roundtrip_is_identical_terminal():
    from liquidtwin_engine.document import parse_document
    first = import_csv_bundle(bundle(), "Reference sample terminal").document
    second = import_csv_bundle(to_csv_bundle(first), "Reference sample terminal").document
    assert parse_document(first) == parse_document(second)

from liquidtwin_engine.validation import validate_document


def codes(issues, severity=None):
    return {i.code for i in issues if severity is None or i.severity == severity}


def test_sample_has_no_errors(sample):
    assert codes(validate_document(sample), "ERROR") == set()


def test_dangling_element(sample):
    sample["elements"][0]["to"] = "999"
    issues = validate_document(sample)
    assert "DANGLING_ELEMENT" in codes(issues)
    bad = next(i for i in issues if i.code == "DANGLING_ELEMENT")
    assert bad.element_id == "1" and bad.fix_hint


def test_duplicate_ids(sample):
    sample["nodes"].append(dict(sample["nodes"][0]))
    assert "DUPLICATE_ID" in codes(validate_document(sample))


def test_stock_over_capacity(sample):
    tank = next(n for n in sample["nodes"] if n["id"] == "7")
    tank["stock_m3"] = tank["capacity_m3"] + 1
    assert "STOCK_OVER_CAPACITY" in codes(validate_document(sample))


def test_unknown_product(sample):
    next(n for n in sample["nodes"] if n["id"] == "7")["product_id"] = "99"
    assert "UNKNOWN_PRODUCT" in codes(validate_document(sample))


def test_header_must_reference_tank(sample):
    next(e for e in sample["elements"] if e["id"] == "8")["tank_id"] = "5"  # a junction
    assert "BAD_TANK_REF" in codes(validate_document(sample))


def test_header_serving_two_tank_headers_warns(sample):
    next(e for e in sample["elements"] if e["id"] == "7")["tank_id"] = "7"
    assert "MULTI_HEADER" in codes(validate_document(sample), "WARNING")


def test_isolated_node_warns(sample):
    sample["nodes"].append({"id": "99", "type": "JUNCTION"})
    assert "ISOLATED_NODE" in codes(validate_document(sample), "WARNING")


def test_schema_error_reported(sample):
    sample["elements"][0]["diameter_mm"] = -5
    issues = validate_document(sample)
    assert any(i.code == "SCHEMA" and i.severity == "ERROR" for i in issues)


def test_rail_car_needs_platform(sample):
    sample["nodes"].append({"id": "50", "type": "RAIL_CAR", "platform_id": "1"})
    assert "BAD_PLATFORM" in codes(validate_document(sample))

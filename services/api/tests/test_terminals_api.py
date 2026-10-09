from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from liquidtwin_api.db.models import Base
from liquidtwin_api.db.session import get_db
from liquidtwin_api.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_database() -> Generator:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def document(name: str = "North Terminal") -> dict:
    return {
        "schema_version": "1.0",
        "name": name,
        "products": [],
        "nodes": [],
        "elements": [],
    }


def import_document() -> dict:
    result = document()
    result["products"] = [{"id": "P1", "name": "Product 1"}]
    result["nodes"] = [
        {"id": "jetty-1", "type": "JETTY", "name": "Jetty 1", "x": 20, "y": 40},
        {"id": "tank-1", "type": "TANK", "name": "Tank 1", "product_id": "P1", "stock_m3": 10, "capacity_m3": 1000},
    ]
    result["elements"] = [
        {
            "id": "line-1",
            "type": "LINE",
            "from": "jetty-1",
            "to": "tank-1",
            "length_m": 100,
            "diameter_mm": 300,
            "certified_products": ["P1"],
        }
    ]
    return result


def test_register_terminal_lists_and_opens_initial_version(client: TestClient) -> None:
    response = client.post("/api/v1/terminals", json={"name": "North Terminal", "document": document()})

    assert response.status_code == 201
    terminal = response.json()
    assert terminal["name"] == "North Terminal"
    assert terminal["current_version"] == 1

    listed = client.get("/api/v1/terminals")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [terminal["id"]]

    opened = client.get(f"/api/v1/terminals/{terminal['id']}")
    assert opened.status_code == 200
    assert opened.json()["document"]["name"] == "North Terminal"
    assert opened.json()["version"] == 1


def test_schema_11_pump_curve_document_round_trips_through_api(client: TestClient) -> None:
    curve_document = document()
    curve_document["schema_version"] = "1.1"
    curve_document["products"] = [{"id": "P1", "name": "Product 1"}]
    curve_document["nodes"] = [
        {"id": "junction-1", "type": "JUNCTION"},
        {"id": "junction-2", "type": "JUNCTION"},
    ]
    curve_document["elements"] = [
        {
            "id": "pump-1",
            "type": "PUMP",
            "from": "junction-1",
            "to": "junction-2",
            "head_m": 50,
            "performance_curve": {
                "model": "QUADRATIC",
                "min_flow_m3h": 100,
                "max_flow_m3h": 1000,
                "shutoff_head_m": 60,
                "quadratic_coefficient": 0.00001,
                "speed_ratio_min": 0.5,
                "speed_ratio_max": 1,
            },
            "npsh_required_m": 2,
            "npsh_margin_m": 0.5,
        },
        {
            "id": "pump-2",
            "type": "PUMP",
            "from": "junction-2",
            "to": "junction-1",
            "head_m": 40,
        },
    ]
    curve_document["pump_trains"] = [
        {"id": "train-1", "arrangement": "SERIES", "member_pump_ids": ["pump-1", "pump-2"]}
    ]

    created = client.post("/api/v1/terminals", json={"name": "Curve terminal", "document": curve_document})

    assert created.status_code == 201
    loaded = client.get(f"/api/v1/terminals/{created.json()['id']}")
    assert loaded.status_code == 200
    stored = loaded.json()["document"]
    assert stored["schema_version"] == "1.1"
    assert stored["elements"][0]["performance_curve"]["model"] == "QUADRATIC"
    assert stored["pump_trains"][0]["member_pump_ids"] == ["pump-1", "pump-2"]


def test_terminal_versions_append_restore_and_delete(client: TestClient) -> None:
    created = client.post("/api/v1/terminals", json={"name": "North Terminal", "document": document()})
    terminal_id = created.json()["id"]
    revised_document = document("North Terminal revised")
    revised_document["elements"] = [
        {
            "id": "pipe-1",
            "type": "LINE",
            "from": "jetty-1",
            "to": "tank-1",
            "length_m": 120,
            "diameter_mm": 300,
            "installation": "ABOVEGROUND",
        }
    ]

    saved = client.post(
        f"/api/v1/terminals/{terminal_id}/versions",
        json={"document": revised_document, "note": "Layout update"},
    )
    assert saved.status_code == 201
    assert saved.json()["version"] == 2
    saved_document = client.get(f"/api/v1/terminals/{terminal_id}?version=2").json()["document"]
    assert saved_document["elements"][0]["from"] == "jetty-1"
    assert "from_" not in saved_document["elements"][0]

    restored = client.post(f"/api/v1/terminals/{terminal_id}/versions", json={"restore_from": 1})
    assert restored.status_code == 201
    assert restored.json()["version"] == 3

    opened = client.get(f"/api/v1/terminals/{terminal_id}")
    assert opened.json()["document"]["name"] == "North Terminal"
    assert len(client.get(f"/api/v1/terminals/{terminal_id}/versions").json()) == 3

    deleted = client.delete(f"/api/v1/terminals/{terminal_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/terminals/{terminal_id}").status_code == 404


def test_validate_route_returns_engine_issues_for_supplied_document(client: TestClient) -> None:
    created = client.post("/api/v1/terminals", json={"name": "North Terminal", "document": document()})
    terminal_id = created.json()["id"]
    invalid_document = document()
    invalid_document["nodes"] = [
        {"id": "tank-1", "type": "TANK", "capacity_m3": 5000},
        {"id": "jetty-1", "type": "JETTY"},
    ]
    invalid_document["elements"] = [
        {
            "id": "pipe-1",
            "type": "LINE",
            "from": "jetty-1",
            "to": "missing-node",
            "length_m": 100,
            "diameter_mm": 300,
        }
    ]

    response = client.post(
        f"/api/v1/terminals/{terminal_id}/validate",
        json={"document": invalid_document},
    )

    assert response.status_code == 200
    issue = next(issue for issue in response.json()["issues"] if issue["code"] == "DANGLING_ELEMENT")
    assert issue["severity"] == "ERROR"
    assert issue["element_id"] == "pipe-1"
    assert issue["fix_hint"] == "Connect the pipe to existing equipment"


def test_graph_projection_preserves_parallel_edges_and_directionality(client: TestClient) -> None:
    graph_document = document()
    graph_document["nodes"] = [
        {"id": "jetty-1", "type": "JETTY", "name": "Jetty 1", "x": 20, "y": 40},
        {"id": "junction-1", "type": "JUNCTION"},
        {"id": "tank-1", "type": "TANK", "capacity_m3": 5000},
        {"id": "tank-2", "type": "TANK", "capacity_m3": 5000},
    ]
    graph_document["elements"] = [
        {"id": "line-1", "type": "LINE", "from": "jetty-1", "to": "junction-1", "length_m": 100, "diameter_mm": 300},
        {"id": "line-2", "type": "LINE", "from": "jetty-1", "to": "junction-1", "length_m": 120, "diameter_mm": 250},
        {"id": "pump-1", "type": "PUMP", "from": "junction-1", "to": "tank-1", "length_m": 0, "diameter_mm": 300, "head_m": 0},
    ]
    created = client.post("/api/v1/terminals", json={"name": "North Terminal", "document": graph_document})

    response = client.get(f"/api/v1/terminals/{created.json()['id']}/graph")

    assert response.status_code == 200
    body = response.json()
    assert body["terminal_version"] == 1
    assert len(body["nodes"]) == 4
    assert body["nodes"][0]["x"] == 20
    parallel = [arc for arc in body["arcs"] if arc["from"] == "jetty-1" and arc["to"] == "junction-1"]
    assert {arc["element_id"] for arc in parallel} == {"line-1", "line-2"}
    reverse_pump = next(arc for arc in body["arcs"] if arc["element_id"] == "pump-1" and arc["reversed"])
    assert reverse_pump["traversable"] is False
    assert reverse_pump["restriction"] == "ONE_WAY_PUMP"


def test_graph_projection_rejects_semantically_invalid_documents(client: TestClient) -> None:
    invalid_document = document()
    invalid_document["nodes"] = [{"id": "jetty-1", "type": "JETTY"}]
    invalid_document["elements"] = [
        {"id": "line-1", "type": "LINE", "from": "jetty-1", "to": "missing", "length_m": 10, "diameter_mm": 100}
    ]
    created = client.post("/api/v1/terminals", json={"name": "North Terminal", "document": invalid_document})

    response = client.get(f"/api/v1/terminals/{created.json()['id']}/graph")

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_TERMINAL_GRAPH"
    assert any(issue["code"] == "DANGLING_ELEMENT" for issue in response.json()["issues"])


def test_graph_projection_returns_topology_with_nonstructural_validation_issues(client: TestClient) -> None:
    document_with_issue = document()
    document_with_issue["nodes"] = [{"id": "rail-car-1", "type": "RAIL_CAR"}]
    created = client.post("/api/v1/terminals", json={"name": "North Terminal", "document": document_with_issue})

    response = client.get(f"/api/v1/terminals/{created.json()['id']}/graph")

    assert response.status_code == 200
    assert [node["id"] for node in response.json()["nodes"]] == ["rail-car-1"]
    assert any(issue["code"] == "BAD_PLATFORM" for issue in response.json()["issues"])


def test_import_json_creates_terminal_and_preserves_document(client: TestClient) -> None:
    source = import_document()

    response = client.post(
        "/api/v1/terminals/import",
        json={"name": "Imported JSON", "document": source},
    )

    assert response.status_code == 201
    terminal_id = response.json()["id"]
    opened = client.get(f"/api/v1/terminals/{terminal_id}")
    assert opened.status_code == 200
    assert opened.json()["document"]["elements"][0]["id"] == "line-1"


def test_import_csv_bundle_is_all_or_nothing_and_export_round_trips(client: TestClient) -> None:
    from liquidtwin_engine.export import to_csv_bundle

    source = import_document()
    files = [
        ("files", (filename, content, "text/csv"))
        for filename, content in to_csv_bundle(source).items()
    ]
    imported = client.post(
        "/api/v1/terminals/import",
        data={"name": "Imported CSV"},
        files=files,
    )

    assert imported.status_code == 201
    terminal_id = imported.json()["id"]
    opened = client.get(f"/api/v1/terminals/{terminal_id}")
    assert opened.status_code == 200
    assert opened.json()["document"]["elements"][0]["from"] == "jetty-1"

    json_export = client.get(f"/api/v1/terminals/{terminal_id}/export?format=json")
    assert json_export.status_code == 200
    assert json_export.json()["elements"][0]["id"] == "line-1"

    csv_export = client.get(f"/api/v1/terminals/{terminal_id}/export?format=csv")
    assert csv_export.status_code == 200
    with zipfile.ZipFile(io.BytesIO(csv_export.content)) as archive:
        assert {"products.csv", "nodes.csv", "elements.csv", "tanks.csv"}.issubset(archive.namelist())
        assert "jetty-1" in archive.read("elements.csv").decode("utf-8")

    invalid_files = [("files", ("products.csv", "id,name\n,Missing ID\n", "text/csv"))]
    rejected = client.post(
        "/api/v1/terminals/import",
        data={"name": "Rejected CSV"},
        files=invalid_files,
    )
    assert rejected.status_code == 422
    assert rejected.json()["issues"]
    listed = client.get("/api/v1/terminals").json()
    assert [terminal["id"] for terminal in listed] == [terminal_id]


def route_request() -> dict:
    return {
        "direction": "IN",
        "product_id": "P1",
        "volume_m3": 50,
        "rate_m3h": 100,
        "window_from": "2026-10-09T12:00:00Z",
        "source_ids": ["jetty-1"],
        "destination_ids": ["tank-1"],
        "max_routes": 5,
    }


def test_routes_api_returns_ranked_routes_and_confirmed_history(client: TestClient) -> None:
    created = client.post(
        "/api/v1/terminals",
        json={"name": "Route terminal", "document": import_document()},
    )
    terminal_id = created.json()["id"]

    response = client.post(f"/api/v1/terminals/{terminal_id}/routes", json=route_request())

    assert response.status_code == 200
    body = response.json()
    assert body["terminal_version"] == 1
    assert body["engine_version"]
    assert [route["rank"] for route in body["routes"]] == [1]
    assert body["routes"][0]["steps"][0]["element_id"] == "line-1"

    confirmed = client.post(
        f"/api/v1/terminals/{terminal_id}/routes/confirm",
        json={"request": route_request(), "route": body["routes"][0]},
    )
    assert confirmed.status_code == 201
    assert confirmed.json()["terminal_version"] == 1
    assert confirmed.json()["outdated"] is False
    history = client.get(f"/api/v1/terminals/{terminal_id}/routes/confirmed")
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["route"]["steps"][0]["element_id"] == "line-1"


def test_routes_api_explains_when_no_certified_path_exists(client: TestClient) -> None:
    terminal_document = import_document()
    terminal_document["elements"][0]["certified_products"] = []
    created = client.post(
        "/api/v1/terminals",
        json={"name": "Blocked terminal", "document": terminal_document},
    )

    response = client.post(f"/api/v1/terminals/{created.json()['id']}/routes", json=route_request())

    assert response.status_code == 200
    assert response.json()["routes"] == []
    assert response.json()["no_route"]["blockers"][0]["reason"] == "NOT_CERTIFIED"


def test_curve_route_api_requires_suction_input_and_reports_operating_point(client: TestClient) -> None:
    terminal_document = import_document()
    terminal_document["schema_version"] = "1.1"
    terminal_document["nodes"].insert(1, {"id": "junction-1", "type": "JUNCTION"})
    pump = {
        "id": "pump-1",
        "type": "PUMP",
        "from": "jetty-1",
        "to": "junction-1",
        "length_m": 0,
        "diameter_mm": 300,
        "head_m": 50,
        "certified_products": ["P1"],
        "performance_curve": {
            "model": "TABULAR",
            "min_flow_m3h": 100,
            "max_flow_m3h": 1000,
            "points": [
                {"flow_m3h": 100, "head_m": 60},
                {"flow_m3h": 1000, "head_m": 10},
            ],
            "speed_ratio_min": 1.0,
            "speed_ratio_max": 1.0,
        },
        "npsh_required_m": 2.0,
        "npsh_margin_m": 0.5,
    }
    terminal_document["elements"] = [
        pump,
        {
            "id": "line-1",
            "type": "LINE",
            "from": "junction-1",
            "to": "tank-1",
            "length_m": 2000,
            "diameter_mm": 300,
            "certified_products": ["P1"],
        },
    ]
    created = client.post(
        "/api/v1/terminals",
        json={"name": "Curve route terminal", "document": terminal_document},
    )
    terminal_id = created.json()["id"]
    request = {
        **route_request(),
        "product_id": "P1",
        "volume_m3": 100,
        "rate_m3h": 400,
        "pump_suction_inputs": [{"pump_id": "pump-1", "npsh_available_m": 4.0}],
    }

    response = client.post(f"/api/v1/terminals/{terminal_id}/routes", json=request)

    assert response.status_code == 200
    assert response.json()["routes"], response.json()
    metrics = response.json()["routes"][0]["metrics"]
    assert metrics["operating_flow_m3h"] >= 400
    assert metrics["suction_margin_m"] == 1.5
    assert metrics["pump_speed_ratio"] == 1.0

    missing_suction = {key: value for key, value in request.items() if key != "pump_suction_inputs"}
    rejected = client.post(f"/api/v1/terminals/{terminal_id}/routes", json=missing_suction)

    assert rejected.status_code == 200
    assert rejected.json()["routes"] == []
    suction_exclusion = next(
        item for item in rejected.json()["exclusions"] if item["reason"] == "PUMP_SUCTION_MARGIN"
    )
    assert suction_exclusion["element_id"] == "pump-1"


def test_optimization_prepare_returns_candidates_and_no_route_blockers(client: TestClient) -> None:
    terminal_document = import_document()
    terminal_document["products"].append({"id": "P2", "name": "Product 2"})
    next(node for node in terminal_document["nodes"] if node["id"] == "tank-1")["product_id"] = None
    created = client.post(
        "/api/v1/terminals",
        json={"name": "Optimization terminal", "document": terminal_document},
    )
    terminal_id = created.json()["id"]
    scenario = {
        "terminal_version": 1,
        "horizon_start": "2026-10-09T00:00:00Z",
        "horizon_minutes": 1000,
        "jobs": [
            {
                "id": "job-candidate",
                "direction": "IN",
                "product_id": "P1",
                "source_ids": ["jetty-1"],
                "destination_ids": ["tank-1"],
                "volume_m3": 10,
                "rate_m3h": 1,
                "earliest_start_min": 0,
                "due_min": 100,
            },
            {
                "id": "job-blocked",
                "direction": "IN",
                "product_id": "P2",
                "source_ids": ["jetty-1"],
                "destination_ids": ["tank-1"],
                "volume_m3": 10,
                "rate_m3h": 1,
                "earliest_start_min": 0,
                "due_min": 100,
            },
        ],
    }

    response = client.post(
        f"/api/v1/terminals/{terminal_id}/optimization/prepare", json=scenario
    )

    assert response.status_code == 200
    prepared = response.json()["jobs"]
    assert prepared[0]["job_id"] == "job-candidate"
    assert prepared[0]["routes"]
    assert prepared[1]["job_id"] == "job-blocked"
    assert prepared[1]["routes"] == []
    assert any(item["reason"] == "NOT_CERTIFIED" for item in prepared[1]["blockers"])


def test_optimization_api_matches_reference_objective(client: TestClient) -> None:
    reference_path = Path(__file__).resolve().parents[3] / "tests" / "reference" / "sample-terminal.json"
    terminal_document = json.loads(reference_path.read_text(encoding="utf-8"))
    created = client.post(
        "/api/v1/terminals",
        json={"name": "Optimization reference", "document": terminal_document},
    )
    terminal_id = created.json()["id"]
    scenario = {
        "terminal_version": 1,
        "horizon_start": "2026-10-09T00:00:00Z",
        "horizon_minutes": 1000,
        "jobs": [
            {"id": "job-1", "direction": "IN", "product_id": "1", "source_ids": ["1"], "destination_ids": ["7", "9"], "volume_m3": 4000, "rate_m3h": 1000, "earliest_start_min": 0, "due_min": 400},
            {"id": "job-2", "direction": "IN", "product_id": "2", "source_ids": ["2"], "destination_ids": ["8", "9"], "volume_m3": 3000, "rate_m3h": 800, "earliest_start_min": 30, "due_min": 600},
            {"id": "job-3", "direction": "IN", "product_id": "1", "source_ids": ["7", "9"], "destination_ids": ["10"], "volume_m3": 600, "rate_m3h": 300, "earliest_start_min": 60, "due_min": 480},
            {"id": "job-4", "direction": "IN", "product_id": "2", "source_ids": ["8", "9"], "destination_ids": ["11"], "volume_m3": 500, "rate_m3h": 250, "earliest_start_min": 100, "due_min": 400},
        ],
    }

    client.post(
        f"/api/v1/terminals/{terminal_id}/availability",
        json={"windows": [{"element_id": "7", "status": "MAINTENANCE", "from": "2026-10-09T00:00:00Z", "to": "2026-10-09T02:00:00Z", "source": "test"}]},
    )
    response = client.post(f"/api/v1/terminals/{terminal_id}/optimize", json=scenario)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "OPTIMAL"
    assert result["detail"] == "Optimality proven."
    assert result["objective"] == 1327
    assert len(result["scheduled_jobs"]) == 4
    assert result["kpis"]["on_time_jobs"] == 4
    assert result["element_timeline"]


def test_availability_upsert_filters_routes_and_marks_confirmations_outdated(client: TestClient) -> None:
    created = client.post(
        "/api/v1/terminals",
        json={"name": "Availability terminal", "document": import_document()},
    )
    terminal_id = created.json()["id"]
    request = route_request()
    route_response = client.post(f"/api/v1/terminals/{terminal_id}/routes", json=request)
    confirmed = client.post(
        f"/api/v1/terminals/{terminal_id}/routes/confirm",
        json={"request": request, "route": route_response.json()["routes"][0]},
    )
    assert confirmed.status_code == 201

    window = {
        "element_id": "line-1",
        "status": "MAINTENANCE",
        "from": "2026-10-09T11:00:00Z",
        "to": "2026-10-09T14:00:00Z",
        "reason": "Inspection",
        "source": "external-feed",
        "external_ref": "work-order-9",
    }
    update = client.post(
        f"/api/v1/terminals/{terminal_id}/availability",
        json={"windows": [window, {**window, "element_id": "missing-element", "external_ref": "unknown-1"}]},
    )

    assert update.status_code == 200
    assert update.json()["applied"] == 1
    assert update.json()["rejected"] == [{"index": 1, "reason": "Unknown element missing-element"}]
    repeated = client.post(f"/api/v1/terminals/{terminal_id}/availability", json={"windows": [window]})
    assert repeated.status_code == 200
    assert len(client.get(f"/api/v1/terminals/{terminal_id}/availability?element_id=line-1").json()) == 1
    assert len(
        client.get(
            f"/api/v1/terminals/{terminal_id}/availability?from=2026-10-09T15:00:00Z"
        ).json()
    ) == 0
    assert len(
        client.get(
            f"/api/v1/terminals/{terminal_id}/availability?to=2026-10-09T10:00:00Z"
        ).json()
    ) == 0

    blocked = client.post(f"/api/v1/terminals/{terminal_id}/routes", json=request)
    assert blocked.json()["routes"] == []
    assert blocked.json()["no_route"]["blockers"][0]["reason"] == "UNAVAILABLE"
    history = client.get(f"/api/v1/terminals/{terminal_id}/routes/confirmed").json()
    assert history[0]["outdated"] is True

    window_id = client.get(f"/api/v1/terminals/{terminal_id}/availability").json()[0]["id"]
    assert client.delete(f"/api/v1/terminals/{terminal_id}/availability/{window_id}").status_code == 204
    restored = client.post(f"/api/v1/terminals/{terminal_id}/routes", json=request)
    assert restored.json()["routes"]


def test_availability_batch_limit_is_5000(client: TestClient) -> None:
    created = client.post("/api/v1/terminals", json={"name": "Availability limit", "document": document()})
    window = {
        "element_id": "pipe-1",
        "status": "MAINTENANCE",
        "from": "2026-10-09T11:00:00Z",
    }

    response = client.post(
        f"/api/v1/terminals/{created.json()['id']}/availability",
        json={"windows": [window] * 5001},
    )

    assert response.status_code == 422


def test_csv_import_persists_availability_windows(client: TestClient) -> None:
    from liquidtwin_engine.export import to_csv_bundle

    source = import_document()
    files = to_csv_bundle(source)
    files["availability.csv"] = (
        "element_id,status,from,to,reason,source,external_ref\n"
        "line-1,MAINTENANCE,2026-10-09T11:00:00Z,2026-10-09T14:00:00Z,Inspection,csv-feed,window-1\n"
    )
    upload = [("files", (filename, content, "text/csv")) for filename, content in files.items()]

    imported = client.post(
        "/api/v1/terminals/import",
        data={"name": "CSV availability"},
        files=upload,
    )

    assert imported.status_code == 201
    availability = client.get(f"/api/v1/terminals/{imported.json()['id']}/availability")
    assert availability.status_code == 200
    assert len(availability.json()) == 1
    assert availability.json()[0]["element_id"] == "line-1"
    assert availability.json()[0]["source"] == "csv-feed"
from __future__ import annotations

from collections.abc import Generator

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
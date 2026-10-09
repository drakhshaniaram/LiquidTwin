from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from liquidtwin_api.db.models import AvailabilityWindow as AvailabilityWindowRecord
from liquidtwin_api.db.models import ConfirmedRoute
from liquidtwin_api.db.repository import TerminalRepository
from liquidtwin_api.db.session import get_db
from liquidtwin_engine.document import parse_document
from liquidtwin_engine.graph import build_graph
from liquidtwin_engine.routing import ENGINE_VERSION, route_job
from liquidtwin_engine.types import AvailabilityWindow, RouteRequest
from liquidtwin_engine.validation import validate_document

router = APIRouter(tags=["routes"])


class RouteRequestBody(BaseModel):
    version: int | None = Field(default=None, ge=1)
    direction: Literal["IN", "OUT", "TRANSFER"]
    product_id: str
    volume_m3: float = Field(gt=0)
    rate_m3h: float = Field(gt=0)
    window_from: datetime
    window_to: datetime | None = None
    source_ids: list[str] = Field(min_length=1)
    destination_ids: list[str] = Field(min_length=1)
    max_routes: int = Field(default=5, ge=1, le=20)
    pump_suction_inputs: list[PumpSuctionInputBody] = Field(default_factory=list)


class PumpSuctionInputBody(BaseModel):
    pump_id: str = Field(min_length=1, max_length=64)
    npsh_available_m: float = Field(ge=0)


class ConfirmRouteBody(BaseModel):
    request: RouteRequestBody
    route: dict[str, Any]


def _minutes(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp() / 60


def _engine_request(body: RouteRequestBody) -> RouteRequest:
    return RouteRequest(
        direction=body.direction,
        product_id=body.product_id,
        volume_m3=body.volume_m3,
        rate_m3h=body.rate_m3h,
        window_from_min=_minutes(body.window_from),
        source_ids=tuple(body.source_ids),
        destination_ids=tuple(body.destination_ids),
        window_to_min=_minutes(body.window_to) if body.window_to else None,
        max_routes=body.max_routes,
        pump_suction_inputs=tuple(
            (item.pump_id, item.npsh_available_m)
            for item in body.pump_suction_inputs
        ),
    )


def _availability(session: Session, terminal_id: UUID) -> list[AvailabilityWindow]:
    records = session.scalars(
        select(AvailabilityWindowRecord).where(AvailabilityWindowRecord.terminal_id == terminal_id)
    )
    return [
        AvailabilityWindow(
            element_id=record.element_id,
            status=record.status,
            start_min=_minutes(record.starts_at),
            end_min=_minutes(record.ends_at) if record.ends_at else None,
            reason=record.reason or "",
        )
        for record in records
    ]


def _serialize_exclusion(exclusion) -> dict[str, Any]:
    result = {"reason": exclusion.reason.value, "detail": exclusion.detail}
    if exclusion.element_id is not None:
        result["element_id"] = exclusion.element_id
    if exclusion.node_id is not None:
        result["node_id"] = exclusion.node_id
    return result


def _serialize_route(route) -> dict[str, Any]:
    return {
        "rank": route.rank,
        "source_id": route.source_id,
        "destination_id": route.destination_id,
        "steps": [
            {
                "element_id": step.element_id,
                "from": step.from_node,
                "to": step.to_node,
                "reversed": step.reversed,
            }
            for step in route.steps
        ],
        "metrics": asdict(route.metrics),
    }


def _route_identity(route: dict[str, Any]) -> tuple[Any, ...]:
    steps = route.get("steps")
    if not isinstance(steps, list):
        return ()
    return (
        route.get("source_id"),
        route.get("destination_id"),
        tuple(
            (step.get("element_id"), step.get("from"), step.get("to"), step.get("reversed"))
            for step in steps
            if isinstance(step, dict)
        ),
    )


def _route_search(
    terminal_id: UUID,
    body: RouteRequestBody,
    session: Session,
):
    repository = TerminalRepository(session)
    terminal = repository.get_terminal(terminal_id)
    document = repository.load_document(terminal_id, body.version)
    if terminal is None or document is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Terminal or version not found"})
    issues = validate_document(document)
    errors = [issue for issue in issues if issue.severity == "ERROR"]
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_TERMINAL", "message": "Terminal contains errors that prevent routing"},
        )
    graph = build_graph(parse_document(document))
    result = route_job(graph, _engine_request(body), _availability(session, terminal_id))
    return terminal.current_version if body.version is None else body.version, result


def _route_response(terminal_version: int, result) -> dict[str, Any]:
    response: dict[str, Any] = {
        "terminal_version": terminal_version,
        "engine_version": ENGINE_VERSION,
        "routes": [_serialize_route(route) for route in result.routes],
        "exclusions": [_serialize_exclusion(exclusion) for exclusion in result.exclusions],
    }
    if result.no_route is not None:
        response["no_route"] = {
            "message": result.no_route.message,
            "blockers": [_serialize_exclusion(item) for item in result.no_route.blockers],
        }
    return response


@router.post("/terminals/{terminal_id}/routes", response_model=None)
def get_routes(
    terminal_id: UUID,
    body: RouteRequestBody,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    terminal_version, result = _route_search(terminal_id, body, session)
    return _route_response(terminal_version, result)


@router.post("/terminals/{terminal_id}/routes/confirm", status_code=201, response_model=None)
def confirm_route(
    terminal_id: UUID,
    body: ConfirmRouteBody,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    terminal_version, result = _route_search(terminal_id, body.request, session)
    routes = [_serialize_route(route) for route in result.routes]
    selected_identity = _route_identity(body.route)
    selected = next((route for route in routes if _route_identity(route) == selected_identity), None)
    if selected is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "ROUTE_NOT_AVAILABLE", "message": "The selected route is not in the current feasible shortlist"},
        )

    record = ConfirmedRoute(
        terminal_id=terminal_id,
        terminal_version=terminal_version,
        request=body.request.model_dump(mode="json", exclude_none=True),
        route=selected,
        outdated=False,
        actor="anonymous",
    )
    session.add(record)
    session.flush()
    session.commit()
    return {
        "id": str(record.id),
        "terminal_version": record.terminal_version,
        "request": record.request,
        "route": record.route,
        "outdated": record.outdated,
        "created_at": record.created_at,
    }


@router.get("/terminals/{terminal_id}/routes/confirmed")
def list_confirmed_routes(terminal_id: UUID, session: Session = Depends(get_db)) -> list[dict[str, Any]]:
    if TerminalRepository(session).get_terminal(terminal_id) is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Terminal not found"})
    records = session.scalars(
        select(ConfirmedRoute)
        .where(ConfirmedRoute.terminal_id == terminal_id)
        .order_by(ConfirmedRoute.created_at.desc())
    )
    return [
        {
            "id": str(record.id),
            "terminal_version": record.terminal_version,
            "request": record.request,
            "route": record.route,
            "outdated": record.outdated,
            "outdated_reason": record.outdated_reason,
            "created_at": record.created_at,
        }
        for record in records
    ]
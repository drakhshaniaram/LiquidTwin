from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from liquidtwin_api.db.models import AvailabilityWindow, ConfirmedRoute
from liquidtwin_api.db.repository import TerminalRepository
from liquidtwin_api.db.session import get_db

router = APIRouter(prefix="/terminals/{terminal_id}/availability", tags=["availability"])
AvailabilityStatus = Literal["AVAILABLE", "MAINTENANCE", "FLUSHING", "CLEANING", "OUT_OF_SERVICE"]


class AvailabilityWindowInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    element_id: str = Field(min_length=1, max_length=64)
    status: AvailabilityStatus
    starts_at: datetime = Field(alias="from")
    ends_at: datetime | None = Field(default=None, alias="to")
    reason: str | None = None
    source: str = Field(default="manual", max_length=120)
    external_ref: str | None = Field(default=None, max_length=255)


class AvailabilityBatch(BaseModel):
    windows: list[AvailabilityWindowInput] = Field(max_length=5000)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _overlaps_route(confirmed: ConfirmedRoute, starts_at: datetime, ends_at: datetime | None) -> bool:
    route_elements = {
        step.get("element_id")
        for step in confirmed.route.get("steps", [])
        if isinstance(step, dict)
    }
    if not route_elements:
        return False
    starts_raw = confirmed.request.get("window_from")
    if not starts_raw:
        return False
    job_start = _utc(datetime.fromisoformat(str(starts_raw).replace("Z", "+00:00")))
    ends_raw = confirmed.request.get("window_to")
    if ends_raw:
        job_end = _utc(datetime.fromisoformat(str(ends_raw).replace("Z", "+00:00")))
    else:
        volume = float(confirmed.request.get("volume_m3", 0))
        rate = float(confirmed.request.get("rate_m3h", 1))
        job_end = job_start + timedelta(hours=volume / rate)
    starts_at = _utc(starts_at)
    ends_at = _utc(ends_at) if ends_at is not None else None
    return starts_at < job_end and (ends_at is None or ends_at > job_start)


def _mark_outdated(
    session: Session,
    terminal_id: UUID,
    element_id: str,
    starts_at: datetime,
    ends_at: datetime | None,
    reason: str,
) -> None:
    records = session.scalars(
        select(ConfirmedRoute).where(ConfirmedRoute.terminal_id == terminal_id)
    )
    for record in records:
        route_elements = {
            step.get("element_id")
            for step in record.route.get("steps", [])
            if isinstance(step, dict)
        }
        if element_id in route_elements and _overlaps_route(record, starts_at, ends_at):
            record.outdated = True
            record.outdated_reason = reason


def _serialize(window: AvailabilityWindow) -> dict[str, Any]:
    result = {
        "id": str(window.id),
        "element_id": window.element_id,
        "status": window.status,
        "from": window.starts_at.isoformat(),
        "reason": window.reason,
        "source": window.source,
    }
    if window.ends_at is not None:
        result["to"] = window.ends_at.isoformat()
    if window.external_ref is not None:
        result["external_ref"] = window.external_ref
    return result


@router.get("")
def list_availability(
    terminal_id: UUID,
    from_: datetime | None = Query(default=None, alias="from"),
    to_: datetime | None = Query(default=None, alias="to"),
    element_id: str | None = Query(default=None),
    session: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    if TerminalRepository(session).get_terminal(terminal_id) is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Terminal not found"})
    query = select(AvailabilityWindow).where(AvailabilityWindow.terminal_id == terminal_id)
    if element_id:
        query = query.where(AvailabilityWindow.element_id == element_id)
    if from_:
        query = query.where(AvailabilityWindow.ends_at.is_(None) | (AvailabilityWindow.ends_at >= from_))
    if to_:
        query = query.where(AvailabilityWindow.starts_at <= to_)
    return [_serialize(window) for window in session.scalars(query.order_by(AvailabilityWindow.starts_at))]


@router.post("")
def upsert_availability(
    terminal_id: UUID,
    body: AvailabilityBatch,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    repository = TerminalRepository(session)
    terminal = repository.get_terminal(terminal_id)
    document = repository.load_document(terminal_id)
    if terminal is None or document is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Terminal not found"})

    element_ids = {element["id"] for element in document["elements"]}
    applied = 0
    rejected: list[dict[str, Any]] = []
    for index, item in enumerate(body.windows):
        if item.element_id not in element_ids:
            rejected.append({"index": index, "reason": f"Unknown element {item.element_id}"})
            continue
        if item.ends_at is not None and item.ends_at < item.starts_at:
            rejected.append({"index": index, "reason": "Window end must not precede its start"})
            continue

        existing = session.scalar(
            select(AvailabilityWindow).where(
                AvailabilityWindow.terminal_id == terminal_id,
                AvailabilityWindow.element_id == item.element_id,
                AvailabilityWindow.source == item.source,
                AvailabilityWindow.external_ref.is_(None)
                if item.external_ref is None
                else AvailabilityWindow.external_ref == item.external_ref,
            )
        )
        changed = existing is None or any(
            (
                existing.status != item.status,
                existing.starts_at != item.starts_at,
                existing.ends_at != item.ends_at,
                existing.reason != item.reason,
            )
        )
        if existing is None:
            existing = AvailabilityWindow(
                terminal_id=terminal_id,
                element_id=item.element_id,
                source=item.source,
                external_ref=item.external_ref,
                status=item.status,
                starts_at=item.starts_at,
                ends_at=item.ends_at,
                reason=item.reason,
            )
            session.add(existing)
        else:
            existing.status = item.status
            existing.starts_at = item.starts_at
            existing.ends_at = item.ends_at
            existing.reason = item.reason
        if changed:
            _mark_outdated(
                session,
                terminal_id,
                item.element_id,
                item.starts_at,
                item.ends_at,
                f"Availability for {item.element_id} changed",
            )
        applied += 1

    session.commit()
    return {"applied": applied, "rejected": rejected}


@router.delete("/{window_id}", status_code=204)
def delete_availability(
    terminal_id: UUID,
    window_id: UUID,
    session: Session = Depends(get_db),
) -> Response:
    window = session.scalar(
        select(AvailabilityWindow).where(
            AvailabilityWindow.terminal_id == terminal_id,
            AvailabilityWindow.id == window_id,
        )
    )
    if window is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Availability window not found"})
    _mark_outdated(
        session,
        terminal_id,
        window.element_id,
        window.starts_at,
        window.ends_at,
        f"Availability window for {window.element_id} changed",
    )
    session.delete(window)
    session.commit()
    return Response(status_code=204)
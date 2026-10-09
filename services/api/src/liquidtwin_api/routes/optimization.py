from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from liquidtwin_api.db.models import AvailabilityWindow as AvailabilityWindowRecord
from liquidtwin_api.db.repository import TerminalRepository
from liquidtwin_api.db.session import get_db
from liquidtwin_engine.document import parse_document
from liquidtwin_engine.graph import build_graph
from liquidtwin_engine.optimization import (
    ObjectiveWeights,
    OptimizationJob,
    prepare_optimization,
    solve_optimization,
)
from liquidtwin_engine.routing import ENGINE_VERSION
from liquidtwin_engine.types import AvailabilityWindow, Exclusion
from liquidtwin_engine.validation import validate_document

router = APIRouter(tags=["optimization"])


class PumpSuctionInputBody(BaseModel):
    pump_id: str = Field(min_length=1, max_length=64)
    npsh_available_m: float = Field(ge=0)


class OptimizationJobBody(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    direction: Literal["IN", "OUT", "TRANSFER"]
    product_id: str = Field(min_length=1, max_length=64)
    source_ids: list[str] = Field(min_length=1, max_length=100)
    destination_ids: list[str] = Field(min_length=1, max_length=100)
    volume_m3: float = Field(gt=0)
    rate_m3h: float = Field(gt=0)
    earliest_start_min: int = Field(ge=0)
    due_min: int = Field(ge=0)
    pump_suction_inputs: list[PumpSuctionInputBody] = Field(default_factory=list)

    @model_validator(mode="after")
    def due_after_earliest(self) -> OptimizationJobBody:
        if self.due_min < self.earliest_start_min:
            raise ValueError("due_min must be greater than or equal to earliest_start_min")
        return self


class ObjectiveWeightsBody(BaseModel):
    waiting: int = Field(default=1, ge=0, le=1000)
    lateness: int = Field(default=20, ge=0, le=1000)
    flush_volume: int = Field(default=1, ge=0, le=1000)
    valves: int = Field(default=2, ge=0, le=1000)
    shared_headers: int = Field(default=3, ge=0, le=1000)


class OptimizationScenarioBody(BaseModel):
    terminal_version: int = Field(ge=1)
    horizon_start: datetime
    horizon_minutes: int = Field(default=1000, ge=1, le=10080)
    jobs: list[OptimizationJobBody] = Field(min_length=1, max_length=100)
    objective_weights: ObjectiveWeightsBody = Field(default_factory=ObjectiveWeightsBody)
    time_limit_seconds: float = Field(default=30, gt=0, le=30)
    random_seed: int = Field(default=1, ge=0, le=2147483647)

    @model_validator(mode="after")
    def validate_job_set(self) -> OptimizationScenarioBody:
        if self.horizon_start.tzinfo is None or self.horizon_start.utcoffset() is None:
            raise ValueError("horizon_start must include a timezone")
        ids = [job.id for job in self.jobs]
        if len(ids) != len(set(ids)):
            raise ValueError("job IDs must be unique within a scenario")
        if any(job.due_min > self.horizon_minutes for job in self.jobs):
            raise ValueError("job due_min must be within the planning horizon")
        return self


def _serialize_exclusion(exclusion: Exclusion) -> dict[str, Any]:
    result: dict[str, Any] = {"reason": exclusion.reason.value, "detail": exclusion.detail}
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


def _optimization_jobs(body: OptimizationScenarioBody) -> tuple[OptimizationJob, ...]:
    return tuple(
        OptimizationJob(
            id=job.id,
            direction=job.direction,
            product_id=job.product_id,
            source_ids=tuple(job.source_ids),
            destination_ids=tuple(job.destination_ids),
            volume_m3=job.volume_m3,
            rate_m3h=job.rate_m3h,
            earliest_start_min=job.earliest_start_min,
            due_min=job.due_min,
            pump_suction_inputs=tuple(
                (item.pump_id, item.npsh_available_m) for item in job.pump_suction_inputs
            ),
        )
        for job in body.jobs
    )


def _load_optimization_graph(terminal_id: UUID, body: OptimizationScenarioBody, session: Session):
    repository = TerminalRepository(session)
    terminal = repository.get_terminal(terminal_id)
    document = repository.load_document(terminal_id, body.terminal_version)
    if terminal is None or document is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Terminal or version not found"},
        )
    if any(issue.severity == "ERROR" for issue in validate_document(document)):
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_TERMINAL", "message": "Terminal contains errors that prevent routing"},
        )
    return build_graph(parse_document(document))


@router.post("/terminals/{terminal_id}/optimization/prepare", response_model=None)
def prepare_jobs(
    terminal_id: UUID,
    body: OptimizationScenarioBody,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    graph = _load_optimization_graph(terminal_id, body, session)
    prepared = prepare_optimization(graph, _optimization_jobs(body))
    return {
        "terminal_version": body.terminal_version,
        "horizon_start": body.horizon_start,
        "horizon_minutes": body.horizon_minutes,
        "engine_version": ENGINE_VERSION,
        "jobs": [
            {
                "job_id": item.job.id,
                "routes": [_serialize_route(route) for route in item.routes],
                "blockers": [_serialize_exclusion(blocker) for blocker in item.blockers],
            }
            for item in prepared
        ],
    }


def _optimization_result(result) -> dict[str, Any]:
    return {
        "status": result.status,
        "detail": result.detail,
        "objective": result.objective,
        "best_bound": result.best_bound,
        "scheduled_jobs": [
            {
                "job_id": job.job_id,
                "start_min": job.start_min,
                "end_min": job.end_min,
                "late_min": job.late_min,
                "route": _serialize_route(job.route),
            }
            for job in result.scheduled_jobs
        ],
        "unscheduled_jobs": [
            {
                "job_id": job.job_id,
                "detail": job.detail,
                "blockers": [_serialize_exclusion(blocker) for blocker in job.blockers],
                "conflict_elements": list(job.conflict_elements),
            }
            for job in result.unscheduled_jobs
        ],
        "kpis": result.kpis,
        "element_timeline": [asdict(item) for item in result.element_timeline],
    }


def _relative_minute(value: datetime, origin: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return (value.timestamp() - origin.timestamp()) / 60


@router.post("/terminals/{terminal_id}/optimize", response_model=None)
def optimize_jobs(
    terminal_id: UUID,
    body: OptimizationScenarioBody,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    graph = _load_optimization_graph(terminal_id, body, session)
    prepared = prepare_optimization(graph, _optimization_jobs(body))
    records = session.scalars(
        select(AvailabilityWindowRecord).where(AvailabilityWindowRecord.terminal_id == terminal_id)
    )
    availability = tuple(
        AvailabilityWindow(
            element_id=record.element_id,
            status=record.status,
            start_min=_relative_minute(record.starts_at, body.horizon_start),
            end_min=_relative_minute(record.ends_at, body.horizon_start) if record.ends_at else None,
            reason=record.reason or "",
        )
        for record in records
    )
    result = solve_optimization(
        graph,
        prepared,
        horizon_minutes=body.horizon_minutes,
        availability=availability,
        weights=ObjectiveWeights(**body.objective_weights.model_dump()),
        time_limit_seconds=body.time_limit_seconds,
        random_seed=body.random_seed,
    )
    return {
        "terminal_version": body.terminal_version,
        "engine_version": ENGINE_VERSION,
        "solver_version": "OR-Tools CP-SAT",
        **_optimization_result(result),
    }
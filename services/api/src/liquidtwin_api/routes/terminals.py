from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from liquidtwin_api.db.models import Terminal, TerminalVersion
from liquidtwin_api.db.repository import TerminalRepository
from liquidtwin_api.db.session import get_db
from liquidtwin_api.schemas.terminal_document import TerminalDocument

router = APIRouter(prefix="/terminals", tags=["terminals"])


class CreateTerminalRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    document: TerminalDocument


class SaveVersionRequest(BaseModel):
    document: TerminalDocument | None = None
    restore_from: int | None = Field(default=None, ge=1)
    note: str | None = Field(default=None, max_length=500)


def terminal_summary(terminal: Terminal, version: TerminalVersion) -> dict[str, Any]:
    return {
        "id": str(terminal.id),
        "name": terminal.name,
        "current_version": terminal.current_version,
        "updated_at": version.created_at,
    }


@router.get("")
def list_terminals(session: Session = Depends(get_db)) -> list[dict[str, Any]]:
    repository = TerminalRepository(session)
    summaries = []
    for terminal in repository.list_terminals():
        version = session.get(TerminalVersion, (terminal.id, terminal.current_version))
        if version is not None:
            summaries.append(terminal_summary(terminal, version))
    return summaries


@router.post("", status_code=201)
def create_terminal(body: CreateTerminalRequest, session: Session = Depends(get_db)) -> dict[str, Any]:
    document = body.document.model_dump(mode="json", exclude_none=True, by_alias=True)
    document["name"] = body.name
    repository = TerminalRepository(session)
    terminal = repository.create_terminal(body.name, document)
    session.commit()
    version = session.get(TerminalVersion, (terminal.id, terminal.current_version))
    if version is None:
        raise HTTPException(status_code=500, detail="Created terminal version could not be loaded")
    return terminal_summary(terminal, version)


@router.get("/{terminal_id}")
def get_terminal(
    terminal_id: UUID,
    version: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    repository = TerminalRepository(session)
    terminal = repository.get_terminal(terminal_id)
    document = repository.load_document(terminal_id, version)
    if terminal is None or document is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Terminal or version not found"},
        )
    return {
        "id": str(terminal.id),
        "name": terminal.name,
        "version": terminal.current_version if version is None else version,
        "document": document,
    }


@router.delete("/{terminal_id}", status_code=204)
def delete_terminal(terminal_id: UUID, session: Session = Depends(get_db)) -> Response:
    if not TerminalRepository(session).delete_terminal(terminal_id):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Terminal not found"})
    session.commit()
    return Response(status_code=204)


@router.get("/{terminal_id}/versions")
def list_versions(terminal_id: UUID, session: Session = Depends(get_db)) -> list[dict[str, Any]]:
    repository = TerminalRepository(session)
    if repository.get_terminal(terminal_id) is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Terminal not found"})
    return [
        {"version": item.version, "created_at": item.created_at, "note": item.note}
        for item in repository.list_versions(terminal_id)
    ]


@router.post("/{terminal_id}/versions", status_code=201)
def save_version(
    terminal_id: UUID,
    body: SaveVersionRequest,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    if (body.document is None) == (body.restore_from is None):
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_VERSION_REQUEST", "message": "Provide exactly one of document or restore_from"},
        )
    repository = TerminalRepository(session)
    if repository.get_terminal(terminal_id) is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Terminal not found"})
    document = (
        body.document.model_dump(mode="json", exclude_none=True, by_alias=True)
        if body.document is not None
        else repository.load_document(terminal_id, body.restore_from)
    )
    if document is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Restore version not found"},
        )
    record = repository.append_version(terminal_id, document, body.note)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Terminal not found"})
    session.commit()
    return {"version": record.version, "created_at": record.created_at, "note": record.note}
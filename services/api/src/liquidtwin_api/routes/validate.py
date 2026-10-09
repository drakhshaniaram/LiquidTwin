from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from liquidtwin_api.db.repository import TerminalRepository
from liquidtwin_api.db.session import get_db
from liquidtwin_api.schemas.terminal_document import TerminalDocument
from liquidtwin_engine.validation import validate_document

router = APIRouter(prefix="/terminals", tags=["validation"])


class ValidateRequest(BaseModel):
    document: TerminalDocument | None = None


@router.post("/{terminal_id}/validate")
def validate_terminal(
    terminal_id: UUID,
    body: ValidateRequest | None = None,
    session: Session = Depends(get_db),
) -> dict[str, list[dict[str, Any]]]:
    repository = TerminalRepository(session)
    terminal = repository.get_terminal(terminal_id)
    if terminal is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Terminal not found"})

    document = (
        body.document.model_dump(mode="json", exclude_none=True, by_alias=True)
        if body is not None and body.document is not None
        else repository.load_document(terminal_id)
    )
    if document is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Terminal document not found"},
        )
    issues = validate_document(document)
    return {"issues": [asdict(issue) for issue in issues]}
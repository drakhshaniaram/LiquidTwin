from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from liquidtwin_api.db.repository import TerminalRepository
from liquidtwin_api.db.session import get_db
from liquidtwin_engine.document import parse_document
from liquidtwin_engine.graph import build_graph
from liquidtwin_engine.validation import validate_document

router = APIRouter(tags=["terminals"])
GRAPH_BLOCKING_ISSUES = {"SCHEMA", "DUPLICATE_ID", "DANGLING_ELEMENT", "SELF_LOOP"}


@router.get("/terminals/{terminal_id}/graph", response_model=None)
def get_terminal_graph(
    terminal_id: UUID,
    version: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    repository = TerminalRepository(session)
    terminal = repository.get_terminal(terminal_id)
    document = repository.load_document(terminal_id, version)
    if terminal is None or document is None:
        return JSONResponse(
            status_code=404,
            content={"code": "NOT_FOUND", "message": "Terminal or version not found"},
        )

    issues = validate_document(document)
    issue_data = [asdict(issue) for issue in issues]
    blocking_issues = [issue for issue in issues if issue.code in GRAPH_BLOCKING_ISSUES]
    if blocking_issues:
        return JSONResponse(
            status_code=422,
            content={
                "code": "INVALID_TERMINAL_GRAPH",
                "message": "The terminal has errors that prevent an accurate graph projection",
                "issues": [asdict(issue) for issue in blocking_issues],
            },
        )

    graph = build_graph(parse_document(document))
    arcs = []
    for arc in graph.arcs:
        element = graph.terminal.elements[arc.element_id]
        pump_reverse = element.type == "PUMP" and arc.reversed
        arcs.append(
            {
                "id": f"{arc.element_id}:{'reverse' if arc.reversed else 'forward'}",
                "element_id": arc.element_id,
                "from": arc.u,
                "to": arc.v,
                "reversed": arc.reversed,
                "traversable": not pump_reverse,
                "restriction": "ONE_WAY_PUMP" if pump_reverse else None,
            }
        )

    return {
        "terminal_version": terminal.current_version if version is None else version,
        "nodes": document["nodes"],
        "elements": document["elements"],
        "arcs": arcs,
        "issues": issue_data,
    }
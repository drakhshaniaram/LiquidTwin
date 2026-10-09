from __future__ import annotations

import json
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from liquidtwin_api.db.models import AvailabilityWindow, TerminalVersion
from liquidtwin_api.db.repository import TerminalRepository
from liquidtwin_api.db.session import get_db
from liquidtwin_api.routes.terminals import terminal_summary
from liquidtwin_api.schemas.terminal_document import TerminalDocument
from liquidtwin_engine.csv_import import import_csv_bundle
from liquidtwin_engine.export import to_csv_bundle, to_json
from liquidtwin_engine.types import ValidationIssue
from liquidtwin_engine.validation import validate_document

router = APIRouter(prefix="/terminals", tags=["terminals"])
MAX_IMPORT_BYTES = 10 * 1024 * 1024
AVAILABILITY_STATUSES = {"AVAILABLE", "MAINTENANCE", "FLUSHING", "CLEANING", "OUT_OF_SERVICE"}


def _issues_response(issues: list[ValidationIssue], code: str = "VALIDATION_FAILED") -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": code,
            "message": "Import rejected; no terminal was created",
            "issues": [asdict(issue) for issue in issues],
        },
    )


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _availability_rows(
    rows: list[dict[str, Any]], document: dict[str, Any]
) -> tuple[list[AvailabilityWindow], list[ValidationIssue]]:
    element_ids = {element["id"] for element in document["elements"]}
    windows: list[AvailabilityWindow] = []
    issues: list[ValidationIssue] = []
    seen: set[tuple[str, str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        element_id = str(row.get("element_id") or "")
        status = str(row.get("status") or "").upper()
        source = str(row.get("source") or "manual")
        external_ref = str(row.get("external_ref") or "")
        if element_id not in element_ids:
            issues.append(ValidationIssue(
                "WARNING", "UNKNOWN_AVAILABILITY_ELEMENT",
                f"Availability row references unknown element {element_id}; row ignored",
                "Check the element_id against elements.csv", element_id=element_id or None,
                row=row_number, file="availability.csv"))
            continue
        if status not in AVAILABILITY_STATUSES:
            issues.append(ValidationIssue(
                "ERROR", "BAD_AVAILABILITY_STATUS", f"Unknown availability status '{status}'",
                "Use an allowed availability status", element_id=element_id,
                row=row_number, file="availability.csv"))
            continue
        try:
            starts_at = _parse_time(str(row.get("from") or ""))
            ends_at = _parse_time(str(row["to"])) if row.get("to") else None
        except ValueError:
            issues.append(ValidationIssue(
                "ERROR", "BAD_AVAILABILITY_TIME", "Availability from/to must be ISO-8601 timestamps",
                "Provide valid ISO-8601 timestamps", element_id=element_id,
                row=row_number, file="availability.csv"))
            continue
        if ends_at is not None and ends_at < starts_at:
            issues.append(ValidationIssue(
                "ERROR", "BAD_AVAILABILITY_TIME", "Availability end must not precede its start",
                "Set to to a time after from", element_id=element_id,
                row=row_number, file="availability.csv"))
            continue
        key = (element_id, source, external_ref)
        if key in seen:
            issues.append(ValidationIssue(
                "ERROR", "DUPLICATE_AVAILABILITY", "Duplicate availability source reference",
                "Keep each element/source/external_ref combination unique", element_id=element_id,
                row=row_number, file="availability.csv"))
            continue
        seen.add(key)
        windows.append(AvailabilityWindow(
            element_id=element_id, status=status, starts_at=starts_at, ends_at=ends_at,
            reason=row.get("reason"), source=source, external_ref=external_ref or None))
    return windows, issues


async def _read_csv_files(request: Request) -> tuple[str, dict[str, str], list[ValidationIssue]]:
    try:
        form = await request.form()
    except (AssertionError, RuntimeError) as error:
        raise HTTPException(status_code=415, detail="Multipart CSV import is unavailable") from error

    name = str(form.get("name") or "").strip()
    if not name:
        return name, {}, [ValidationIssue("ERROR", "MISSING_NAME", "Terminal name is required")]

    files: dict[str, str] = {}
    issues: list[ValidationIssue] = []
    for value in form.getlist("files"):
        if not isinstance(value, UploadFile) or not value.filename:
            issues.append(ValidationIssue("ERROR", "BAD_FILE", "Each files entry must be a named CSV file"))
            continue
        filename = PurePosixPath(value.filename.replace("\\", "/")).name
        if filename in files:
            issues.append(ValidationIssue("ERROR", "DUPLICATE_FILE", f"Duplicate file {filename}", file=filename))
            continue
        if not filename.lower().endswith(".csv"):
            issues.append(ValidationIssue("ERROR", "BAD_FILE_TYPE", "Only CSV files are accepted", file=filename))
            continue
        content = await value.read(MAX_IMPORT_BYTES + 1)
        if len(content) > MAX_IMPORT_BYTES:
            issues.append(ValidationIssue("ERROR", "FILE_TOO_LARGE", "CSV file exceeds the 10 MiB limit", file=filename))
            continue
        try:
            files[filename] = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            issues.append(ValidationIssue("ERROR", "BAD_ENCODING", "CSV files must use UTF-8 encoding", file=filename))
    return name, files, issues


@router.post("/import", status_code=201, response_model=None)
async def import_terminal(request: Request, session: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    content_type = request.headers.get("content-type", "").lower()
    availability_rows: list[dict[str, Any]] = []
    name: str

    if content_type.startswith("application/json"):
        raw = await request.body()
        if len(raw) > MAX_IMPORT_BYTES:
            return _issues_response([ValidationIssue("ERROR", "BODY_TOO_LARGE", "JSON import exceeds the 10 MiB limit")])
        try:
            body = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _issues_response([ValidationIssue("ERROR", "BAD_JSON", "Request body must be valid JSON")])
        if not isinstance(body, dict) or not isinstance(body.get("document"), dict):
            return _issues_response([ValidationIssue("ERROR", "BAD_IMPORT", "Provide a name and terminal document")])
        name = str(body.get("name") or "").strip()
        source_document = dict(body["document"])
        source_document["name"] = name
        issues = validate_document(source_document)
        availability_rows = []
    elif content_type.startswith("multipart/form-data"):
        name, files, read_issues = await _read_csv_files(request)
        if read_issues:
            return _issues_response(read_issues)
        result = import_csv_bundle(files, name)
        issues = result.issues
        if result.document is None:
            return _issues_response(issues)
        source_document = result.document
        availability_rows = result.availability
    else:
        raise HTTPException(status_code=415, detail="Use application/json or multipart/form-data")

    if not name or len(name) > 120:
        issues.append(ValidationIssue("ERROR", "BAD_NAME", "Terminal name must contain 1 to 120 characters"))
    if any(issue.severity == "ERROR" for issue in issues):
        return _issues_response(issues)

    try:
        normalized = TerminalDocument.model_validate(source_document).model_dump(
            mode="json", by_alias=True, exclude_none=True
        )
    except Exception:
        return _issues_response(validate_document(source_document))
    normalized["name"] = name
    windows, availability_issues = _availability_rows(availability_rows, normalized)
    issues.extend(availability_issues)
    if any(issue.severity == "ERROR" for issue in issues):
        return _issues_response(issues)

    repository = TerminalRepository(session)
    terminal = repository.create_terminal(name, normalized, note="Imported terminal")
    for window in windows:
        window.terminal_id = terminal.id
        session.add(window)
    session.commit()
    version = session.get(TerminalVersion, (terminal.id, terminal.current_version))
    if version is None:
        raise HTTPException(status_code=500, detail="Imported terminal version could not be loaded")
    return {**terminal_summary(terminal, version), "issues": [asdict(issue) for issue in issues]}


@router.get("/{terminal_id}/export")
def export_terminal(
    terminal_id: UUID,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    session: Session = Depends(get_db),
) -> Response:
    document = TerminalRepository(session).load_document(terminal_id)
    if document is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Terminal not found"})
    if format == "json":
        return Response(to_json(document), media_type="application/json")

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, contents in to_csv_bundle(document).items():
            archive.writestr(filename, contents)
    return Response(
        buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="terminal-{terminal_id}.zip"'},
    )
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from liquidtwin_api.routes.terminals import router as terminals_router
from liquidtwin_api.routes.graph import router as graph_router
from liquidtwin_api.routes.validate import router as validation_router


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "path"):
            payload["path"] = record.path
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


logger = logging.getLogger("liquidtwin_api")
if not logger.handlers:
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(JsonLogFormatter())
    logger.addHandler(log_handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
logger.propagate = False


def current_actor() -> str:
    return "anonymous"


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(terminals_router)
api_router.include_router(graph_router)
api_router.include_router(validation_router)
app = FastAPI(title="LiquidTwin API", version="0.1.0")
app.include_router(api_router)


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code", "HTTP_ERROR"))
        message = str(detail.get("message", "Request failed"))
    else:
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        message = str(detail)
    return JSONResponse(status_code=exc.status_code, content={"code": code, "message": message})


@app.exception_handler(RequestValidationError)
async def handle_validation_exception(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"code": "VALIDATION_ERROR", "message": "Request validation failed"},
    )


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled API exception",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={"path": request.url.path},
    )
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
    )
"""Structured logging with structlog. Every request is tagged with a trace_id that is
bound into the log context and returned in the `X-Trace-Id` response header."""

import logging
import time
import uuid
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def configure_logging() -> None:
    logging.basicConfig(level=settings.LOG_LEVEL, format="%(message)s")
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.is_production
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.LOG_LEVEL)
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app"):
    return structlog.get_logger(name)


def current_trace_id() -> str:
    return trace_id_var.get()


class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex
        trace_id_var.set(trace_id)
        structlog.contextvars.bind_contextvars(trace_id=trace_id, path=request.url.path)

        log = get_logger("request")
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        response.headers["X-Trace-Id"] = trace_id
        log.info("request_completed", status_code=response.status_code, duration_ms=duration_ms)
        return response

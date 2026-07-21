from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.documents_router import router as documents_router
from app.api.eval_router import router as eval_router
from app.api.query_router import router as query_router
from app.api.ws_router import router as ws_router
from app.auth.router import router as auth_router
from app.config import settings
from app.database.connection import engine
from app.database.models import Base
from app.ingestion.router import rebuild_sparse_index
from app.ingestion.router import router as ingestion_router
from app.observability.logging import TraceIDMiddleware, configure_logging, get_logger
from app.rate_limit import limiter

configure_logging()
log = get_logger("startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    # Warm the in-memory BM25 index from anything already persisted.
    try:
        await rebuild_sparse_index()
    except Exception as exc:  # pragma: no cover - DB may be empty/unavailable at boot
        log.warning("sparse_index_warm_failed", error=str(exc))
    log.info("startup_complete", env=settings.APP_ENV)
    yield


app = FastAPI(title="Agentic Knowledge Worker", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(TraceIDMiddleware)

# In development accept any localhost port: Next.js falls back to 3001+ when 3000 is in
# use, and a hard-coded origin turns every browser call into an opaque "Failed to fetch".
_cors_kwargs: dict = (
    {"allow_origins": settings.cors_origins_list}
    if settings.is_production
    else {"allow_origin_regex": r"http://(localhost|127\.0\.0\.1):\d+"}
)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id"],
    **_cors_kwargs,
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", path=request.url.path, error=str(exc))
    detail = "Internal server error" if settings.is_production else f"{type(exc).__name__}: {exc}"
    return JSONResponse(status_code=500, content={"detail": detail})


app.include_router(auth_router)
app.include_router(ingestion_router)
app.include_router(query_router)
app.include_router(documents_router)
app.include_router(eval_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.APP_ENV}

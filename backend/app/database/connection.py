import asyncio
from contextlib import asynccontextmanager
from typing import Awaitable, Callable, TypeVar
from urllib.parse import parse_qs, urlparse, urlunparse

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

T = TypeVar("T")

# Query params psycopg/libpq understand but asyncpg does not — strip them and translate
# to asyncpg's own SSL handling instead.
_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding", "gssencmode"}


def normalize_db_url(raw_url: str) -> tuple[str, dict]:
    """Make any Postgres URL work with the async (asyncpg) driver.

    Handles the common shapes cloud providers hand out (e.g. Neon):
      - forces the ``postgresql+asyncpg`` driver,
      - drops libpq-only query params asyncpg would reject (``sslmode`` etc.),
      - enables TLS via asyncpg ``connect_args`` for any non-local host, or when the
        original URL explicitly asked for SSL.

    Local ``localhost`` URLs pass through unchanged with no SSL — identical to before.
    """
    parsed = urlparse(raw_url)

    scheme = parsed.scheme
    if scheme in ("postgresql", "postgres"):
        scheme = "postgresql+asyncpg"

    params = parse_qs(parsed.query)
    wants_ssl = params.get("sslmode", [""])[0] in {"require", "verify-ca", "verify-full"}
    kept = [(k, v) for k, v in params.items() if k not in _LIBPQ_ONLY_PARAMS]
    query = "&".join(f"{k}={v[0]}" for k, v in kept)

    host = parsed.hostname or ""
    is_local = host in {"localhost", "127.0.0.1", "", "db"}  # "db" = docker-compose service

    clean_url = urlunparse(parsed._replace(scheme=scheme, query=query))
    connect_args = {"ssl": True} if (wants_ssl or not is_local) else {}
    return clean_url, connect_args


_url, _connect_args = normalize_db_url(settings.DATABASE_URL)
engine = create_async_engine(
    _url,
    echo=False,
    future=True,
    pool_pre_ping=True,   # validate a connection on checkout (catches idle-dropped ones)
    pool_recycle=240,     # recycle before a serverless DB (Neon) suspends after ~5 min idle
    connect_args=_connect_args,
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def with_db_retry(op: Callable[[], Awaitable[T]], attempts: int = 3) -> T:
    """Retry a DB operation when a serverless DB drops the connection mid-flight.

    Neon scales to zero and can terminate a connection during an operation (cold start,
    idle suspend). SQLAlchemy flags these as `connection_invalidated`; a fresh attempt on
    a new (pre-pinged) connection then succeeds. Non-disconnect errors are re-raised at once.
    """
    for attempt in range(attempts):
        try:
            return await op()
        except DBAPIError as exc:
            if not getattr(exc, "connection_invalidated", False) or attempt == attempts - 1:
                raise
            await asyncio.sleep(0.5 * (attempt + 1))
    raise RuntimeError("unreachable")  # pragma: no cover


@asynccontextmanager
async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


async def get_session_dep() -> AsyncSession:
    async with async_session_factory() as session:
        yield session

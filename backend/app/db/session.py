from __future__ import annotations

from typing import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# asyncpg does not accept sslmode/channel_binding URL params (unlike psycopg2).
# Strip them and use connect_args ssl=True instead (e.g. for Neon).
_database_url = settings.database_url
_connect_args = {}
if "sslmode=" in _database_url or "ssl=" in _database_url:
    parsed = urlparse(_database_url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs.pop("sslmode", None)
    qs.pop("channel_binding", None)
    new_query = urlencode(
        {k: v[0] if isinstance(v, list) else v for k, v in qs.items()},
        doseq=False,
    )
    _database_url = urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )
    _connect_args = {"ssl": True}

engine = create_async_engine(
    _database_url,
    connect_args=_connect_args,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session



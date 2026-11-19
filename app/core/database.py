"""Motor SQLAlchemy 2 async (SQLite sandbox o PostgreSQL)."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

_engine_kwargs: dict = {"echo": settings.debug}
if _is_sqlite:
    _engine_kwargs.update(
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    _engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

engine = create_async_engine(settings.database_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Sesión por request. El commit lo hacen los servicios, no esta dependencia."""
    async with AsyncSessionLocal() as session:
        yield session


async def create_schema() -> None:
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

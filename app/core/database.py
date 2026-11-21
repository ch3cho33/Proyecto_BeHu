"""Motor SQLAlchemy 2 async (SQLite sandbox o PostgreSQL)."""

import ssl
from collections.abc import AsyncGenerator
from urllib.parse import urlsplit

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.config import settings

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_is_sqlite = settings.database_url.startswith("sqlite")


def _asyncpg_needs_ssl(url: str) -> bool:
    if not url.startswith("postgresql+asyncpg://"):
        return False
    host = (urlsplit(url).hostname or "").lower()
    return host not in _LOCAL_HOSTS


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
    if _asyncpg_needs_ssl(settings.database_url):
        _engine_kwargs["connect_args"] = {"ssl": ssl.create_default_context()}

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


def _add_v2_columns(connection) -> None:
    """Suma columnas v2 en Neon o SQLite ya creados. create_all no altera tablas viejas."""
    from sqlalchemy import inspect, text

    inspector = inspect(connection)
    dialect = connection.dialect.name
    flag = "BOOLEAN NOT NULL DEFAULT false" if dialect != "sqlite" else "BOOLEAN NOT NULL DEFAULT 0"
    plan = {
        "usuario": [
            ("moneda_preferida", "VARCHAR(3) NOT NULL DEFAULT 'COP'"),
            ("llave_behu", "VARCHAR(80)"),
            ("ingreso_mensual_estimado", "NUMERIC(14,2)"),
        ],
        "cuenta": [("tarjeta_bloqueada", flag)],
        "transaccion": [
            ("metodo_pago", "VARCHAR(32)"),
            ("notas", "VARCHAR(280)"),
            ("recurrencia", "VARCHAR(20)"),
            ("bucket", "VARCHAR(20)"),
            ("is_impulsive", flag),
        ],
        "ledger_contable": [("sello_hmac", "VARCHAR(64)")],
    }
    for table, columns in plan.items():
        if not inspector.has_table(table):
            continue
        present = {column["name"] for column in inspector.get_columns(table)}
        for name, ddl in columns:
            if name in present:
                continue
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
    if dialect != "postgresql" or not inspector.has_table("transaccion"):
        return
    for columna, ancho in (("categoria", 80), ("metodo_pago", 40)):
        try:
            connection.execute(
                text(
                    f"ALTER TABLE transaccion ALTER COLUMN {columna} TYPE VARCHAR({ancho}) "
                    f"USING {columna}::text"
                )
            )
        except Exception:
            continue


async def create_schema() -> None:
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_v2_columns)

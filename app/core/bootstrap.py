"""Inicialización idempotente por instancia. Cubre el caso en que Vercel no corre el lifespan."""

import asyncio
import logging

from app.core.config import settings
from app.core.database import create_schema

logger = logging.getLogger("behu")

_ready = False
_lock = asyncio.Lock()


async def ensure_ready() -> None:
    """create_all y, si aplica, seed. Una vez por proceso; un fallo no marca la instancia como lista."""
    global _ready
    if _ready:
        return
    async with _lock:
        if _ready:
            return
        if settings.auto_seed_sandbox and settings.database_url.startswith("sqlite"):
            logger.warning(
                "AUTO_SEED_SANDBOX sobre SQLite. En Vercel el disco es efímero; "
                "usa DATABASE_URL de Neon o Supabase (postgresql+asyncpg)."
            )
        if settings.auto_seed_sandbox:
            from scripts.seed_sandbox import seed

            await seed()
        elif settings.auto_create_tables:
            await create_schema()
        _ready = True

"""Punto de entrada FastAPI — API stateless para móvil / PWA.

Vercel Services reenvía la ruta original. /api/v1/auth/login llega tal cual;
no se recorta /api ni se define root_path.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.exception_handlers import register_exception_handlers
from app.api.v1.router import api_v1_router
from app.core.bootstrap import ensure_ready
from app.core.config import settings
from app.core.mongodb import close_mongo_client
from app.models import Base  # noqa: F401  — registra mappers SQLAlchemy

logger = logging.getLogger("behu")

_API_PREFIXES = ("/api", "/docs", "/redoc", "/openapi.json")
_LIVENESS_PATHS = frozenset({"/health", "/api/health", "/api/v1/health", "/api/v1/health/db"})


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        await ensure_ready()
    except Exception:
        logger.exception("La base no quedó lista en el lifespan; /health sigue respondiendo")
    yield
    await close_mongo_client()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="BeHu Fintech Core — API REST stateless para iOS, Android y PWA.",
    lifespan=lifespan,
)

register_exception_handlers(app)
app.include_router(api_v1_router)


@app.middleware("http")
async def bootstrap_database(request, call_next):
    """Si el lifespan no corrió, deja Neon listo antes de /api/v1/auth/login."""
    path = request.url.path
    if path not in _LIVENESS_PATHS and path.startswith(_API_PREFIXES):
        try:
            await ensure_ready()
        except Exception as exc:
            logger.exception("No se pudo inicializar la base")
            return JSONResponse(
                status_code=500,
                content={"detail": f"No se pudo inicializar la base: {exc.__class__.__name__}: {exc}"},
            )
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=600,
)


@app.get("/health", tags=["ops"])
@app.get("/api/health", tags=["ops"])
async def healthcheck() -> dict[str, str]:
    """Liveness sin base de datos. Sirve para separar un fallo de import de un fallo de Neon."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/api/v1/health/db", tags=["ops"])
async def health_database():
    """Intenta SELECT 1 contra Neon y devuelve el error exacto si la conexión falla."""
    from sqlalchemy import text

    from app.core.database import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": f"{exc.__class__.__name__}: {exc}"},
        )
    return {"status": "ok", "database": "connected"}

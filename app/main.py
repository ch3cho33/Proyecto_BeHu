"""Punto de entrada FastAPI — API stateless para móvil / PWA."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import create_schema
from app.core.mongodb import close_mongo_client
from app.models import Base  # noqa: F401  — registra mappers SQLAlchemy


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.auto_seed_sandbox:
        from scripts.seed_sandbox import seed

        await seed()
    elif settings.auto_create_tables and not settings.is_production:
        await create_schema()
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=600,
)


@app.get("/health", tags=["ops"])
async def healthcheck() -> dict[str, str]:
    """Liveness liviano para Railway y clientes móviles."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }

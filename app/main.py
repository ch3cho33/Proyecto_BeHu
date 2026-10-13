"""Punto de entrada FastAPI — API stateless para móvil / PWA."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.mongodb import close_mongo_client
from app.models import Base  # noqa: F401  — registra mappers SQLAlchemy


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_mongo_client()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="BeHu Fintech Core — API REST stateless para iOS, Android y PWA.",
    lifespan=lifespan,
)

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

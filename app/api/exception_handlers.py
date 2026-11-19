"""Mapea errores de dominio a JSON HTTP para el cliente móvil."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.exceptions import DomainError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

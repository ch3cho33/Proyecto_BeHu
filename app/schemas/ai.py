"""Contrato JSON de BeHu Mini."""

from pydantic import BaseModel, Field


class AiConsultRequest(BaseModel):
    pregunta: str | None = Field(default=None, max_length=280)


class AiConsultResponse(BaseModel):
    id: str
    rol: str
    enfoque: str
    resumen: str
    recomendaciones: list[str]
    fuente: str
    created_at: str


class ParentalAlert(BaseModel):
    junior_id: str
    junior_nombre: str
    tipo: str
    mensaje: str
    sugerencia: str


class AiHistoryItem(BaseModel):
    id: str
    rol: str
    enfoque: str
    recomendaciones: list[str]
    created_at: str

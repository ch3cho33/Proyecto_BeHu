"""Contrato JSON de BeHu Mini."""

from pydantic import BaseModel, Field


class AiConsultRequest(BaseModel):
    pregunta: str | None = Field(default=None, max_length=280)
    message: str | None = Field(default=None, max_length=280)
    question: str | None = Field(default=None, max_length=280)

    def texto(self) -> str | None:
        return self.pregunta or self.message or self.question


class AiConsultResponse(BaseModel):
    id: str
    rol: str
    enfoque: str
    resumen: str
    recomendaciones: list[str]
    fuente: str
    created_at: str
    reply: str
    response: str
    insights: list[str]
    suggested_actions: list[str]


class ParentalAlert(BaseModel):
    junior_id: str
    junior_nombre: str
    tipo: str
    mensaje: str
    sugerencia: str
    severity: str = "medium"
    badge: str | None = None


class AiHistoryItem(BaseModel):
    id: str
    rol: str
    enfoque: str
    recomendaciones: list[str]
    created_at: str

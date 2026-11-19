"""Contrato JSON del Score BeHu."""

from pydantic import BaseModel, Field


class ScoreFactor(BaseModel):
    codigo: str
    etiqueta: str
    puntos: int


class ScoreResponse(BaseModel):
    puntaje: int = Field(ge=0, le=100)
    nivel: str
    color: str
    factores_positivos: list[ScoreFactor]
    factores_negativos: list[ScoreFactor]
    consejos: list[str]

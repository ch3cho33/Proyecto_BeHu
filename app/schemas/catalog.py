"""Categorías y notificaciones in-app."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CategoryPublic(BaseModel):
    codigo: str
    nombre: str
    origen: str


class CategoryCreateRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)


class NotificationPublic(BaseModel):
    id: UUID
    tipo: str
    severity: str
    titulo: str
    detalle: str
    sugerencia: str
    leida: bool
    created_at: datetime

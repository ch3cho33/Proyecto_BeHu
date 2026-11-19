"""Contrato JSON de metas de ahorro."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class GoalCreateRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    monto_objetivo: Decimal = Field(gt=0)
    fecha_limite: date


class GoalDepositRequest(BaseModel):
    monto: Decimal = Field(gt=0)
    descripcion: str | None = Field(default=None, max_length=280)


class GoalPublic(BaseModel):
    id: UUID
    cuenta_id: UUID
    nombre: str
    monto_objetivo: Decimal
    monto_actual: Decimal
    fecha_limite: date
    estado: str
    porcentaje: Decimal
    created_at: datetime

"""Schemas de vínculo parental y presupuesto."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SupervisionCreateRequest(BaseModel):
    cuenta_junior_id: UUID
    presupuesto_periodico: Decimal = Field(ge=0)
    periodicidad: str = Field(pattern="^(SEMANAL|MENSUAL)$")


class SupervisionUnlinkRequest(BaseModel):
    """Desvinculación exige confirmación explícita del cliente (RF-05)."""

    confirmacion: bool = Field(
        description="Debe ser true para ejecutar el desvínculo",
    )


class SupervisionJuniorItem(BaseModel):
    """Junior vinculado, pensado para listados en la app del acudiente."""

    supervision_id: UUID
    cuenta_junior_id: UUID
    email: str
    nombres: str
    apellidos: str
    saldo: Decimal
    moneda: str = "COP"
    presupuesto_periodico: Decimal
    periodicidad: str
    estado: str


class SupervisionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cuenta_senior_id: UUID
    cuenta_junior_id: UUID
    presupuesto_periodico: Decimal
    periodicidad: str
    estado: str
    alerta_desvinculo: bool
    confirmado_desvinculo_en: datetime | None = None
    created_at: datetime

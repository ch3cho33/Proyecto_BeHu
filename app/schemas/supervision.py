"""Schemas de vínculo parental y presupuesto."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import SandboxEmail


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
    limite_gasto_diario: Decimal | None = None
    limite_gasto_semanal: Decimal | None = None
    limite_gasto_mensual: Decimal | None = None
    tarjeta_bloqueada: bool = False


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


class InviteRequest(BaseModel):
    email: SandboxEmail
    initial_budget: Decimal = Field(ge=0)
    daily_limit: Decimal = Field(ge=0)
    weekly_limit: Decimal = Field(ge=0)
    monthly_limit: Decimal = Field(ge=0)


class CreateJuniorRequest(InviteRequest):
    nombres: str = Field(min_length=1, max_length=120)
    apellidos: str = Field(default="Junior", min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=72)


class InvitationPublic(BaseModel):
    id: UUID
    senior_id: UUID
    junior_id: UUID
    senior_nombre: str
    junior_nombre: str = ""
    junior_email: str = ""
    initial_budget: Decimal
    daily_limit: Decimal
    weekly_limit: Decimal
    monthly_limit: Decimal
    estado: str


class InvitationRespondRequest(BaseModel):
    accept: bool


class ActivityItem(BaseModel):
    id: UUID
    categoria: str | None = None
    metodo_pago: str | None = None
    fecha: datetime
    monto: Decimal
    descripcion: str | None = None
    is_impulsive: bool = False
    es_hormiga: bool = False


class CardStatusRequest(BaseModel):
    bloqueada: bool


class CardStatusResponse(BaseModel):
    cuenta_junior_id: UUID
    tarjeta_bloqueada: bool


class LimitsRequest(BaseModel):
    daily_limit: Decimal = Field(ge=0)
    weekly_limit: Decimal = Field(ge=0)
    monthly_limit: Decimal = Field(ge=0)


class LimitsResponse(BaseModel):
    cuenta_junior_id: UUID
    daily_limit: Decimal
    weekly_limit: Decimal
    monthly_limit: Decimal

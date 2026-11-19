"""Schemas de cuenta, saldo y límites para la app móvil."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.transaction import TransactionPublic


class AccountPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    usuario_id: UUID
    tipo: str
    saldo: Decimal
    moneda: str
    estado: str
    limite_gasto_diario: Decimal | None = None
    limite_gasto_semanal: Decimal | None = None
    limite_gasto_mensual: Decimal | None = None
    created_at: datetime


class AccountBalanceResponse(BaseModel):
    """Consulta de saldo (RF-06). Junior no incluye red global."""

    account_id: UUID
    tipo: str
    saldo: Decimal
    moneda: str = "COP"
    limite_gasto_diario: Decimal | None = None
    limite_gasto_semanal: Decimal | None = None
    limite_gasto_mensual: Decimal | None = None
    tarjeta_bloqueada: bool = False
    saldo_congelado: Decimal = Decimal("0.00")
    saldo_disponible: Decimal = Decimal("0.00")
    puede_ver_transferencias_globales: bool = Field(
        description="False para perfiles JUNIOR",
    )


class AccountMeResponse(BaseModel):
    """Saldo derivado del ledger + historial visible según el rol JWT."""

    account: AccountBalanceResponse
    llave: str = ""
    movimientos: list[TransactionPublic] = Field(default_factory=list)

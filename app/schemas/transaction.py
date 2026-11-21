"""Schemas de movimientos para el cliente móvil."""

import re
import unicodedata
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def codigo_flexible(value: str, *, tope: int) -> str:
    base = unicodedata.normalize("NFKD", value.strip())
    plano = "".join(caracter for caracter in base if not unicodedata.combining(caracter))
    codigo = re.sub(r"[^A-Za-z0-9]+", "_", plano).strip("_").upper()
    if len(codigo) < 2:
        raise ValueError("Valor demasiado corto")
    return codigo[:tope]


class SpendRequest(BaseModel):
    """Compra simulada en un comercio del sandbox."""

    monto: Decimal = Field(gt=0)
    categoria: str = Field(min_length=1, max_length=80)
    comercio: str = Field(min_length=2, max_length=120)

    @field_validator("categoria")
    @classmethod
    def _categoria(cls, value: str) -> str:
        return codigo_flexible(value, tope=80)
    descripcion: str | None = Field(default=None, max_length=280)
    forzar_confirmacion: bool = False


class MovementRequest(BaseModel):
    """Ingreso o gasto del neobanco. El gasto pasa por el nudge anti-impulsos."""

    tipo: str = Field(pattern="^(GASTO|INGRESO)$")
    monto: Decimal = Field(gt=0)
    categoria: str = Field(default="COMIDA", min_length=1, max_length=80)
    metodo_pago: str = Field(default="EFECTIVO", min_length=1, max_length=40)

    @field_validator("categoria")
    @classmethod
    def _categoria(cls, value: str) -> str:
        return codigo_flexible(value, tope=80)

    @field_validator("metodo_pago")
    @classmethod
    def _metodo(cls, value: str) -> str:
        return codigo_flexible(value, tope=40)
    notas: str | None = Field(default=None, max_length=280)
    recurrencia: str = Field(default="UNICA", pattern="^(UNICA|SEMANAL|MENSUAL)$")
    bucket: str = Field(default="DESEOS", pattern="^(NECESIDADES|DESEOS|AHORRO)$")
    forzar_confirmacion: bool = False
    redondear_ahorro: bool = False


class IncomeRequest(BaseModel):
    monto: Decimal = Field(gt=0)
    descripcion: str | None = Field(default=None, max_length=280)
    bucket: str = Field(default="AHORRO", pattern="^(NECESIDADES|DESEOS|AHORRO)$")


class BudgetTransferRequest(BaseModel):
    """Asignación de presupuesto parental (sandbox, no ACH)."""

    cuenta_junior_id: UUID
    monto: Decimal = Field(gt=0)
    descripcion: str | None = Field(default=None, max_length=280)


class KeyTransferRequest(BaseModel):
    llave: str = Field(min_length=3, max_length=80)
    monto: Decimal = Field(gt=0)
    descripcion: str | None = Field(default=None, max_length=280)


class TransferCreateRequest(BaseModel):
    cuenta_destino_id: UUID
    monto: Decimal = Field(gt=0)
    descripcion: str | None = Field(default=None, max_length=280)


class TransactionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tipo: str
    estado: str
    monto: Decimal
    moneda: str
    descripcion: str | None = None
    categoria: str | None = None
    comercio: str | None = None
    es_transferencia_global: bool
    forzada: bool = False
    is_impulsive: bool = False
    metodo_pago: str | None = None
    notas: str | None = None
    recurrencia: str | None = None
    bucket: str | None = None
    created_at: datetime
    redondeo: Decimal = Decimal("0.00")
    meta_redondeo: str | None = None


class LedgerLine(BaseModel):
    naturaleza: str
    cuenta: str
    monto: Decimal
    sello_hmac: str | None = None


class ReceiptPublic(BaseModel):
    transaccion: TransactionPublic
    asientos: list[LedgerLine]

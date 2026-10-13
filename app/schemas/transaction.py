"""Schemas de movimientos para el cliente móvil."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    es_transferencia_global: bool
    created_at: datetime

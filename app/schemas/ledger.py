"""Schemas de asientos. Solo Senior / operaciones internas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LedgerEntryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaccion_id: UUID
    cuenta_id: UUID
    naturaleza: str
    monto: Decimal
    created_at: datetime


class LedgerPairResponse(BaseModel):
    """Par débito/crédito de una transacción (auditoría)."""

    transaccion_id: UUID
    asientos: list[LedgerEntryPublic]

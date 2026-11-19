"""Asientos de ledger inmutables (partida doble)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.account import Cuenta
    from app.models.transaction import Transaccion


class NaturalezaAsiento(StrEnum):
    DEBITO = "DEBITO"
    CREDITO = "CREDITO"


class LedgerContable(Base):
    """Sin updated_at: los asientos no se modifican."""

    __tablename__ = "ledger_contable"
    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_ledger_monto_positivo"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    transaccion_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("transaccion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cuenta_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("cuenta.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    naturaleza: Mapped[str] = mapped_column(String(10), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    transaccion: Mapped[Transaccion] = relationship(
        "Transaccion",
        back_populates="asientos",
    )
    cuenta: Mapped[Cuenta] = relationship("Cuenta")

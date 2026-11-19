"""Meta de ahorro. El dinero abonado sale del saldo gastable vía ledger."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EstadoMeta(StrEnum):
    ACTIVA = "ACTIVA"
    COMPLETADA = "COMPLETADA"
    CANCELADA = "CANCELADA"


class MetaAhorro(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meta_ahorro"
    __table_args__ = (
        CheckConstraint("monto_objetivo > 0", name="ck_meta_objetivo_positivo"),
        CheckConstraint("monto_actual >= 0", name="ck_meta_actual_no_negativo"),
    )

    cuenta_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("cuenta.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    monto_objetivo: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    monto_actual: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    fecha_limite: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EstadoMeta.ACTIVA.value,
        index=True,
    )
    completada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

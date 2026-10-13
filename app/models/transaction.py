"""Cabecera de transacción de negocio."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ledger import LedgerContable
    from app.models.user import Usuario


class TipoTransaccion(StrEnum):
    TRANSFERENCIA_INTERNA = "TRANSFERENCIA_INTERNA"
    ASIGNACION_PRESUPUESTO = "ASIGNACION_PRESUPUESTO"
    REVERSO = "REVERSO"


class EstadoTransaccion(StrEnum):
    PENDIENTE = "PENDIENTE"
    COMPLETADA = "COMPLETADA"
    RECHAZADA = "RECHAZADA"


class Transaccion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transaccion"
    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_transaccion_monto_positivo"),
    )

    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EstadoTransaccion.PENDIENTE.value,
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="COP")
    descripcion: Mapped[str | None] = mapped_column(String(280), nullable=True)
    iniciada_por_usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    es_transferencia_global: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    iniciada_por: Mapped[Usuario] = relationship("Usuario")
    asientos: Mapped[list[LedgerContable]] = relationship(
        "LedgerContable",
        back_populates="transaccion",
    )

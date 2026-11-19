"""Vínculo parental SupervisiónCuenta."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.account import Cuenta
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EstadoSupervision(StrEnum):
    ACTIVA = "ACTIVA"
    PENDIENTE_DESVINCULO = "PENDIENTE_DESVINCULO"
    DESVINCULADA = "DESVINCULADA"


class PeriodicidadPresupuesto(StrEnum):
    SEMANAL = "SEMANAL"
    MENSUAL = "MENSUAL"


class SupervisionCuenta(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supervision_cuenta"
    __table_args__ = (
        UniqueConstraint(
            "cuenta_senior_id",
            "cuenta_junior_id",
            name="uq_supervision_par",
        ),
        CheckConstraint(
            "cuenta_senior_id <> cuenta_junior_id",
            name="ck_supervision_distintas",
        ),
        CheckConstraint(
            "presupuesto_periodico >= 0",
            name="ck_supervision_presupuesto_no_negativo",
        ),
    )

    cuenta_senior_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("cuenta.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cuenta_junior_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("cuenta.id", ondelete="RESTRICT"),
        nullable=False,
    )
    presupuesto_periodico: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    periodicidad: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PeriodicidadPresupuesto.MENSUAL.value,
    )
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EstadoSupervision.ACTIVA.value,
        index=True,
    )
    alerta_desvinculo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    confirmado_desvinculo_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cuenta_senior: Mapped[Cuenta] = relationship(
        "Cuenta",
        foreign_keys=[cuenta_senior_id],
    )
    cuenta_junior: Mapped[Cuenta] = relationship(
        "Cuenta",
        foreign_keys=[cuenta_junior_id],
    )

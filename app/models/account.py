"""Cuentas polimórficas: CuentaSenior / CuentaJunior."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import Usuario


class TipoCuenta(StrEnum):
    SENIOR = "SENIOR"
    JUNIOR = "JUNIOR"


class EstadoCuenta(StrEnum):
    ACTIVA = "ACTIVA"
    BLOQUEADA = "BLOQUEADA"
    CERRADA = "CERRADA"


class Cuenta(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Clase base de cuenta transaccional (herencia de tabla única)."""

    __tablename__ = "cuenta"
    __table_args__ = (
        CheckConstraint("saldo >= 0", name="ck_cuenta_saldo_no_negativo"),
    )
    __mapper_args__ = {
        "polymorphic_on": "tipo",
        "polymorphic_identity": "CUENTA",
    }

    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    saldo: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="COP")
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EstadoCuenta.ACTIVA.value,
    )
    limite_gasto_diario: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )
    limite_gasto_mensual: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    usuario: Mapped[Usuario] = relationship("Usuario", back_populates="cuenta")

    def puede_ver_transferencias_globales(self) -> bool:
        return False

    def aplica_limites_de_gasto(self) -> bool:
        return False


class CuentaSenior(Cuenta):
    __mapper_args__ = {"polymorphic_identity": TipoCuenta.SENIOR.value}

    def puede_ver_transferencias_globales(self) -> bool:
        return True


class CuentaJunior(Cuenta):
    __mapper_args__ = {"polymorphic_identity": TipoCuenta.JUNIOR.value}

    def aplica_limites_de_gasto(self) -> bool:
        return True

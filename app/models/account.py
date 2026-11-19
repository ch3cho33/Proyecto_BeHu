"""Cuentas polimórficas: CuentaSenior / CuentaJunior."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import Usuario


class TipoCuenta(StrEnum):
    SENIOR = "SENIOR"
    JUNIOR = "JUNIOR"
    SANDBOX_FLOAT = "SANDBOX_FLOAT"
    SANDBOX_EQUITY = "SANDBOX_EQUITY"
    SANDBOX_MERCHANT = "SANDBOX_MERCHANT"
    SANDBOX_META = "SANDBOX_META"


class EstadoCuenta(StrEnum):
    ACTIVA = "ACTIVA"
    BLOQUEADA = "BLOQUEADA"
    CERRADA = "CERRADA"


class Cuenta(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Clase base de cuenta transaccional (herencia de tabla única)."""

    __tablename__ = "cuenta"
    __table_args__ = (
        CheckConstraint(
            "saldo >= 0 OR tipo = 'SANDBOX_EQUITY'",
            name="ck_cuenta_saldo_no_negativo",
        ),
    )
    __mapper_args__ = {
        "polymorphic_on": "tipo",
        "polymorphic_identity": "CUENTA",
    }

    usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
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
    limite_gasto_semanal: Mapped[Decimal | None] = mapped_column(
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


class CuentaSandboxFloat(Cuenta):
    """Puente operativo del sandbox. El funding de clientes sale de aquí."""

    __mapper_args__ = {"polymorphic_identity": TipoCuenta.SANDBOX_FLOAT.value}

    def puede_ver_transferencias_globales(self) -> bool:
        return True


class CuentaSandboxEquity(Cuenta):
    """Contrapartida de emisión de capital. Puede quedar en saldo negativo."""

    __mapper_args__ = {"polymorphic_identity": TipoCuenta.SANDBOX_EQUITY.value}

    def puede_ver_transferencias_globales(self) -> bool:
        return True


class CuentaSandboxMerchant(Cuenta):
    """Comercio simulado del sandbox. Recibe los débitos de compra."""

    __mapper_args__ = {"polymorphic_identity": TipoCuenta.SANDBOX_MERCHANT.value}


class CuentaSandboxMeta(Cuenta):
    """Bóveda de metas. El saldo abonado deja de estar disponible para gastar."""

    __mapper_args__ = {"polymorphic_identity": TipoCuenta.SANDBOX_META.value}

"""Invitación familiar. El Junior acepta antes de quedar vinculado."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EstadoInvitacion(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class FamilyInvitation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "family_invitation"

    senior_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    junior_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    initial_budget: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    daily_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    weekly_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EstadoInvitacion.PENDING.value,
        index=True,
    )

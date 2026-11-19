"""Cápsulas de micro-learning y progreso por usuario."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ModuloEducativo(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "modulo_educativo"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    resumen: Mapped[str] = mapped_column(Text, nullable=False)
    pregunta: Mapped[str] = mapped_column(String(280), nullable=False)
    opciones_json: Mapped[str] = mapped_column(Text, nullable=False)
    respuesta_correcta: Mapped[str] = mapped_column(String(8), nullable=False)
    insignia: Mapped[str] = mapped_column(String(80), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ProgresoEducativo(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "progreso_educativo"
    __table_args__ = (
        UniqueConstraint("usuario_id", "modulo_id", name="uq_progreso_usuario_modulo"),
    )

    usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    modulo_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("modulo_educativo.id", ondelete="RESTRICT"),
        nullable=False,
    )
    completado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    insignia: Mapped[str] = mapped_column(String(80), nullable=False)
    respondido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

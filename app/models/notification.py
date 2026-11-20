"""Alertas in-app materializadas por usuario."""

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Notificacion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notificacion"
    __table_args__ = (UniqueConstraint("usuario_id", "clave", name="uq_notificacion_usuario_clave"),)

    usuario_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, index=True)
    clave: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    detalle: Mapped[str] = mapped_column(Text, nullable=False)
    sugerencia: Mapped[str] = mapped_column(Text, nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

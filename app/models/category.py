"""Catálogo de categorías de gasto del sandbox."""

from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CodigoCategoria(StrEnum):
    COMIDA = "COMIDA"
    ENTRETENIMIENTO = "ENTRETENIMIENTO"
    TRANSPORTE = "TRANSPORTE"
    EDUCACION = "EDUCACION"
    ROPA = "ROPA"


CATEGORIAS_CATALOGO: dict[str, str] = {
    "COMIDA": "Comida",
    "TRANSPORTE": "Transporte",
    "EDUCACION": "Educación",
    "ROPA": "Ropa",
    "ENTRETENIMIENTO": "Ocio",
    "SALUD": "Salud",
    "VIVIENDA": "Vivienda",
    "SERVICIOS": "Servicios",
    "SUPERMERCADO": "Supermercado",
    "SUSCRIPCIONES": "Suscripciones",
    "VIAJES": "Viajes",
    "DEPORTES": "Deportes",
    "REGALOS": "Regalos",
    "CUIDADO_PERSONAL": "Cuidado personal",
    "TECNOLOGIA": "Tecnología",
    "IMPUESTOS": "Impuestos",
    "FAMILIA": "Familia",
    "TRABAJO": "Trabajo",
}


class CategoriaPersonal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categoria_personal"
    __table_args__ = (UniqueConstraint("usuario_id", "codigo", name="uq_categoria_usuario_codigo"),)

    usuario_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(32), nullable=False)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)


class CategoriaGasto(Base):
    __tablename__ = "categoria_gasto"

    codigo: Mapped[str] = mapped_column(String(32), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)

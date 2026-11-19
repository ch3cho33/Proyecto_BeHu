"""Catálogo de categorías de gasto del sandbox."""

from enum import StrEnum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CodigoCategoria(StrEnum):
    COMIDA = "COMIDA"
    ENTRETENIMIENTO = "ENTRETENIMIENTO"
    TRANSPORTE = "TRANSPORTE"
    EDUCACION = "EDUCACION"
    ROPA = "ROPA"


CATEGORIAS_CATALOGO: dict[str, str] = {
    CodigoCategoria.COMIDA.value: "Comida",
    CodigoCategoria.ENTRETENIMIENTO.value: "Entretenimiento",
    CodigoCategoria.TRANSPORTE.value: "Transporte",
    CodigoCategoria.EDUCACION.value: "Educación",
    CodigoCategoria.ROPA.value: "Ropa",
}


class CategoriaGasto(Base):
    __tablename__ = "categoria_gasto"

    codigo: Mapped[str] = mapped_column(String(32), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)

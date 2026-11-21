"""Catálogo del sistema y categorías propias de cada cuenta."""

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import CATEGORIAS_CATALOGO, CategoriaPersonal
from app.models.user import Usuario
from app.schemas.catalog import CategoryPublic
from app.services.exceptions import DomainError


class CategoriaDuplicada(DomainError):
    status_code = 409


def _codigo(nombre: str) -> str:
    plano = unicodedata.normalize("NFKD", nombre)
    ascii_nombre = "".join(ch for ch in plano if not unicodedata.combining(ch))
    limpio = re.sub(r"[^A-Za-z0-9]+", "_", ascii_nombre).strip("_").upper()
    return (limpio or "CATEGORIA")[:80]


async def listar(db: AsyncSession, usuario: Usuario) -> list[CategoryPublic]:
    propias = (
        await db.scalars(select(CategoriaPersonal).where(CategoriaPersonal.usuario_id == usuario.id).order_by(CategoriaPersonal.nombre))
    ).all()
    sistema = [CategoryPublic(codigo=codigo, nombre=nombre, origen="sistema") for codigo, nombre in CATEGORIAS_CATALOGO.items()]
    extra = [CategoryPublic(codigo=item.codigo, nombre=item.nombre, origen="personal") for item in propias]
    return sistema + extra


async def crear(db: AsyncSession, usuario: Usuario, nombre: str) -> CategoryPublic:
    codigo = _codigo(nombre)
    if codigo in CATEGORIAS_CATALOGO:
        raise CategoriaDuplicada("Esa categoría ya existe en el catálogo")
    previa = await db.scalar(
        select(CategoriaPersonal).where(CategoriaPersonal.usuario_id == usuario.id, CategoriaPersonal.codigo == codigo)
    )
    if previa is not None:
        raise CategoriaDuplicada("Ya tienes esa categoría")
    fila = CategoriaPersonal(usuario_id=usuario.id, codigo=codigo, nombre=nombre.strip())
    db.add(fila)
    await db.commit()
    await db.refresh(fila)
    return CategoryPublic(codigo=fila.codigo, nombre=fila.nombre, origen="personal")

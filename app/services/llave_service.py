"""Llave BeHu pública: @ana.behu. Sirve para cobrar o enviar dentro del sandbox."""

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Usuario


def _slug(nombre: str) -> str:
    plano = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("ascii")
    limpio = re.sub(r"[^a-z0-9]", "", plano.lower())
    return limpio or "behu"


async def asegurar_llave(db: AsyncSession, usuario: Usuario) -> str:
    if usuario.llave_behu:
        return usuario.llave_behu
    base = _slug(usuario.nombres.split()[0])
    candidata = f"{base}.behu"
    serie = 2
    while await db.scalar(select(Usuario.id).where(Usuario.llave_behu == candidata, Usuario.id != usuario.id)):
        candidata = f"{base}{serie}.behu"
        serie += 1
    usuario.llave_behu = candidata
    await db.commit()
    await db.refresh(usuario)
    return candidata


def normalizar_llave(valor: str) -> str:
    return valor.strip().lower().lstrip("@")

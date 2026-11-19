"""Cuentas internas del sandbox: comercio simulado y bóveda de metas."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.account import (
    Cuenta,
    CuentaSandboxMerchant,
    CuentaSandboxMeta,
    TipoCuenta,
)
from app.models.user import RolUsuario, Usuario

MERCHANT_EMAIL = "merchant@behu.internal"
META_EMAIL = "meta@behu.internal"

_SYSTEM = {
    MERCHANT_EMAIL: (CuentaSandboxMerchant, TipoCuenta.SANDBOX_MERCHANT.value, "Comercio"),
    META_EMAIL: (CuentaSandboxMeta, TipoCuenta.SANDBOX_META.value, "Boveda"),
}


async def obtener_cuenta_sistema(db: AsyncSession, email: str) -> Cuenta:
    cuenta_cls, tipo, nombres = _SYSTEM[email]
    user = await db.scalar(select(Usuario).where(Usuario.email == email))
    if user is None:
        user = Usuario(
            email=email,
            password_hash=hash_password("unused-system-account-xx"),
            nombres=nombres,
            apellidos="Sandbox",
            rol=RolUsuario.SENIOR.value,
            is_active=False,
        )
        db.add(user)
        await db.flush()
        cuenta = cuenta_cls(usuario_id=user.id, tipo=tipo, saldo=Decimal("0.00"))
        db.add(cuenta)
        await db.flush()
        return cuenta

    cuenta = await db.scalar(select(Cuenta).where(Cuenta.usuario_id == user.id))
    if cuenta is None:
        cuenta = cuenta_cls(usuario_id=user.id, tipo=tipo, saldo=Decimal("0.00"))
        db.add(cuenta)
        await db.flush()
    return cuenta

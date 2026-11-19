"""Puebla el sandbox local con Senior, Junior, puente FLOAT y capital EQUITY."""

from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.database import AsyncSessionLocal, create_schema  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.account import (  # noqa: E402
    Cuenta,
    CuentaJunior,
    CuentaSandboxEquity,
    CuentaSandboxFloat,
    CuentaSenior,
    TipoCuenta,
)
from app.models.supervision import PeriodicidadPresupuesto, SupervisionCuenta  # noqa: E402
from app.models.transaction import TipoTransaccion  # noqa: E402
from app.models.user import RolUsuario, Usuario  # noqa: E402
from app.services.ledger_service import transferir  # noqa: E402
from app.services.sandbox_accounts import MERCHANT_EMAIL, META_EMAIL, obtener_cuenta_sistema  # noqa: E402
from app.services.spend_service import asegurar_catalogo  # noqa: E402

SENIOR_EMAIL = "senior@behu.test"
SENIOR_PASSWORD = "BeHuSenior1!"
JUNIOR_EMAIL = "junior@behu.test"
JUNIOR_PASSWORD = "BeHuJunior1!"
FLOAT_EMAIL = "float@behu.internal"
EQUITY_EMAIL = "equity@behu.internal"

SENIOR_FUNDING = Decimal("1000000.00")
EQUITY_CAPITAL = Decimal("10000000.00")
PRESUPUESTO_PERIODICO = Decimal("200000.00")


async def _get_user(db: AsyncSession, email: str) -> Usuario | None:
    return await db.scalar(select(Usuario).where(Usuario.email == email))


async def _ensure_system_user(
    db: AsyncSession,
    *,
    email: str,
    nombres: str,
    cuenta_cls: type,
    tipo: str,
    saldo_inicial: Decimal,
) -> Usuario:
    user = await _get_user(db, email)
    if user is not None:
        return user
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
    db.add(cuenta_cls(usuario_id=user.id, tipo=tipo, saldo=saldo_inicial))
    await db.flush()
    return user


async def seed() -> None:
    await create_schema()
    async with AsyncSessionLocal() as db:
        existing_senior = await _get_user(db, SENIOR_EMAIL)
        if existing_senior is not None:
            print("Sandbox ya poblado. Usuarios:")
            print(f"  SENIOR  {SENIOR_EMAIL} / {SENIOR_PASSWORD}")
            print(f"  JUNIOR  {JUNIOR_EMAIL} / {JUNIOR_PASSWORD}")
            return

        equity_user = await _ensure_system_user(
            db,
            email=EQUITY_EMAIL,
            nombres="Equity",
            cuenta_cls=CuentaSandboxEquity,
            tipo=TipoCuenta.SANDBOX_EQUITY.value,
            saldo_inicial=Decimal("0.00"),
        )
        float_user = await _ensure_system_user(
            db,
            email=FLOAT_EMAIL,
            nombres="Float",
            cuenta_cls=CuentaSandboxFloat,
            tipo=TipoCuenta.SANDBOX_FLOAT.value,
            saldo_inicial=Decimal("0.00"),
        )
        await db.commit()

        equity_cta = await db.scalar(select(Cuenta).where(Cuenta.usuario_id == equity_user.id))
        float_cta = await db.scalar(select(Cuenta).where(Cuenta.usuario_id == float_user.id))
        assert equity_cta is not None and float_cta is not None

        await transferir(
            db,
            origen_id=equity_cta.id,
            destino_id=float_cta.id,
            monto=EQUITY_CAPITAL,
            iniciada_por_usuario_id=equity_user.id,
            tipo=TipoTransaccion.APERTURA_SANDBOX.value,
            descripcion="Capitalización del puente SANDBOX_FLOAT",
            es_transferencia_global=True,
        )

        senior = Usuario(
            email=SENIOR_EMAIL,
            password_hash=hash_password(SENIOR_PASSWORD),
            nombres="Ana",
            apellidos="Acudiente",
            rol=RolUsuario.SENIOR.value,
        )
        junior = Usuario(
            email=JUNIOR_EMAIL,
            password_hash=hash_password(JUNIOR_PASSWORD),
            nombres="Lucas",
            apellidos="Menor",
            rol=RolUsuario.JUNIOR.value,
        )
        db.add_all([senior, junior])
        await db.flush()

        senior_cta = CuentaSenior(usuario_id=senior.id, tipo=TipoCuenta.SENIOR.value)
        junior_cta = CuentaJunior(
            usuario_id=junior.id,
            tipo=TipoCuenta.JUNIOR.value,
            limite_gasto_diario=Decimal("50000.00"),
            limite_gasto_semanal=Decimal("200000.00"),
            limite_gasto_mensual=Decimal("500000.00"),
        )
        db.add_all([senior_cta, junior_cta])
        await db.commit()

        await transferir(
            db,
            origen_id=float_cta.id,
            destino_id=senior_cta.id,
            monto=SENIOR_FUNDING,
            iniciada_por_usuario_id=senior.id,
            tipo=TipoTransaccion.APERTURA_SANDBOX.value,
            descripcion="Funding inicial sandbox Senior 1.000.000 COP",
            es_transferencia_global=True,
        )

        db.add(
            SupervisionCuenta(
                cuenta_senior_id=senior_cta.id,
                cuenta_junior_id=junior_cta.id,
                presupuesto_periodico=PRESUPUESTO_PERIODICO,
                periodicidad=PeriodicidadPresupuesto.MENSUAL.value,
            )
        )
        await db.commit()

        async with AsyncSessionLocal() as extra:
            await asegurar_catalogo(extra)
            await obtener_cuenta_sistema(extra, MERCHANT_EMAIL)
            await obtener_cuenta_sistema(extra, META_EMAIL)
            await extra.commit()

        print("Sandbox poblado.")
        print(f"  SENIOR  {SENIOR_EMAIL} / {SENIOR_PASSWORD}  saldo 1.000.000 COP")
        print(f"  JUNIOR  {JUNIOR_EMAIL} / {JUNIOR_PASSWORD}  saldo 0 COP (vinculado)")
        print(f"  Junior cuenta_id={junior_cta.id}")
        print("  Login en /docs y Authorize con el access_token.")


if __name__ == "__main__":
    asyncio.run(seed())

"""Compra simulada y motor anti-impulsos (HU-07)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import CATEGORIAS_CATALOGO, CategoriaGasto
from app.models.ledger import LedgerContable, NaturalezaAsiento
from app.models.transaction import EstadoTransaccion, TipoTransaccion, Transaccion
from app.models.user import Usuario
from app.schemas.transaction import SpendRequest
from app.services.account_service import get_cuenta_usuario
from app.services.exceptions import CardBlocked, ImpulsiveSpend, InsufficientFunds
from app.services.ledger_service import transferir
from app.services.sandbox_accounts import MERCHANT_EMAIL, obtener_cuenta_sistema

UMBRAL_SALDO = Decimal("0.40")
ZERO = Decimal("0.00")


async def asegurar_catalogo(db: AsyncSession) -> None:
    existentes = set((await db.scalars(select(CategoriaGasto.codigo))).all())
    for codigo, nombre in CATEGORIAS_CATALOGO.items():
        if codigo not in existentes:
            db.add(CategoriaGasto(codigo=codigo, nombre=nombre))
    await db.flush()


async def _gastado_desde(db: AsyncSession, cuenta_id, desde: datetime) -> Decimal:
    total = await db.scalar(
        select(func.coalesce(func.sum(LedgerContable.monto), 0))
        .join(Transaccion, Transaccion.id == LedgerContable.transaccion_id)
        .where(
            LedgerContable.cuenta_id == cuenta_id,
            LedgerContable.naturaleza == NaturalezaAsiento.DEBITO.value,
            Transaccion.tipo == TipoTransaccion.COMPRA.value,
            Transaccion.estado == EstadoTransaccion.COMPLETADA.value,
            Transaccion.created_at >= desde,
        )
    )
    return Decimal(str(total))


def _razones_impulso(
    *,
    cuenta,
    monto: Decimal,
    saldo: Decimal,
    gastado_hoy: Decimal,
    gastado_semana: Decimal,
) -> list[str]:
    razones: list[str] = []
    if cuenta.limite_gasto_diario is not None and gastado_hoy + monto > Decimal(cuenta.limite_gasto_diario):
        razones.append("supera_limite_diario")
    semanal = cuenta.limite_gasto_semanal
    if semanal is None and cuenta.limite_gasto_diario is not None:
        semanal = Decimal(cuenta.limite_gasto_diario) * 7
    if semanal is not None and gastado_semana + monto > Decimal(semanal):
        razones.append("supera_limite_semanal")
    if saldo > ZERO and monto > (saldo * UMBRAL_SALDO):
        razones.append("supera_40_porciento_saldo")
    return razones


async def simular_compra(
    db: AsyncSession,
    usuario: Usuario,
    payload: SpendRequest,
    *,
    commit: bool = True,
) -> Transaccion:
    await asegurar_catalogo(db)
    cuenta = await get_cuenta_usuario(db, usuario)
    if cuenta.tarjeta_bloqueada:
        raise CardBlocked("La tarjeta de este Junior está bloqueada por el acudiente")
    monto = Decimal(payload.monto).quantize(Decimal("0.01"))
    saldo = Decimal(cuenta.saldo)
    if saldo < monto:
        raise InsufficientFunds("Fondos insuficientes para esta compra")

    if cuenta.aplica_limites_de_gasto() and not payload.forzar_confirmacion:
        ahora = datetime.now(timezone.utc)
        inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        inicio_semana = inicio_dia - timedelta(days=inicio_dia.weekday())
        razones = _razones_impulso(
            cuenta=cuenta,
            monto=monto,
            saldo=saldo,
            gastado_hoy=await _gastado_desde(db, cuenta.id, inicio_dia),
            gastado_semana=await _gastado_desde(db, cuenta.id, inicio_semana),
        )
        if razones:
            raise ImpulsiveSpend(
                {
                    "code": "GASTO_IMPULSIVO",
                    "mensaje": (
                        "BeHu Mini pausó esta compra. El monto se ve impulsivo "
                        "frente a tu saldo o a los límites que definió tu acudiente."
                    ),
                    "razones": razones,
                    "categoria": payload.categoria,
                    "monto": f"{monto:.2f}",
                    "saldo_disponible": f"{saldo:.2f}",
                    "accion": "Reenvía con forzar_confirmacion=true para confirmar, o cancela el gasto.",
                }
            )

    comercio_cta = await obtener_cuenta_sistema(db, MERCHANT_EMAIL)
    nombre = CATEGORIAS_CATALOGO[payload.categoria]
    return await transferir(
        db,
        origen_id=cuenta.id,
        destino_id=comercio_cta.id,
        monto=monto,
        iniciada_por_usuario_id=usuario.id,
        tipo=TipoTransaccion.COMPRA.value,
        descripcion=payload.descripcion or f"Compra en {payload.comercio} ({nombre})",
        es_transferencia_global=False,
        categoria=payload.categoria,
        comercio=payload.comercio,
        forzada=payload.forzar_confirmacion,
        commit=commit,
    )

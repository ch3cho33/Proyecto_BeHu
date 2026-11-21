"""Compra simulada y motor anti-impulsos (HU-07)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import CATEGORIAS_CATALOGO, CategoriaGasto
from app.models.ledger import LedgerContable, NaturalezaAsiento
from app.models.transaction import EstadoTransaccion, TipoTransaccion, Transaccion
from app.models.user import Usuario
from app.schemas.transaction import SpendRequest
from app.services.account_service import get_cuenta_usuario
from app.services.exceptions import CardBlocked, ImpulsiveSpend, InsufficientFunds, PatternPause
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


async def _pausar_si_patron(db: AsyncSession, usuario: Usuario, monto: Decimal, *, forzar: bool) -> None:
    desde = datetime.now(timezone.utc) - timedelta(hours=3)
    recientes = (
        await db.scalars(
            select(Transaccion).where(
                Transaccion.iniciada_por_usuario_id == usuario.id,
                Transaccion.tipo == TipoTransaccion.COMPRA.value,
                Transaccion.estado == EstadoTransaccion.COMPLETADA.value,
                Transaccion.created_at >= desde,
            )
        )
    ).all()
    historicas = (
        await db.scalars(
            select(Transaccion)
            .where(
                Transaccion.iniciada_por_usuario_id == usuario.id,
                Transaccion.tipo == TipoTransaccion.COMPRA.value,
                Transaccion.estado == EstadoTransaccion.COMPLETADA.value,
            )
            .order_by(Transaccion.created_at.desc())
            .limit(30)
        )
    ).all()
    mensajes: list[str] = []
    if len(recientes) >= 2:
        mensajes.append("Has realizado varias compras seguidas hoy")
    if historicas:
        promedio = sum((Decimal(tx.monto) for tx in historicas), Decimal("0")) / Decimal(len(historicas))
        if promedio > 0 and monto > promedio * Decimal("1.5"):
            factor = (monto / promedio).quantize(Decimal("0.1"))
            mensajes.append(f"Este gasto es {factor}x mayor a tu promedio habitual")
    if not mensajes:
        return
    from app.models.notification import Notificacion

    db.add(
        Notificacion(
            usuario_id=usuario.id,
            clave=f"patron:{uuid4()}",
            tipo="PATRON_ANOMALO",
            severity="medium",
            titulo="Pausa de estabilidad",
            detalle=" ".join(mensajes),
            sugerencia="Espera unas horas o baja el monto. Un ritmo estable protege el Score mejor que una racha de compras.",
        )
    )
    await db.commit()
    if not forzar:
        raise PatternPause(
            {
                "code": "PATRON_ANOMALO",
                "mensaje": " ".join(mensajes),
                "accion": "Reenvía con forzar_confirmacion=true para continuar, o cancela el gasto.",
            }
        )


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

    if usuario.rol == "JUNIOR":
        await _pausar_si_patron(db, usuario, monto, forzar=payload.forzar_confirmacion)

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
    nombre = CATEGORIAS_CATALOGO.get(payload.categoria, payload.categoria.replace("_", " ").title())
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

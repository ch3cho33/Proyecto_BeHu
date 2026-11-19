"""Metas de ahorro. El abono congela saldo en la bóveda (HU-06)."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import EstadoMeta, MetaAhorro
from app.models.transaction import TipoTransaccion
from app.models.user import Usuario
from app.schemas.goal import GoalCreateRequest, GoalDepositRequest, GoalPublic
from app.services.account_service import get_cuenta_usuario
from app.services.exceptions import (
    ForbiddenAction,
    GoalDepositExceedsTarget,
    GoalNotActive,
    GoalNotFound,
    InsufficientFunds,
)
from app.services.ledger_service import transferir
from app.services.sandbox_accounts import META_EMAIL, obtener_cuenta_sistema


def _public(meta: MetaAhorro) -> GoalPublic:
    objetivo = Decimal(meta.monto_objetivo)
    actual = Decimal(meta.monto_actual)
    porcentaje = (actual / objetivo * Decimal("100")).quantize(Decimal("0.01")) if objetivo else Decimal("0")
    return GoalPublic(
        id=meta.id,
        cuenta_id=meta.cuenta_id,
        nombre=meta.nombre,
        monto_objetivo=objetivo,
        monto_actual=actual,
        fecha_limite=meta.fecha_limite,
        estado=meta.estado,
        porcentaje=porcentaje,
        created_at=meta.created_at,
    )


async def crear_meta(db: AsyncSession, usuario: Usuario, payload: GoalCreateRequest) -> GoalPublic:
    cuenta = await get_cuenta_usuario(db, usuario)
    meta = MetaAhorro(
        cuenta_id=cuenta.id,
        nombre=payload.nombre.strip(),
        monto_objetivo=Decimal(payload.monto_objetivo).quantize(Decimal("0.01")),
        monto_actual=Decimal("0.00"),
        fecha_limite=payload.fecha_limite,
        estado=EstadoMeta.ACTIVA.value,
    )
    db.add(meta)
    await db.commit()
    await db.refresh(meta)
    return _public(meta)


async def listar_metas(db: AsyncSession, usuario: Usuario) -> list[GoalPublic]:
    cuenta = await get_cuenta_usuario(db, usuario)
    result = await db.scalars(
        select(MetaAhorro)
        .where(MetaAhorro.cuenta_id == cuenta.id)
        .order_by(MetaAhorro.created_at.desc())
    )
    return [_public(meta) for meta in result.all()]


async def abonar_meta(
    db: AsyncSession,
    usuario: Usuario,
    meta_id: UUID,
    payload: GoalDepositRequest,
) -> GoalPublic:
    cuenta = await get_cuenta_usuario(db, usuario)
    meta = await db.get(MetaAhorro, meta_id)
    if meta is None:
        raise GoalNotFound("Meta de ahorro no encontrada")
    if meta.cuenta_id != cuenta.id:
        raise ForbiddenAction("Esta meta pertenece a otra cuenta")
    if meta.estado != EstadoMeta.ACTIVA.value:
        raise GoalNotActive("La meta ya no acepta abonos")

    monto = Decimal(payload.monto).quantize(Decimal("0.01"))
    restante = Decimal(meta.monto_objetivo) - Decimal(meta.monto_actual)
    if monto > restante:
        raise GoalDepositExceedsTarget("El abono supera lo que falta para completar la meta")
    if Decimal(cuenta.saldo) < monto:
        raise InsufficientFunds("Saldo disponible insuficiente para abonar a la meta")

    boveda = await obtener_cuenta_sistema(db, META_EMAIL)
    await transferir(
        db,
        origen_id=cuenta.id,
        destino_id=boveda.id,
        monto=monto,
        iniciada_por_usuario_id=usuario.id,
        tipo=TipoTransaccion.ABONO_META.value,
        descripcion=payload.descripcion or f"Abono a meta: {meta.nombre}",
        es_transferencia_global=False,
    )
    meta.monto_actual = Decimal(meta.monto_actual) + monto
    if meta.monto_actual >= Decimal(meta.monto_objetivo):
        meta.estado = EstadoMeta.COMPLETADA.value
        meta.completada_en = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(meta)
    return _public(meta)

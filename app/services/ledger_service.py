"""Partida doble atómica: cabecera + débito origen + crédito destino."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine
from app.models.account import Cuenta, EstadoCuenta, TipoCuenta
from app.models.ledger import LedgerContable, NaturalezaAsiento
from app.models.transaction import EstadoTransaccion, Transaccion
from app.services.exceptions import (
    AccountNotActive,
    AccountNotFound,
    InsufficientFunds,
    InvalidTransfer,
)

ZERO = Decimal("0.00")


async def _lock_account(db: AsyncSession, cuenta_id: UUID) -> Cuenta:
    stmt = select(Cuenta).where(Cuenta.id == cuenta_id)
    if engine.dialect.name != "sqlite":
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    cuenta = result.scalar_one_or_none()
    if cuenta is None:
        raise AccountNotFound("Cuenta no encontrada")
    return cuenta


async def saldo_desde_ledger(db: AsyncSession, cuenta_id: UUID) -> Decimal:
    creditos = await db.scalar(
        select(func.coalesce(func.sum(LedgerContable.monto), 0)).where(
            LedgerContable.cuenta_id == cuenta_id,
            LedgerContable.naturaleza == NaturalezaAsiento.CREDITO.value,
        )
    )
    debitos = await db.scalar(
        select(func.coalesce(func.sum(LedgerContable.monto), 0)).where(
            LedgerContable.cuenta_id == cuenta_id,
            LedgerContable.naturaleza == NaturalezaAsiento.DEBITO.value,
        )
    )
    return Decimal(str(creditos)) - Decimal(str(debitos))


async def transferir(
    db: AsyncSession,
    *,
    origen_id: UUID,
    destino_id: UUID,
    monto: Decimal,
    iniciada_por_usuario_id: UUID,
    tipo: str,
    descripcion: str | None = None,
    es_transferencia_global: bool = False,
) -> Transaccion:
    """Débito origen / crédito destino en una sola transacción SQL."""
    monto = Decimal(monto).quantize(Decimal("0.01"))
    if origen_id == destino_id:
        raise InvalidTransfer("Origen y destino deben ser distintos")
    if monto <= ZERO:
        raise InvalidTransfer("El monto debe ser mayor a cero")

    locked: dict[UUID, Cuenta] = {}
    for cuenta_id in sorted([origen_id, destino_id], key=str):
        locked[cuenta_id] = await _lock_account(db, cuenta_id)

    origen = locked[origen_id]
    destino = locked[destino_id]
    if origen.estado != EstadoCuenta.ACTIVA.value or destino.estado != EstadoCuenta.ACTIVA.value:
        raise AccountNotActive("Una de las cuentas no está activa")
    saldo_origen = Decimal(origen.saldo)
    permite_emision = origen.tipo == TipoCuenta.SANDBOX_EQUITY.value
    if saldo_origen < monto and not permite_emision:
        raise InsufficientFunds("Fondos insuficientes en la cuenta origen")

    transaccion = Transaccion(
        tipo=tipo,
        estado=EstadoTransaccion.PENDIENTE.value,
        monto=monto,
        moneda=origen.moneda,
        descripcion=descripcion,
        iniciada_por_usuario_id=iniciada_por_usuario_id,
        es_transferencia_global=es_transferencia_global,
    )
    db.add(transaccion)
    await db.flush()

    db.add(
        LedgerContable(
            transaccion_id=transaccion.id,
            cuenta_id=origen.id,
            naturaleza=NaturalezaAsiento.DEBITO.value,
            monto=monto,
        )
    )
    db.add(
        LedgerContable(
            transaccion_id=transaccion.id,
            cuenta_id=destino.id,
            naturaleza=NaturalezaAsiento.CREDITO.value,
            monto=monto,
        )
    )

    origen.saldo = Decimal(origen.saldo) - monto
    destino.saldo = Decimal(destino.saldo) + monto
    transaccion.estado = EstadoTransaccion.COMPLETADA.value
    await db.flush()
    await db.commit()
    await db.refresh(transaccion)
    return transaccion

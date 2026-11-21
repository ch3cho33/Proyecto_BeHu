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
    categoria: str | None = None,
    comercio: str | None = None,
    forzada: bool = False,
    is_impulsive: bool = False,
    metodo_pago: str | None = None,
    notas: str | None = None,
    recurrencia: str | None = None,
    bucket: str | None = None,
    commit: bool = True,
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
        categoria=categoria,
        comercio=comercio,
        forzada=forzada,
        is_impulsive=is_impulsive or forzada,
        metodo_pago=metodo_pago,
        notas=notas,
        recurrencia=recurrencia,
        bucket=bucket,
    )
    db.add(transaccion)
    await db.flush()

    from app.core.crypto import sello_ledger

    def _asiento(cuenta_id, naturaleza: str) -> LedgerContable:
        return LedgerContable(
            transaccion_id=transaccion.id,
            cuenta_id=cuenta_id,
            naturaleza=naturaleza,
            monto=monto,
            sello_hmac=sello_ledger(
                transaccion_id=str(transaccion.id),
                cuenta_id=str(cuenta_id),
                naturaleza=naturaleza,
                monto=f"{monto:.2f}",
            ),
        )

    db.add(_asiento(origen.id, NaturalezaAsiento.DEBITO.value))
    db.add(_asiento(destino.id, NaturalezaAsiento.CREDITO.value))

    origen.saldo = Decimal(origen.saldo) - monto
    destino.saldo = Decimal(destino.saldo) + monto
    transaccion.estado = EstadoTransaccion.COMPLETADA.value
    await db.flush()
    if commit:
        await db.commit()
        await db.refresh(transaccion)
    return transaccion


def vuelto_redondeo(monto: Decimal, paso: Decimal = Decimal("5000")) -> Decimal:
    """Vuelto hasta el siguiente múltiplo. 13.400 con paso 5.000 deja 1.600."""
    monto = Decimal(monto).quantize(Decimal("0.01"))
    resto = monto % paso
    if resto == 0:
        return Decimal("0.00")
    return (paso - resto).quantize(Decimal("0.01"))

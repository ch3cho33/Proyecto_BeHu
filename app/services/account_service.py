"""Consulta de saldo derivado del ledger y visibilidad por rol (RF-06)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Cuenta
from app.models.ledger import LedgerContable
from app.models.transaction import Transaccion
from app.models.user import Usuario
from app.schemas.account import AccountBalanceResponse, AccountMeResponse
from app.schemas.transaction import TransactionPublic
from app.services.exceptions import UserAccountMissing
from app.services.ledger_service import saldo_desde_ledger


async def get_cuenta_usuario(db: AsyncSession, usuario: Usuario) -> Cuenta:
    cuenta = await db.scalar(select(Cuenta).where(Cuenta.usuario_id == usuario.id))
    if cuenta is None:
        raise UserAccountMissing("El usuario no tiene cuenta transaccional")
    return cuenta


async def _movimientos_visibles(
    db: AsyncSession,
    cuenta: Cuenta,
) -> list[TransactionPublic]:
    stmt = (
        select(Transaccion)
        .join(LedgerContable, LedgerContable.transaccion_id == Transaccion.id)
        .where(LedgerContable.cuenta_id == cuenta.id)
        .order_by(Transaccion.created_at.desc())
        .distinct()
    )
    if not cuenta.puede_ver_transferencias_globales():
        stmt = stmt.where(Transaccion.es_transferencia_global.is_(False))

    result = await db.execute(stmt)
    return [TransactionPublic.model_validate(tx) for tx in result.scalars().all()]


async def snapshot_cuenta(db: AsyncSession, usuario: Usuario) -> AccountMeResponse:
    cuenta = await get_cuenta_usuario(db, usuario)
    saldo_ledger = await saldo_desde_ledger(db, cuenta.id)
    movimientos = await _movimientos_visibles(db, cuenta)
    return AccountMeResponse(
        account=AccountBalanceResponse(
            account_id=cuenta.id,
            tipo=cuenta.tipo,
            saldo=saldo_ledger,
            moneda=cuenta.moneda,
            limite_gasto_diario=cuenta.limite_gasto_diario,
            limite_gasto_mensual=cuenta.limite_gasto_mensual,
            puede_ver_transferencias_globales=cuenta.puede_ver_transferencias_globales(),
        ),
        movimientos=movimientos,
    )


async def asignar_presupuesto(
    db: AsyncSession,
    senior: Usuario,
    cuenta_junior_id: UUID,
    monto,
    descripcion: str | None,
):
    from app.models.transaction import TipoTransaccion
    from app.services.ledger_service import transferir
    from app.services.supervision_service import exigir_supervision_activa

    cuenta_senior = await get_cuenta_usuario(db, senior)
    await exigir_supervision_activa(db, cuenta_senior.id, cuenta_junior_id)
    return await transferir(
        db,
        origen_id=cuenta_senior.id,
        destino_id=cuenta_junior_id,
        monto=monto,
        iniciada_por_usuario_id=senior.id,
        tipo=TipoTransaccion.ASIGNACION_PRESUPUESTO.value,
        descripcion=descripcion or "Asignación de presupuesto parental",
        es_transferencia_global=False,
    )

"""Comprobante con los dos asientos del ledger."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ledger import LedgerContable
from app.models.transaction import Transaccion
from app.models.user import Usuario
from app.schemas.transaction import LedgerLine, ReceiptPublic, TransactionPublic
from app.services.account_service import get_cuenta_usuario
from app.services.exceptions import ForbiddenAction, AccountNotFound


async def comprobante(db: AsyncSession, usuario: Usuario, transaccion_id: UUID) -> ReceiptPublic:
    cuenta = await get_cuenta_usuario(db, usuario)
    transaccion = await db.scalar(
        select(Transaccion)
        .options(selectinload(Transaccion.asientos).selectinload(LedgerContable.cuenta))
        .where(Transaccion.id == transaccion_id)
    )
    if transaccion is None:
        raise AccountNotFound("Movimiento no encontrado")
    propias = {asiento.cuenta_id for asiento in transaccion.asientos}
    if cuenta.id not in propias and transaccion.iniciada_por_usuario_id != usuario.id:
        raise ForbiddenAction("Ese comprobante no es de tu cuenta")
    if not cuenta.puede_ver_transferencias_globales() and transaccion.es_transferencia_global:
        raise ForbiddenAction("Ese comprobante no es de tu cuenta")
    lineas = [
        LedgerLine(
            naturaleza=asiento.naturaleza,
            cuenta=asiento.cuenta.tipo,
            monto=asiento.monto,
        )
        for asiento in transaccion.asientos
    ]
    return ReceiptPublic(transaccion=TransactionPublic.model_validate(transaccion), asientos=lineas)

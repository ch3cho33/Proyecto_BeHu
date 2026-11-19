"""Envío sandbox entre cuentas usando la llave @usuario.behu."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import TipoTransaccion
from app.models.user import Usuario
from app.schemas.transaction import KeyTransferRequest
from app.services.account_service import get_cuenta_usuario
from app.services.exceptions import AccountNotFound, InvalidTransfer
from app.services.ledger_service import transferir
from app.services.llave_service import normalizar_llave


async def enviar_por_llave(db: AsyncSession, origen: Usuario, payload: KeyTransferRequest):
    llave = normalizar_llave(payload.llave)
    destino_user = await db.scalar(select(Usuario).where(Usuario.llave_behu == llave))
    if destino_user is None:
        raise AccountNotFound("No hay una cuenta con esa llave BeHu")
    if destino_user.id == origen.id:
        raise InvalidTransfer("No puedes enviarte dinero a tu propia llave")
    cuenta_origen = await get_cuenta_usuario(db, origen)
    cuenta_destino = await get_cuenta_usuario(db, destino_user)
    return await transferir(
        db,
        origen_id=cuenta_origen.id,
        destino_id=cuenta_destino.id,
        monto=Decimal(payload.monto),
        iniciada_por_usuario_id=origen.id,
        tipo=TipoTransaccion.TRANSFERENCIA_INTERNA.value,
        descripcion=payload.descripcion or f"Envío a @{llave}",
        es_transferencia_global=False,
        metodo_pago="TRANSFERENCIA",
    )

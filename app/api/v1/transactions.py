"""HU-07: compra simulada con alerta anti-impulsos."""

from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.schemas.transaction import IncomeRequest, MovementRequest, ReceiptPublic, SpendRequest, TransactionPublic
from app.services import neobank_service, receipt_service, spend_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionPublic, status_code=status.HTTP_201_CREATED)
async def register_movement(
    payload: MovementRequest,
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionPublic:
    transaccion, redondeo, meta = await neobank_service.registrar(db, user, payload)
    publico = TransactionPublic.model_validate(transaccion)
    publico.redondeo = redondeo
    publico.meta_redondeo = meta
    return publico


@router.post("/income", response_model=TransactionPublic, status_code=status.HTTP_201_CREATED)
async def register_income(
    payload: IncomeRequest,
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionPublic:
    transaccion = await neobank_service.registrar_ingreso(db, user, payload)
    return TransactionPublic.model_validate(transaccion)


@router.post("/spend", response_model=TransactionPublic, status_code=status.HTTP_201_CREATED)
async def spend(
    payload: SpendRequest,
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionPublic:
    transaccion = await spend_service.simular_compra(db, user, payload)
    return TransactionPublic.model_validate(transaccion)


@router.get("/{transaccion_id}/receipt", response_model=ReceiptPublic)
async def receipt(
    transaccion_id: UUID,
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReceiptPublic:
    return await receipt_service.comprobante(db, user, transaccion_id)

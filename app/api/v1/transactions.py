"""HU-07: compra simulada con alerta anti-impulsos."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.schemas.transaction import SpendRequest, TransactionPublic
from app.services import spend_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/spend", response_model=TransactionPublic, status_code=status.HTTP_201_CREATED)
async def spend(
    payload: SpendRequest,
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionPublic:
    transaccion = await spend_service.simular_compra(db, user, payload)
    return TransactionPublic.model_validate(transaccion)

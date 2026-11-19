"""RF-04: asignación de presupuesto Senior → Junior (sandbox)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.security import ROLE_SENIOR
from app.models.user import Usuario
from app.schemas.transaction import BudgetTransferRequest, TransactionPublic
from app.services import account_service

router = APIRouter(prefix="/transfers", tags=["transfers"])

SeniorUser = Annotated[Usuario, Depends(require_role(ROLE_SENIOR))]


@router.post("/budget", response_model=TransactionPublic, status_code=status.HTTP_201_CREATED)
async def assign_budget(
    payload: BudgetTransferRequest,
    senior: SeniorUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionPublic:
    transaccion = await account_service.asignar_presupuesto(
        db,
        senior,
        payload.cuenta_junior_id,
        payload.monto,
        payload.descripcion,
    )
    return TransactionPublic.model_validate(transaccion)

"""RF-06: saldo e historial filtrado por rol JWT."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.schemas.account import AccountMeResponse
from app.services import account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/me", response_model=AccountMeResponse)
async def get_my_account(
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountMeResponse:
    return await account_service.snapshot_cuenta(db, user)

"""Regla 50/30/20 sobre los ingresos del mes."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.services import neobank_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("/50-30-20")
async def rule_50_30_20(
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    return await neobank_service.resumen_503020(db, user)

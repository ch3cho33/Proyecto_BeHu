"""Respaldo cifrado de la cuenta."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.services import cloud_backup_service

router = APIRouter(prefix="/system", tags=["system"])


@router.post("/backup")
async def backup(
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    return await cloud_backup_service.respaldar(db, user)

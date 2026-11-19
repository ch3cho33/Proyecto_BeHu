"""HU-09: cápsulas y quiz de micro-learning."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.schemas.education import CompleteModuleRequest, CompleteModuleResponse, ModulePublic
from app.services import education_service

router = APIRouter(prefix="/education", tags=["education"])


@router.get("/modules", response_model=list[ModulePublic])
async def list_modules(
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ModulePublic]:
    return await education_service.listar_modulos(db, user)


@router.post("/modules/{modulo_id}/complete", response_model=CompleteModuleResponse)
async def complete_module(
    modulo_id: UUID,
    payload: CompleteModuleRequest,
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompleteModuleResponse:
    return await education_service.completar_modulo(db, user, modulo_id, payload.respuesta)

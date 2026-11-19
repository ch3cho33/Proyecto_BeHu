"""HU-06: metas de ahorro y abono que congela saldo."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.schemas.goal import GoalCreateRequest, GoalDepositRequest, GoalPublic
from app.services import goal_service

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalPublic, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreateRequest,
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GoalPublic:
    return await goal_service.crear_meta(db, user, payload)


@router.get("", response_model=list[GoalPublic])
async def list_goals(
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GoalPublic]:
    return await goal_service.listar_metas(db, user)


@router.post("/{meta_id}/deposit", response_model=GoalPublic)
async def deposit_goal(
    meta_id: UUID,
    payload: GoalDepositRequest,
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GoalPublic:
    return await goal_service.abonar_meta(db, user, meta_id, payload)

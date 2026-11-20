"""Campana de alertas financieras."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.schemas.catalog import NotificationPublic
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationPublic])
async def list_notifications(
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[NotificationPublic]:
    return await notification_service.listar(db, user)


@router.patch("/{notificacion_id}/read", response_model=NotificationPublic)
async def read_notification(
    notificacion_id: UUID,
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationPublic:
    return await notification_service.marcar_leida(db, user, notificacion_id)

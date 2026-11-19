"""RF-02 / RF-03 / RF-05: vínculo parental."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.security import ROLE_JUNIOR, ROLE_SENIOR
from app.models.user import Usuario
from app.schemas.supervision import (
    ActivityItem,
    CardStatusRequest,
    CardStatusResponse,
    CreateJuniorRequest,
    InvitationPublic,
    InvitationRespondRequest,
    InviteRequest,
    SupervisionCreateRequest,
    SupervisionJuniorItem,
    SupervisionPublic,
)
from app.services import invitation_service, supervision_service

router = APIRouter(prefix="/supervision", tags=["supervision"])

SeniorUser = Annotated[Usuario, Depends(require_role(ROLE_SENIOR))]
JuniorUser = Annotated[Usuario, Depends(require_role(ROLE_JUNIOR))]


@router.post("/invite", response_model=InvitationPublic, status_code=status.HTTP_201_CREATED)
async def invite_junior(
    payload: InviteRequest,
    senior: SeniorUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InvitationPublic:
    return await invitation_service.invitar(db, senior, payload)


@router.post("/create-junior", response_model=InvitationPublic, status_code=status.HTTP_201_CREATED)
async def create_junior(
    payload: CreateJuniorRequest,
    senior: SeniorUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InvitationPublic:
    return await invitation_service.crear_junior(db, senior, payload)


@router.get("/invitations", response_model=list[InvitationPublic])
async def pending_invitations(
    junior: JuniorUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[InvitationPublic]:
    return await invitation_service.listar_pendientes(db, junior)


@router.post("/invitations/{invitation_id}/respond", response_model=InvitationPublic)
async def respond_invitation(
    invitation_id: UUID,
    payload: InvitationRespondRequest,
    junior: JuniorUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InvitationPublic:
    return await invitation_service.responder(db, junior, invitation_id, payload.accept)


@router.get("/juniors/{junior_id}/activity", response_model=list[ActivityItem])
async def junior_activity(
    junior_id: UUID,
    senior: SeniorUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ActivityItem]:
    return await invitation_service.actividad(db, senior, junior_id)


@router.patch("/juniors/{junior_id}/card-status", response_model=CardStatusResponse)
async def junior_card_status(
    junior_id: UUID,
    payload: CardStatusRequest,
    senior: SeniorUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CardStatusResponse:
    return await invitation_service.cambiar_tarjeta(db, senior, junior_id, payload.bloqueada)


@router.post("/link", response_model=SupervisionPublic, status_code=status.HTTP_201_CREATED)
async def link_junior(
    payload: SupervisionCreateRequest,
    senior: SeniorUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SupervisionPublic:
    return await supervision_service.vincular(db, senior, payload)


@router.get("/juniors", response_model=list[SupervisionJuniorItem])
async def list_juniors(
    senior: SeniorUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SupervisionJuniorItem]:
    return await supervision_service.listar_juniors(db, senior)


@router.delete("/link/{supervision_id}", response_model=SupervisionPublic)
async def unlink_junior(
    supervision_id: UUID,
    senior: SeniorUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    confirmacion: Annotated[
        bool,
        Query(description="Debe ser true para confirmar la alerta de desvinculación"),
    ] = False,
) -> SupervisionPublic:
    return await supervision_service.desvincular(
        db,
        senior,
        supervision_id,
        confirmacion=confirmacion,
    )

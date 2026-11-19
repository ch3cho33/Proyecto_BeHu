"""RF-02 / RF-03 / RF-05: vínculo parental."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.security import ROLE_SENIOR
from app.models.user import Usuario
from app.schemas.supervision import SupervisionCreateRequest, SupervisionJuniorItem, SupervisionPublic
from app.services import supervision_service

router = APIRouter(prefix="/supervision", tags=["supervision"])

SeniorUser = Annotated[Usuario, Depends(require_role(ROLE_SENIOR))]


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

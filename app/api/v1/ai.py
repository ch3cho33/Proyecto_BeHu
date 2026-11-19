"""HU-05: consulta e historial de BeHu Mini."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.schemas.ai import AiConsultRequest, AiConsultResponse, AiHistoryItem, ParentalAlert
from app.services import behu_mini_ai

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/consult", response_model=AiConsultResponse)
async def consult(
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: AiConsultRequest | None = None,
) -> AiConsultResponse:
    pregunta = payload.pregunta if payload else None
    return await behu_mini_ai.consultar(db, user, pregunta)


@router.get("/parental-alerts", response_model=list[ParentalAlert])
async def parental_alerts(
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ParentalAlert]:
    return await behu_mini_ai.alertas_parentales(db, user)


@router.get("/history", response_model=list[AiHistoryItem])
async def history(
    user: Annotated[Usuario, Depends(get_current_user)],
) -> list[AiHistoryItem]:
    return await behu_mini_ai.listar_historial(user)

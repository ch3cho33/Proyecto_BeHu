"""HU-05: consulta e historial de BeHu Mini."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.schemas.ai import AiConsultRequest, AiConsultResponse, AiHistoryItem, ParentalAlert
from app.services import behu_mini_ai

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger("behu.mini")


@router.post("/consult", response_model=AiConsultResponse)
async def consult(
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: AiConsultRequest | None = None,
) -> AiConsultResponse:
    pregunta = payload.texto() if payload else None
    try:
        return await behu_mini_ai.consultar(db, user, pregunta)
    except Exception:
        logger.exception("POST /ai/consult no pudo completar el cálculo")
        return await behu_mini_ai.respuesta_de_respaldo(db, user)


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

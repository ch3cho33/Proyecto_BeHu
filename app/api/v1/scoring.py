"""HU-08: Score BeHu del usuario autenticado."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.schemas.scoring import ScoreResponse
from app.services import scoring_service

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.get("/me", response_model=ScoreResponse)
async def my_score(
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScoreResponse:
    return await scoring_service.calcular_score(db, user)

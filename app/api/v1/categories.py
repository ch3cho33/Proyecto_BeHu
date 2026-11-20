"""Categorías del sistema y categorías personales."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.schemas.catalog import CategoryCreateRequest, CategoryPublic
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryPublic])
async def list_categories(
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CategoryPublic]:
    return await category_service.listar(db, user)


@router.post("", response_model=CategoryPublic, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreateRequest,
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CategoryPublic:
    return await category_service.crear(db, user, payload.nombre)

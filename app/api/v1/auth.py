"""RF-01: registro y login."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.schemas.user import AuthSessionResponse, UserLoginRequest, UserPublic, UserRegisterRequest, UserUpdateRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthSessionResponse:
    return await auth_service.register(db, payload)


@router.post("/login", response_model=AuthSessionResponse)
async def login(
    payload: UserLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthSessionResponse:
    return await auth_service.login(db, payload)


users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.patch("/me", response_model=UserPublic)
async def update_me(
    payload: UserUpdateRequest,
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPublic:
    return await auth_service.actualizar_perfil(db, user, payload)

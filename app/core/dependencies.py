"""Dependencias FastAPI: DB, usuario actual y aislamiento de roles."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenError, decode_access_token, parse_user_id
from app.models.user import Usuario

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = parse_user_id(payload)
        token_rol = payload["rol"]
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo o inexistente",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.rol != token_rol:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Rol del token no coincide",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*roles: str) -> Callable[..., Usuario]:
    """Aislamiento Senior / Junior para endpoints móviles."""

    allowed = frozenset(roles)

    async def _checker(
        user: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        if user.rol not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Perfil no autorizado para este recurso",
            )
        return user

    return _checker

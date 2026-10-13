"""Hashing bcrypt y JWT stateless para clientes móviles / PWA."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import settings

ROLE_SENIOR = "SENIOR"
ROLE_JUNIOR = "JUNIOR"
ALLOWED_ROLES = frozenset({ROLE_SENIOR, ROLE_JUNIOR})


class TokenError(Exception):
    """Token ausente, malformado, expirado o con claims inválidos."""


def hash_password(plain_password: str) -> str:
    digest = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return digest.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def create_access_token(
    *,
    user_id: UUID,
    rol: str,
    expires_delta: timedelta | None = None,
) -> str:
    if rol not in ALLOWED_ROLES:
        raise ValueError(f"Rol JWT no permitido: {rol}")

    now = datetime.now(timezone.utc)
    expires = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "rol": rol,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise TokenError("Token inválido o expirado") from exc

    sub = payload.get("sub")
    rol = payload.get("rol")
    if not sub or rol not in ALLOWED_ROLES:
        raise TokenError("Claims JWT incompletos")
    if payload.get("typ") != "access":
        raise TokenError("Tipo de token no soportado")
    return payload


def parse_user_id(payload: dict[str, Any]) -> UUID:
    try:
        return UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise TokenError("sub JWT inválido") from exc

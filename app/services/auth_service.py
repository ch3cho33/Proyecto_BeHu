"""Registro, login y emisión de JWT para clientes móviles."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    ALLOWED_ROLES,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.account import CuentaJunior, CuentaSenior
from app.models.user import Usuario
from app.schemas.user import AuthSessionResponse, UserLoginRequest, UserPublic, UserRegisterRequest
from app.services.exceptions import EmailAlreadyRegistered, InvalidCredentials, InvalidRole


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _build_session(user: Usuario) -> AuthSessionResponse:
    token = create_access_token(user_id=user.id, rol=user.rol)
    return AuthSessionResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        rol=user.rol,
        user=UserPublic.model_validate(user),
    )


async def register(db: AsyncSession, payload: UserRegisterRequest) -> AuthSessionResponse:
    if payload.rol not in ALLOWED_ROLES:
        raise InvalidRole("Rol no permitido")

    email = _normalize_email(payload.email)
    existing = await db.scalar(select(Usuario).where(Usuario.email == email))
    if existing is not None:
        raise EmailAlreadyRegistered("El correo ya está registrado")

    user = Usuario(
        email=email,
        password_hash=hash_password(payload.password),
        nombres=payload.nombres.strip(),
        apellidos=payload.apellidos.strip(),
        rol=payload.rol,
        telefono=payload.telefono,
        moneda_preferida=payload.moneda,
    )
    db.add(user)
    await db.flush()

    cuenta_cls: type[CuentaSenior] | type[CuentaJunior] = (
        CuentaSenior if payload.rol == "SENIOR" else CuentaJunior
    )
    db.add(cuenta_cls(usuario_id=user.id, tipo=payload.rol, moneda=payload.moneda))
    await db.commit()
    await db.refresh(user)
    return _build_session(user)


async def login(db: AsyncSession, payload: UserLoginRequest) -> AuthSessionResponse:
    email = _normalize_email(payload.email)
    user = await db.scalar(select(Usuario).where(Usuario.email == email))
    if user is None or not user.is_active:
        raise InvalidCredentials("Correo o contraseña inválidos")
    if not verify_password(payload.password, user.password_hash):
        raise InvalidCredentials("Correo o contraseña inválidos")
    return _build_session(user)

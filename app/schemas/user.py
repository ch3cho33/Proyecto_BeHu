"""Schemas de autenticación e identidad (payloads livianos)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from app.core.security import ROLE_JUNIOR, ROLE_SENIOR


def _sandbox_email(value: str) -> str:
    """Acepta dominios de laboratorio (.test) que EmailStr RFC rechaza."""
    cleaned = value.strip().lower()
    if "@" not in cleaned or " " in cleaned:
        raise ValueError("Correo inválido")
    local, _, domain = cleaned.partition("@")
    if not local or "." not in domain:
        raise ValueError("Correo inválido")
    return cleaned


SandboxEmail = Annotated[str, AfterValidator(_sandbox_email)]


class UserRegisterRequest(BaseModel):
    email: SandboxEmail
    password: str = Field(min_length=8, max_length=72)
    nombres: str = Field(min_length=1, max_length=120)
    apellidos: str = Field(min_length=1, max_length=120)
    rol: str = Field(pattern=f"^({ROLE_SENIOR}|{ROLE_JUNIOR})$")
    telefono: str | None = Field(default=None, max_length=32)
    moneda: str = Field(default="COP", pattern="^(COP|USD|EUR|MXN|PEN)$")
    ingreso_mensual_estimado: Decimal | None = Field(default=None, ge=0)

    @field_validator("password")
    @classmethod
    def _password_mixta(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value) or not any(ch.isdigit() for ch in value):
            raise ValueError("La contraseña necesita letras y números")
        return value


class UserLoginRequest(BaseModel):
    email: SandboxEmail
    password: str = Field(min_length=1, max_length=72)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: SandboxEmail
    nombres: str
    apellidos: str
    rol: str
    is_active: bool
    kyc_status: str
    moneda_preferida: str = "COP"
    ingreso_mensual_estimado: Decimal | None = None
    created_at: datetime


class UserUpdateRequest(BaseModel):
    nombres: str = Field(min_length=1, max_length=120)
    apellidos: str = Field(min_length=1, max_length=120)
    moneda: str = Field(pattern="^(COP|USD|EUR|MXN|PEN)$")
    ingreso_mensual_estimado: Decimal | None = Field(default=None, ge=0)


class TokenResponse(BaseModel):
    """Respuesta de login/registro para persistir en el dispositivo."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Segundos hasta exp")
    rol: str


class AuthSessionResponse(TokenResponse):
    """Login/registro: JWT + perfil público para el cliente móvil."""

    user: UserPublic

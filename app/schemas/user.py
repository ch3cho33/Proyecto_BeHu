"""Schemas de autenticación e identidad (payloads livianos)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.security import ROLE_JUNIOR, ROLE_SENIOR


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    nombres: str = Field(min_length=1, max_length=120)
    apellidos: str = Field(min_length=1, max_length=120)
    rol: str = Field(pattern=f"^({ROLE_SENIOR}|{ROLE_JUNIOR})$")
    telefono: str | None = Field(default=None, max_length=32)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    """Respuesta de login/registro para persistir en el dispositivo."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Segundos hasta exp")
    rol: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    nombres: str
    apellidos: str
    rol: str
    is_active: bool
    kyc_status: str
    created_at: datetime

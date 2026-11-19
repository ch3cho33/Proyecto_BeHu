"""Configuración 12-factor (Pydantic Settings)."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno del API. Pensado para Railway y desarrollo local."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "behu-api"
    app_version: str = "0.4.0"
    environment: str = "development"
    debug: bool = False

    database_url: str = Field(
        default="sqlite+aiosqlite:///./behu_sandbox.db"
    )
    auto_create_tables: bool = Field(default=True)
    mongodb_uri: str = Field(default="mongodb://localhost:27017")
    mongodb_db: str = Field(default="behu")

    jwt_secret: str = Field(default="change-me-to-a-long-random-secret-key")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60, ge=5, le=1440)

    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8081,http://127.0.0.1:3000"
    )
    frontend_url: str = Field(default="")

    aws_region: str = Field(default="us-east-1")
    aws_kms_key_id: str = Field(default="")
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")
    aws_s3_kyc_bucket: str = Field(default="")

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return "postgresql+asyncpg://" + value[len("postgres://") :]
        if value.startswith("postgresql://") and "+asyncpg" not in value.split("://", 1)[0]:
            return "postgresql+asyncpg://" + value[len("postgresql://") :]
        return value

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_min_length(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET debe tener al menos 32 caracteres")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        extra = self.frontend_url.strip().rstrip("/")
        if extra and extra not in origins:
            origins.append(extra)
        return origins

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

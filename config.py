from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional

class Settings(BaseSettings):
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # MongoDB
    DATABASE_URL: str
    DATABASE_NAME: str

    # Pasarela de pagos
    MERCADOPAGO_API_KEY: Optional[str] = None

    # Entorno
    ENV: str = "development"

    @field_validator("ENV")
    def validate_env(cls, v):
        allowed = {"development", "production", "test"}
        if v not in allowed:
            raise ValueError(f"ENV debe ser uno de: {allowed}")
        return v

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

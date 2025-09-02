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

    # --- NUEVAS VARIABLES PARA MERCADO PAGO ---
    # Tu Access Token privado de Mercado Pago (lo leerá del .env)
    MERCADOPAGO_ACCESS_TOKEN: Optional[str] = None
    
    # URL base para tus webhooks (importante para desarrollo y producción)
    # En desarrollo usaremos ngrok, en producción será tu dominio
    WEBHOOK_BASE_URL: str = "http://localhost:8000"

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

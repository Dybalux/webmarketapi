from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Clave secreta para JWT. ¡CAMBIA ESTO EN PRODUCCIÓN Y USA UNA VARIABLE DE ENTORNO SEGURA!
    SECRET_KEY: str = "your-super-secret-key-replace-me-in-prod-12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # Tiempo de expiración del token JWT

    # Configuración de la base de datos (usaremos MongoDB con Motor)
    DATABASE_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "bebidas_db"

    # Configuración para pasarelas de pago (ejemplo)
    MERCADOPAGO_API_KEY: Optional[str] = None
    
    # Entorno de la aplicación (development, production)
    ENV: str = "development"

    # Configuración para cargar variables de entorno desde un archivo .env
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
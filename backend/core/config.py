from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    Lee configuración desde variables de entorno (.env).
    En producción real estos valores nunca se hardcodean ni se suben a Git.
    """

    PROJECT_NAME: str = "GyverLabs"
    ENVIRONMENT: str = "evaluacion"

    # La versión de evaluación usa SQLite local (cero dependencias externas)
    # para que el jurado pueda ejecutar la demo con un simple `pip install`.
    # En producción real, DATABASE_URL apunta a PostgreSQL multi-tenant
    # (ver docs/ARQUITECTURA.md) y se configura vía variable de entorno.
    DATABASE_URL: str = "sqlite:///./gyverlabs_demo.db"
    REDIS_URL: str = "redis://redis:6379/0"  # no requerido para correr la demo

    JWT_SECRET_KEY: str = "CAMBIAR_EN_PRODUCCION"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # En la demo se permite cualquier origen porque el frontend se abre como
    # archivo local o se sirve con un servidor estático simple en un puerto
    # variable. En producción esto se restringe a los dominios reales de
    # cada institución (ver docs/ARQUITECTURA.md).
    ALLOWED_ORIGINS: List[str] = ["*"]

    # Umbral mínimo de riesgo para disparar una alerta (versión demo).
    # El umbral real y la calibración por institución viven en el
    # servicio de producción — ver AVISO en srd_service.py
    SRD_UMBRAL_DEMO: float = 0.65

    class Config:
        env_file = ".env"


settings = Settings()

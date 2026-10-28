"""Configuración de la aplicación, leída desde el entorno o el archivo `.env`."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes de la API resueltos desde variables de entorno.

    Los valores por defecto permiten levantar la API sin configuración previa;
    en producción `JWT_SECRET` debe cambiarse por un valor propio.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://vet:vet@db:5432/vetclinic"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia única de ajustes, cacheada por proceso."""
    return Settings()


settings = get_settings()

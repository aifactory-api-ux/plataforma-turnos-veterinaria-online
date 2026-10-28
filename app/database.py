"""Engine, sesión y tipos de columna compartidos por toda la aplicación."""

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, TypeDecorator, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings


class Base(DeclarativeBase):
    """Base declarativa de SQLAlchemy 2 sobre la que se construyen los modelos."""


class UTCDateTime(TypeDecorator):
    """Columna de fecha y hora que se persiste y se devuelve siempre en UTC.

    En PostgreSQL la columna se guarda sin zona horaria en UTC; en SQLite el
    valor se normaliza de la misma forma. Al leer se reincorpora
    `tzinfo=UTC`, de modo que la API serializa siempre marcas `...Z`.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Any
    ) -> datetime | None:
        """Normaliza el valor a UTC naive antes de enviarlo al motor."""
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(
        self, value: datetime | None, dialect: Any
    ) -> datetime | None:
        """Devuelve el valor leído como fecha y hora consciente de UTC."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def _engine_options(url: str) -> dict[str, Any]:
    """Opciones del engine según el motor configurado en `DATABASE_URL`."""
    options: dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        # SQLite no admite el uso compartido de conexiones entre hilos por defecto.
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            # Una base en memoria debe conservar la misma conexión para todos los hilos.
            options["poolclass"] = StaticPool
    return options


engine: Engine = create_engine(
    settings.database_url,
    future=True,
    **_engine_options(settings.database_url),
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Iterator[Session]:
    """Dependencia de FastAPI que entrega una sesión por petición."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

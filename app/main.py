"""Punto de entrada de la API de la clínica veterinaria."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.database import Base, engine
from app.routers.appointments import router as appointments_router
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.pets import router as pets_router
from app.routers.vets import router as vets_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Crea el esquema de la base de datos al arrancar la aplicación."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="API de turnos veterinaria",
    description=(
        "Registro de clientes y mascotas y gestión de turnos con veterinarios "
        "para la clínica veterinaria."
    ),
    version=__version__,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(vets_router)
app.include_router(pets_router)
app.include_router(appointments_router)

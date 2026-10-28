"""Configuración compartida de la suite de pruebas.

La base de datos de las pruebas se toma de la variable `DATABASE_URL`. Cuando
no está definida se usa una base SQLite temporal, de modo que la suite se
ejecuta sin un servidor PostgreSQL y sin un demonio Docker.
"""

import os
import shutil
import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# La URL se fija antes de importar `app.*`: los ajustes se leen al importar.
_TMP_DIR = tempfile.mkdtemp(prefix="vetclinic-tests-")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP_DIR) / 'vetclinic.db'}"

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import create_access_token, hash_password  # noqa: E402

# Los correos usan un dominio válido: `EmailStr` rechaza los dominios
# reservados o de uso especial, como `.test`.
CLIENT_EMAIL = "cliente@example.com"
VET_EMAIL = "veterinario@example.com"
CLIENT_PASSWORD = "secreto123"
VET_PASSWORD = "veterinaria1"


def create_user(session: Session, email: str, password: str, role: str) -> User:
    """Crea una cuenta en la base de datos con la contraseña hasheada."""
    user = User(email=email, password_hash=hash_password(password), role=role)
    session.add(user)
    session.flush()
    return user


@pytest.fixture(scope="session", autouse=True)
def _temporary_directory() -> Iterator[None]:
    """Elimina la base de datos temporal al terminar la sesión de pruebas."""
    yield
    shutil.rmtree(_TMP_DIR, ignore_errors=True)


@pytest.fixture(scope="session")
def database() -> Iterator[object]:
    """Prepara un esquema limpio en la base de datos de las pruebas."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(database: object) -> Iterator[TestClient]:
    """Cliente HTTP de pruebas con el ciclo de vida de la aplicación activo."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def accounts(database: object) -> dict[str, User]:
    """Cuentas de ejemplo: un cliente y un veterinario."""
    with SessionLocal() as session:
        client_user = create_user(session, CLIENT_EMAIL, CLIENT_PASSWORD, "client")
        vet_user = create_user(session, VET_EMAIL, VET_PASSWORD, "vet")
        session.commit()
        session.expunge_all()
    return {"client": client_user, "vet": vet_user}


@pytest.fixture(scope="session")
def client_user(accounts: dict[str, User]) -> User:
    """Cuenta de ejemplo con rol `client`."""
    return accounts["client"]


@pytest.fixture(scope="session")
def vet_user(accounts: dict[str, User]) -> User:
    """Cuenta de ejemplo con rol `vet`."""
    return accounts["vet"]


@pytest.fixture(scope="session")
def client_token(client_user: User) -> str:
    """Token bearer de la cuenta de ejemplo con rol `client`."""
    return create_access_token(client_user.id, client_user.role)


@pytest.fixture(scope="session")
def vet_token(vet_user: User) -> str:
    """Token bearer de la cuenta de ejemplo con rol `vet`."""
    return create_access_token(vet_user.id, vet_user.role)


@pytest.fixture()
def client_headers(client_token: str) -> dict[str, str]:
    """Cabecera `Authorization` de la cuenta de ejemplo con rol `client`."""
    return {"Authorization": f"Bearer {client_token}"}


@pytest.fixture()
def vet_headers(vet_token: str) -> dict[str, str]:
    """Cabecera `Authorization` de la cuenta de ejemplo con rol `vet`."""
    return {"Authorization": f"Bearer {vet_token}"}


@pytest.fixture()
def unique_email() -> str:
    """Correo irrepetible para las cuentas creadas dentro de una prueba."""
    return f"usuario-{uuid.uuid4().hex[:12]}@example.com"

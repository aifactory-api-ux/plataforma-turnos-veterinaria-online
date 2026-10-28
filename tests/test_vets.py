"""Pruebas del directorio de veterinarios.

`GET /vets` exige un token bearer válido y devuelve únicamente las cuentas con
rol `vet`. Para comprobar el caso del directorio vacío se aísla la base de
datos sustituyendo la dependencia `get_db`, de modo que el estado compartido
por el resto de la suite no influya en el resultado.
"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, SessionLocal, get_db
from app.main import app
from app.models import User

PASSWORD = "secreto123"


def _unique_email(prefix: str) -> str:
    """Correo irrepetible para las cuentas creadas dentro de una prueba."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


def _register(client: TestClient, email: str, role: str) -> int:
    """Registra una cuenta y devuelve el identificador asignado."""
    response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "role": role},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _login(client: TestClient, email: str) -> str:
    """Inicia sesión y devuelve el token bearer de la cuenta."""
    response = client.post(
        "/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture()
def isolated_client() -> Iterator[TestClient]:
    """Cliente HTTP de la aplicación real con una base de datos aislada."""
    isolated_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=isolated_engine)
    isolated_session_factory = sessionmaker(
        bind=isolated_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db() -> Iterator[Session]:
        session = isolated_session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=isolated_engine)
        isolated_engine.dispose()


def test_directorio_devuelve_solo_los_veterinarios(client: TestClient) -> None:
    """El listado incluye a los veterinarios y excluye a las cuentas cliente."""
    client_email = _unique_email("directorio-cliente")
    vet_email = _unique_email("directorio-vet")
    other_vet_email = _unique_email("directorio-vet")

    _register(client, client_email, "client")
    vet_id = _register(client, vet_email, "vet")
    other_vet_id = _register(client, other_vet_email, "vet")

    token = _login(client, client_email)
    response = client.get("/vets", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)

    entries = {entry["email"]: entry for entry in body}
    assert entries[vet_email] == {"id": vet_id, "email": vet_email}
    assert entries[other_vet_email] == {"id": other_vet_id, "email": other_vet_email}
    assert client_email not in entries
    assert all(set(entry) == {"id", "email"} for entry in body)

    with SessionLocal() as session:
        vet_ids = set(
            session.scalars(select(User.id).where(User.role == "vet")).all()
        )
    assert {entry["id"] for entry in body} <= vet_ids


def test_directorio_vacio_responde_200_con_lista_vacia(
    isolated_client: TestClient,
) -> None:
    """Sin veterinarios registrados el directorio responde con una lista vacía."""
    client_email = _unique_email("directorio-sin-vets")
    _register(isolated_client, client_email, "client")

    token = _login(isolated_client, client_email)
    response = isolated_client.get(
        "/vets", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == []


def test_directorio_sin_token_responde_401(client: TestClient) -> None:
    """Sin cabecera `Authorization` el directorio responde 401."""
    response = client.get("/vets")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_directorio_con_token_invalido_responde_401(client: TestClient) -> None:
    """Un token que no es un JWT válido se rechaza con 401."""
    response = client.get(
        "/vets", headers={"Authorization": "Bearer invalid.token.value"}
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"

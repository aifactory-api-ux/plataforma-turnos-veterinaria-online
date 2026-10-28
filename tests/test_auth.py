"""Pruebas del alta de cuentas, el inicio de sesión y la protección bearer.

Las rutas de negocio protegidas (`/vets`, `/pets`, `/appointments`) llegan en
grupos posteriores, así que la verificación del guardián de autenticación se
apoya en una aplicación mínima que usa la misma dependencia `get_current_user`
que emplean los routers de la API.
"""

import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import settings
from app.database import SessionLocal
from app.dependencies import get_current_user
from app.models import User
from app.security import create_access_token, decode_access_token, verify_password

PASSWORD = "secreto123"


def _count_users(email: str) -> int:
    """Devuelve cuántas cuentas existen con el correo indicado."""
    with SessionLocal() as session:
        return session.scalar(
            select(func.count()).select_from(User).where(User.email == email)
        )


def _stored_user(email: str) -> User | None:
    """Devuelve la cuenta almacenada con el correo indicado, si existe."""
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is not None:
            session.expunge(user)
        return user


@pytest.fixture()
def new_email() -> str:
    """Correo irrepetible y válido para las cuentas creadas en las pruebas."""
    return f"usuario-{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture()
def protected_client(database: object) -> Iterator[TestClient]:
    """Cliente de una aplicación mínima con una ruta protegida por bearer."""
    protected_app = FastAPI()

    @protected_app.get("/protegido")
    def protegido(user: User = Depends(get_current_user)) -> dict[str, int]:
        """Devuelve el identificador de la cuenta autenticada."""
        return {"id": user.id}

    with TestClient(protected_app) as test_client:
        yield test_client


def test_registro_de_un_cliente_responde_201(
    client: TestClient, new_email: str
) -> None:
    """`POST /auth/register` crea una cuenta de cliente y devuelve sus datos."""
    response = client.post(
        "/auth/register",
        json={"email": new_email, "password": PASSWORD, "role": "client"},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "role"}
    assert body["email"] == new_email
    assert body["role"] == "client"
    assert isinstance(body["id"], int)


def test_registro_de_un_veterinario_responde_201(
    client: TestClient, new_email: str
) -> None:
    """`POST /auth/register` también acepta el rol `vet`."""
    response = client.post(
        "/auth/register",
        json={"email": new_email, "password": PASSWORD, "role": "vet"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == new_email
    assert body["role"] == "vet"


def test_registro_con_correo_duplicado_responde_409(
    client: TestClient, new_email: str
) -> None:
    """Un correo ya registrado se rechaza con 409 y no duplica la cuenta."""
    payload = {"email": new_email, "password": PASSWORD, "role": "client"}
    first = client.post("/auth/register", json=payload)
    second = client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert _count_users(new_email) == 1


def test_registro_con_contrasena_corta_responde_422(
    client: TestClient, new_email: str
) -> None:
    """Una contraseña de menos de 8 caracteres se rechaza con 422."""
    response = client.post(
        "/auth/register",
        json={"email": new_email, "password": "corto7", "role": "client"},
    )

    assert response.status_code == 422
    assert _count_users(new_email) == 0


def test_registro_con_rol_invalido_responde_422(
    client: TestClient, new_email: str
) -> None:
    """Un rol distinto de `client` o `vet` se rechaza con 422."""
    response = client.post(
        "/auth/register",
        json={"email": new_email, "password": PASSWORD, "role": "admin"},
    )

    assert response.status_code == 422
    assert _count_users(new_email) == 0


def test_registro_no_devuelve_la_contrasena_ni_la_almacena_en_claro(
    client: TestClient, new_email: str
) -> None:
    """La respuesta solo trae datos públicos y la contraseña se guarda hasheada."""
    response = client.post(
        "/auth/register",
        json={"email": new_email, "password": PASSWORD, "role": "client"},
    )

    assert response.status_code == 201
    assert PASSWORD not in response.text

    stored = _stored_user(new_email)
    assert stored is not None
    assert stored.password_hash != PASSWORD
    assert verify_password(PASSWORD, stored.password_hash)


def test_inicio_de_sesion_exitoso_responde_200(
    client: TestClient, new_email: str
) -> None:
    """`POST /auth/login` devuelve 200 con un token bearer utilizable."""
    client.post(
        "/auth/register",
        json={"email": new_email, "password": PASSWORD, "role": "client"},
    )

    response = client.post(
        "/auth/login", json={"email": new_email, "password": PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    payload = decode_access_token(body["access_token"])
    stored = _stored_user(new_email)
    assert stored is not None
    assert payload["sub"] == str(stored.id)
    assert payload["role"] == "client"
    assert "iat" in payload
    assert "exp" in payload


def test_inicio_de_sesion_con_contrasena_incorrecta_responde_401(
    client: TestClient, new_email: str
) -> None:
    """Una contraseña que no coincide se rechaza con 401."""
    client.post(
        "/auth/register",
        json={"email": new_email, "password": PASSWORD, "role": "client"},
    )

    response = client.post(
        "/auth/login", json={"email": new_email, "password": "incorrecta9"}
    )

    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_inicio_de_sesion_con_correo_desconocido_responde_401(
    client: TestClient, new_email: str
) -> None:
    """Un correo sin cuenta responde 401 sin revelar información."""
    response = client.post(
        "/auth/login", json={"email": new_email, "password": PASSWORD}
    )

    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_ruta_protegida_sin_cabecera_responde_401(
    protected_client: TestClient,
) -> None:
    """Sin cabecera `Authorization` la respuesta es 401 con `WWW-Authenticate`."""
    response = protected_client.get("/protegido")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_ruta_protegida_con_cabecera_mal_formada_responde_401(
    protected_client: TestClient,
) -> None:
    """Un esquema que no es `Bearer` se rechaza con 401."""
    response = protected_client.get(
        "/protegido", headers={"Authorization": "Basic dXNlcjpwYXNz"}
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_ruta_protegida_con_token_invalido_responde_401(
    protected_client: TestClient,
) -> None:
    """Un token que no es un JWT válido se rechaza con 401."""
    response = protected_client.get(
        "/protegido", headers={"Authorization": "Bearer invalid.token.value"}
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_ruta_protegida_con_token_caducado_responde_401(
    protected_client: TestClient, client_user: User
) -> None:
    """Un token ya caducado se rechaza con 401."""
    token = create_access_token(client_user.id, client_user.role, expires_minutes=-5)

    response = protected_client.get(
        "/protegido", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_ruta_protegida_con_token_firmado_con_otro_secreto_responde_401(
    protected_client: TestClient, client_user: User
) -> None:
    """Un token firmado con otro secreto se rechaza con 401."""
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(client_user.id),
            "role": client_user.role,
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        "secreto-ajeno",
        algorithm=settings.jwt_algorithm,
    )

    response = protected_client.get(
        "/protegido", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_ruta_protegida_con_token_valido_responde_200(
    protected_client: TestClient, client_user: User
) -> None:
    """Un token válido deja pasar la petición y resuelve la cuenta."""
    token = create_access_token(client_user.id, client_user.role)

    response = protected_client.get(
        "/protegido", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"id": client_user.id}

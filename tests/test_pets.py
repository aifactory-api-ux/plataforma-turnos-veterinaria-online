"""Pruebas del registro y el listado de mascotas.

`POST /pets` está reservada a las cuentas con rol `client` y valida la especie
(`dog`/`cat`/`other`) y la fecha de nacimiento (no futura). `GET /pets` solo
devuelve las mascotas de la cuenta autenticada. Cada prueba usa cuentas
propias para no depender del estado compartido por el resto de la suite.
"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Pet, User

PASSWORD = "secreto123"


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


def _headers(token: str) -> dict[str, str]:
    """Construye la cabecera `Authorization` de una cuenta."""
    return {"Authorization": f"Bearer {token}"}


def _count_pets(name: str) -> int:
    """Devuelve cuántas mascotas existen con el nombre indicado."""
    with SessionLocal() as session:
        return session.scalar(
            select(func.count()).select_from(Pet).where(Pet.name == name)
        )


def test_registro_de_un_perro_responde_201(
    client: TestClient, client_headers: dict[str, str], client_user: User
) -> None:
    """Un cliente registra un perro y la respuesta trae el propietario."""
    response = client.post(
        "/pets",
        json={"name": "Firu", "species": "dog", "birth_date": "2021-05-04"},
        headers=client_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "name", "species", "birth_date", "owner_id"}
    assert body["name"] == "Firu"
    assert body["species"] == "dog"
    assert body["birth_date"] == "2021-05-04"
    assert body["owner_id"] == client_user.id
    assert isinstance(body["id"], int)


def test_registro_de_un_gato_responde_201(
    client: TestClient, client_headers: dict[str, str]
) -> None:
    """Un cliente registra un gato y la respuesta trae la especie."""
    response = client.post(
        "/pets",
        json={"name": "Michi", "species": "cat", "birth_date": "2023-01-15"},
        headers=client_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Michi"
    assert body["species"] == "cat"
    assert body["birth_date"] == "2023-01-15"


def test_registro_de_una_mascota_de_otra_especie_responde_201(
    client: TestClient, client_headers: dict[str, str]
) -> None:
    """La especie `other` está admitida para cualquier otra mascota."""
    response = client.post(
        "/pets",
        json={"name": "Pepita", "species": "other", "birth_date": "2022-09-30"},
        headers=client_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["species"] == "other"
    assert body["birth_date"] == "2022-09-30"


def test_registro_con_especie_no_soportada_responde_422(
    client: TestClient, client_headers: dict[str, str]
) -> None:
    """Una especie fuera de `dog`/`cat`/`other` se rechaza y no crea la mascota."""
    response = client.post(
        "/pets",
        json={"name": "Ham", "species": "hamster", "birth_date": "2021-05-04"},
        headers=client_headers,
    )

    assert response.status_code == 422
    assert _count_pets("Ham") == 0


def test_registro_con_especie_en_mayusculas_responde_422(
    client: TestClient, client_headers: dict[str, str]
) -> None:
    """La especie distingue mayúsculas: `DOG` no es `dog`."""
    response = client.post(
        "/pets",
        json={"name": "Firu", "species": "DOG", "birth_date": "2021-05-04"},
        headers=client_headers,
    )

    assert response.status_code == 422


def test_registro_con_fecha_de_nacimiento_futura_responde_422(
    client: TestClient, client_headers: dict[str, str]
) -> None:
    """Una fecha de nacimiento posterior a hoy se rechaza."""
    response = client.post(
        "/pets",
        json={"name": "Futuro", "species": "dog", "birth_date": "2999-01-01"},
        headers=client_headers,
    )

    assert response.status_code == 422
    assert _count_pets("Futuro") == 0


def test_registro_con_fecha_de_nacimiento_de_hoy_responde_201(
    client: TestClient, client_headers: dict[str, str]
) -> None:
    """Una fecha de nacimiento igual a hoy se admite."""
    today = date.today().isoformat()

    response = client.post(
        "/pets",
        json={"name": "Hoy", "species": "dog", "birth_date": today},
        headers=client_headers,
    )

    assert response.status_code == 201
    assert response.json()["birth_date"] == today


def test_registro_sin_nombre_responde_422(
    client: TestClient, client_headers: dict[str, str]
) -> None:
    """Un payload sin `name` se rechaza por validación."""
    response = client.post(
        "/pets",
        json={"species": "dog", "birth_date": "2021-05-04"},
        headers=client_headers,
    )

    assert response.status_code == 422


def test_registro_con_fecha_de_nacimiento_mal_formada_responde_422(
    client: TestClient, client_headers: dict[str, str]
) -> None:
    """Una fecha que no sigue el formato `YYYY-MM-DD` se rechaza."""
    response = client.post(
        "/pets",
        json={"name": "Firu", "species": "dog", "birth_date": "04-05-2021"},
        headers=client_headers,
    )

    assert response.status_code == 422


def test_un_veterinario_no_puede_registrar_mascotas_responde_403(
    client: TestClient, vet_headers: dict[str, str]
) -> None:
    """Una cuenta con rol `vet` recibe 403 y no registra ninguna mascota."""
    response = client.post(
        "/pets",
        json={"name": "DelVet", "species": "dog", "birth_date": "2021-05-04"},
        headers=vet_headers,
    )

    assert response.status_code == 403
    assert _count_pets("DelVet") == 0


def test_listado_devuelve_solo_las_mascotas_del_cliente(
    client: TestClient, unique_email: str
) -> None:
    """Cada cliente ve sus mascotas y las del resto quedan ocultas."""
    owner_email = f"duenno-{unique_email}"
    other_email = f"vecino-{unique_email}"
    owner_id = _register(client, owner_email, "client")
    other_id = _register(client, other_email, "client")
    owner_headers = _headers(_login(client, owner_email))
    other_headers = _headers(_login(client, other_email))

    for name, species in (("Firu", "dog"), ("Michi", "cat")):
        created = client.post(
            "/pets",
            json={"name": name, "species": species, "birth_date": "2021-05-04"},
            headers=owner_headers,
        )
        assert created.status_code == 201
    foreign = client.post(
        "/pets",
        json={"name": "Pepita", "species": "other", "birth_date": "2022-09-30"},
        headers=other_headers,
    )
    assert foreign.status_code == 201

    response = client.get("/pets", headers=owner_headers)

    assert response.status_code == 200
    body = response.json()
    assert [pet["name"] for pet in body] == ["Firu", "Michi"]
    assert all(pet["owner_id"] == owner_id for pet in body)
    assert all(
        set(pet) == {"id", "name", "species", "birth_date", "owner_id"} for pet in body
    )
    assert "Pepita" not in [pet["name"] for pet in body]

    other_response = client.get("/pets", headers=other_headers)

    assert other_response.status_code == 200
    other_body = other_response.json()
    assert [pet["name"] for pet in other_body] == ["Pepita"]
    assert all(pet["owner_id"] == other_id for pet in other_body)


def test_un_veterinario_no_tiene_mascotas_en_su_listado(
    client: TestClient, vet_headers: dict[str, str]
) -> None:
    """El listado de un veterinario es una lista vacía."""
    response = client.get("/pets", headers=vet_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_listado_sin_token_responde_401(client: TestClient) -> None:
    """Sin cabecera `Authorization` el listado responde 401."""
    response = client.get("/pets")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_registro_sin_token_responde_401(client: TestClient) -> None:
    """Sin cabecera `Authorization` el alta de una mascota responde 401."""
    response = client.post(
        "/pets",
        json={"name": "Firu", "species": "dog", "birth_date": "2021-05-04"},
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"

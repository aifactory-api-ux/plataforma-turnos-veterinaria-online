"""Pruebas de la sonda de disponibilidad de la API."""

from fastapi.testclient import TestClient


def test_health_responde_ok_sin_credenciales(client: TestClient) -> None:
    """`GET /health` responde 200 con `{"status": "ok"}` sin cabecera de autorización."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ignora_un_token_bearer_invalido(client: TestClient) -> None:
    """Un token inválido no protege la sonda: la respuesta sigue siendo 200."""
    response = client.get(
        "/health", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_responde_ok_con_un_token_valido(
    client: TestClient, client_headers: dict[str, str]
) -> None:
    """Con un token válido la sonda responde el mismo cuerpo."""
    response = client.get("/health", headers=client_headers)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

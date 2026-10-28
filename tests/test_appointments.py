"""Pruebas de la agenda de turnos.

Comprueba el comportamiento HTTP de `POST /appointments`, `GET /appointments` y
`POST /appointments/{id}/cancel`. Las reglas de la franja horaria (duración de
30 minutos, inicio en punto o en y media, de lunes a sábado, entre las 09:00 y
las 17:30 UTC y nunca en el pasado) se verifican sobre las respuestas que
devuelve la API. Cada prueba registra sus propias cuentas para no depender del
estado compartido por el resto de la suite.
"""

from datetime import date, datetime, time, timedelta, timezone

from fastapi.testclient import TestClient

PASSWORD = "secreto123"

# Duración del turno que declara la clínica, comprobada sobre la respuesta.
SLOT_DURATION_MINUTES = 30

# Días de la semana usados por la agenda (0 es lunes).
MONDAY = 0
SATURDAY = 5
SUNDAY = 6


def _iso(moment: datetime) -> str:
    """Serializa un instante en UTC con el formato `YYYY-MM-DDTHH:MM:SSZ`."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _future_date(weekday: int) -> date:
    """Devuelve la próxima fecha futura que cae en ese día de la semana."""
    today = date.today()
    day = today + timedelta(days=(weekday - today.weekday()) % 7)
    if day <= today:
        day += timedelta(days=7)
    return day


def _slot(weekday: int, hour: int, minute: int = 0) -> str:
    """Devuelve la próxima fecha futura de ese día de la semana, a esa hora."""
    momento = datetime.combine(
        _future_date(weekday), time(hour, minute), tzinfo=timezone.utc
    )
    return _iso(momento)


def _end_of(slot: str) -> str:
    """Devuelve el final esperado de una franja, 30 minutos después."""
    inicio = datetime.strptime(slot, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    return _iso(inicio + timedelta(minutes=SLOT_DURATION_MINUTES))


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


def _new_account(
    client: TestClient, email: str, role: str
) -> tuple[int, dict[str, str]]:
    """Registra una cuenta, inicia sesión y devuelve su id y sus cabeceras."""
    account_id = _register(client, email, role)
    return account_id, _headers(_login(client, email))


def _new_pet(client: TestClient, headers: dict[str, str], name: str) -> int:
    """Registra una mascota a nombre de la cuenta y devuelve su id."""
    response = client.post(
        "/pets",
        json={"name": name, "species": "dog", "birth_date": "2021-05-04"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _book(
    client: TestClient,
    headers: dict[str, str],
    pet_id: int,
    vet_id: int,
    start_at: str,
):
    """Intenta reservar una franja y devuelve la respuesta del endpoint."""
    return client.post(
        "/appointments",
        json={"pet_id": pet_id, "vet_id": vet_id, "start_at": start_at},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Reglas de la franja horaria, comprobadas sobre la respuesta de la API
# ---------------------------------------------------------------------------


def test_la_duracion_del_turno_es_de_30_minutos(
    client: TestClient, unique_email: str
) -> None:
    """El turno creado termina 30 minutos después de su inicio."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")
    inicio = _slot(MONDAY, 10, 0)

    response = _book(client, client_headers, pet_id, vet_id, inicio)

    assert response.status_code == 201
    body = response.json()
    assert body["start_at"] == inicio
    assert body["end_at"] == _end_of(inicio)


def test_la_ventana_horaria_se_abre_a_las_09_00(
    client: TestClient, unique_email: str
) -> None:
    """El primer inicio admitido de la mañana es a las 09:00."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")

    response = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 9, 0))

    assert response.status_code == 201
    assert response.json()["start_at"] == _slot(MONDAY, 9, 0)


def test_los_turnos_empiezan_en_punto_o_en_y_media(
    client: TestClient, unique_email: str
) -> None:
    """Un inicio en punto y un inicio en y media se admiten ambos."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")

    en_punto = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 14, 0))
    en_y_media = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 14, 30))

    assert en_punto.status_code == 201
    assert en_punto.json()["start_at"] == _slot(MONDAY, 14, 0)
    assert en_y_media.status_code == 201
    assert en_y_media.json()["start_at"] == _slot(MONDAY, 14, 30)


def test_la_clinica_atiende_de_lunes_a_sabado(
    client: TestClient, unique_email: str
) -> None:
    """Un inicio de lunes se admite en la respuesta de la API."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")

    response = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 10, 0))

    assert response.status_code == 201


def test_una_marca_sin_zona_se_interpreta_en_utc(
    client: TestClient, unique_email: str
) -> None:
    """Una marca de tiempo sin zona se trata como UTC en la respuesta."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")
    inicio = f"{_future_date(MONDAY).isoformat()}T10:00:00"

    response = _book(client, client_headers, pet_id, vet_id, inicio)

    assert response.status_code == 201
    body = response.json()
    assert body["start_at"] == f"{_future_date(MONDAY).isoformat()}T10:00:00Z"
    assert body["end_at"] == f"{_future_date(MONDAY).isoformat()}T10:30:00Z"


def test_una_marca_con_desfase_se_normaliza_a_utc(
    client: TestClient, unique_email: str
) -> None:
    """Un inicio con desfase de dos horas equivale a las 10:00 UTC."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")
    inicio = f"{_future_date(MONDAY).isoformat()}T12:00:00+02:00"

    response = _book(client, client_headers, pet_id, vet_id, inicio)

    assert response.status_code == 201
    body = response.json()
    assert body["start_at"] == f"{_future_date(MONDAY).isoformat()}T10:00:00Z"
    assert body["end_at"] == f"{_future_date(MONDAY).isoformat()}T10:30:00Z"


# ---------------------------------------------------------------------------
# Reserva de turnos
# ---------------------------------------------------------------------------


def test_reserva_de_un_turno_para_una_mascota_propia_responde_201(
    client: TestClient, unique_email: str
) -> None:
    """Un cliente reserva una franja para su mascota y recibe el turno creado."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")
    inicio = _slot(MONDAY, 10, 0)

    response = _book(client, client_headers, pet_id, vet_id, inicio)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "pet_id", "vet_id", "start_at", "end_at", "status"}
    assert isinstance(body["id"], int)
    assert body["pet_id"] == pet_id
    assert body["vet_id"] == vet_id
    assert body["start_at"] == inicio
    assert body["end_at"] == _end_of(inicio)
    assert body["status"] == "scheduled"


def test_reserva_de_un_turno_a_las_10_30_responde_201(
    client: TestClient, unique_email: str
) -> None:
    """Un inicio en y media es válido y el turno termina una hora después."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Michi")
    inicio = _slot(MONDAY, 10, 30)

    response = _book(client, client_headers, pet_id, vet_id, inicio)

    assert response.status_code == 201
    body = response.json()
    assert body["start_at"] == inicio
    assert body["end_at"] == _end_of(inicio)
    assert body["status"] == "scheduled"


def test_un_veterinario_no_puede_reservar_turnos_responde_403(
    client: TestClient, unique_email: str
) -> None:
    """Una cuenta con rol `vet` recibe 403 y no crea ningún turno."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, vet_headers = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Pepita")

    response = _book(client, vet_headers, pet_id, vet_id, _slot(MONDAY, 10, 0))

    assert response.status_code == 403


def test_reserva_de_una_mascota_ajena_responde_403(
    client: TestClient, unique_email: str
) -> None:
    """Un cliente no puede reservar un turno para la mascota de otro."""
    _, vecino_headers = _new_account(client, f"vecino-{unique_email}", "client")
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, vecino_headers, "Firu")

    response = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 10, 0))

    assert response.status_code == 403


def test_reserva_con_una_mascota_inexistente_responde_404(
    client: TestClient, unique_email: str
) -> None:
    """Una mascota que no existe se responde con 404."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")

    response = _book(client, client_headers, 999999, vet_id, _slot(MONDAY, 10, 0))

    assert response.status_code == 404


def test_reserva_con_un_veterinario_inexistente_responde_404(
    client: TestClient, unique_email: str
) -> None:
    """Un veterinario que no existe se responde con 404."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    pet_id = _new_pet(client, client_headers, "Firu")

    response = _book(client, client_headers, pet_id, 999999, _slot(MONDAY, 10, 0))

    assert response.status_code == 404


def test_reserva_con_el_identificador_de_un_cliente_responde_404(
    client: TestClient, unique_email: str
) -> None:
    """El identificador de una cuenta de cliente no es un veterinario."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    cliente_id, _ = _new_account(client, f"otro-cliente-{unique_email}", "client")
    pet_id = _new_pet(client, client_headers, "Firu")

    response = _book(client, client_headers, pet_id, cliente_id, _slot(MONDAY, 10, 0))

    assert response.status_code == 404


def test_reserva_con_minuto_15_responde_422(
    client: TestClient, unique_email: str
) -> None:
    """Un inicio en el minuto 15 no es una franja válida."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")

    response = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 10, 15))

    assert response.status_code == 422


def test_reserva_con_minuto_45_responde_422(
    client: TestClient, unique_email: str
) -> None:
    """Un inicio en el minuto 45 tampoco es una franja válida."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")

    response = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 10, 45))

    assert response.status_code == 422


def test_reserva_en_domingo_responde_422(
    client: TestClient, unique_email: str
) -> None:
    """La clínica no agenda turnos los domingos."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")

    response = _book(client, client_headers, pet_id, vet_id, _slot(SUNDAY, 10, 0))

    assert response.status_code == 422


def test_reserva_en_sabado_responde_201(
    client: TestClient, unique_email: str
) -> None:
    """El sábado es un día de agenda."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")

    response = _book(client, client_headers, pet_id, vet_id, _slot(SATURDAY, 10, 0))

    assert response.status_code == 201


def test_reserva_a_las_08_30_responde_422(
    client: TestClient, unique_email: str
) -> None:
    """Antes de las 09:00 la agenda está cerrada."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")

    response = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 8, 30))

    assert response.status_code == 422


def test_reserva_a_las_18_00_responde_422(
    client: TestClient, unique_email: str
) -> None:
    """A las 18:00 la agenda está cerrada."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")

    response = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 18, 0))

    assert response.status_code == 422


def test_reserva_a_las_17_30_responde_201(
    client: TestClient, unique_email: str
) -> None:
    """El último inicio admitido es a las 17:30 y el turno termina a las 18:00."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")
    inicio = _slot(MONDAY, 17, 30)

    response = _book(client, client_headers, pet_id, vet_id, inicio)

    assert response.status_code == 201
    body = response.json()
    assert body["start_at"] == inicio
    assert body["end_at"] == _end_of(inicio)
    assert body["end_at"].endswith("T18:00:00Z")


def test_reserva_de_una_fecha_pasada_responde_422(
    client: TestClient, unique_email: str
) -> None:
    """No se pueden reservar turnos en el pasado."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")

    response = _book(
        client, client_headers, pet_id, vet_id, "2020-01-01T10:00:00Z"
    )

    assert response.status_code == 422


def test_doble_reserva_del_mismo_veterinario_responde_409(
    client: TestClient, unique_email: str
) -> None:
    """Un veterinario no puede tener dos turnos activos en la misma franja."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")
    inicio = _slot(MONDAY, 10, 0)

    primera = _book(client, client_headers, pet_id, vet_id, inicio)
    assert primera.status_code == 201

    segunda = _book(client, client_headers, pet_id, vet_id, inicio)

    assert segunda.status_code == 409


def test_doble_reserva_del_mismo_veterinario_con_otra_mascota_responde_409(
    client: TestClient, unique_email: str
) -> None:
    """El conflicto se detecta también cuando la mascota es diferente."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    primera_pet = _new_pet(client, client_headers, "Firu")
    segunda_pet = _new_pet(client, client_headers, "Michi")
    inicio = _slot(MONDAY, 10, 0)

    primera = _book(client, client_headers, primera_pet, vet_id, inicio)
    assert primera.status_code == 201

    segunda = _book(client, client_headers, segunda_pet, vet_id, inicio)

    assert segunda.status_code == 409


def test_otro_veterinario_puede_reservar_la_misma_franja_responde_201(
    client: TestClient, unique_email: str
) -> None:
    """La franja ocupada por un veterinario sigue libre para otro."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    primer_vet, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    segundo_vet, _ = _new_account(
        client, f"segundo-veterinario-{unique_email}", "vet"
    )
    pet_id = _new_pet(client, client_headers, "Firu")
    inicio = _slot(MONDAY, 10, 0)

    primera = _book(client, client_headers, pet_id, primer_vet, inicio)
    assert primera.status_code == 201

    segunda = _book(client, client_headers, pet_id, segundo_vet, inicio)

    assert segunda.status_code == 201
    assert segunda.json()["vet_id"] == segundo_vet


def test_reserva_sin_token_responde_401(client: TestClient) -> None:
    """Sin cabecera `Authorization` la reserva responde 401."""
    response = client.post(
        "/appointments",
        json={"pet_id": 1, "vet_id": 2, "start_at": _slot(MONDAY, 10, 0)},
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


# ---------------------------------------------------------------------------
# Listado de turnos
# ---------------------------------------------------------------------------


def test_listado_de_turnos_del_cliente_muestra_solo_sus_mascotas(
    client: TestClient, unique_email: str
) -> None:
    """El cliente ve los turnos de sus mascotas y no los de los demás."""
    _, duenno_headers = _new_account(client, f"duenno-{unique_email}", "client")
    _, vecino_headers = _new_account(client, f"vecino-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, duenno_headers, "Firu")
    pet_ajena = _new_pet(client, vecino_headers, "Michi")

    propia = _book(client, duenno_headers, pet_id, vet_id, _slot(MONDAY, 10, 0))
    assert propia.status_code == 201
    ajena = _book(client, vecino_headers, pet_ajena, vet_id, _slot(MONDAY, 11, 0))
    assert ajena.status_code == 201

    response = client.get("/appointments", headers=duenno_headers)

    assert response.status_code == 200
    body = response.json()
    assert [turno["id"] for turno in body] == [propia.json()["id"]]
    assert all(turno["pet_id"] == pet_id for turno in body)
    assert all(
        set(turno) == {"id", "pet_id", "vet_id", "start_at", "end_at", "status"}
        for turno in body
    )


def test_listado_de_turnos_del_veterinario_muestra_sus_turnos(
    client: TestClient, unique_email: str
) -> None:
    """El veterinario ve los turnos que tiene asignados y solo ellos."""
    _, duenno_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, vet_headers = _new_account(client, f"veterinario-{unique_email}", "vet")
    otro_vet, _ = _new_account(client, f"otro-veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, duenno_headers, "Firu")

    primera = _book(client, duenno_headers, pet_id, vet_id, _slot(MONDAY, 10, 0))
    assert primera.status_code == 201
    segunda = _book(client, duenno_headers, pet_id, vet_id, _slot(MONDAY, 11, 0))
    assert segunda.status_code == 201
    ajena = _book(client, duenno_headers, pet_id, otro_vet, _slot(MONDAY, 12, 0))
    assert ajena.status_code == 201

    response = client.get("/appointments", headers=vet_headers)

    assert response.status_code == 200
    body = response.json()
    assert [turno["id"] for turno in body] == [
        primera.json()["id"],
        segunda.json()["id"],
    ]
    assert all(turno["vet_id"] == vet_id for turno in body)


def test_listado_de_turnos_sin_token_responde_401(client: TestClient) -> None:
    """Sin cabecera `Authorization` el listado responde 401."""
    response = client.get("/appointments")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


# ---------------------------------------------------------------------------
# Cancelación de turnos
# ---------------------------------------------------------------------------


def test_cancelacion_por_el_dueno_responde_200(
    client: TestClient, unique_email: str
) -> None:
    """El dueño de la mascota cancela el turno y la respuesta lo refleja."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")
    creada = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 10, 0))
    assert creada.status_code == 201
    appointment_id = creada.json()["id"]

    response = client.post(
        f"/appointments/{appointment_id}/cancel", headers=client_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == appointment_id
    assert body["status"] == "cancelled"
    assert body["pet_id"] == pet_id
    assert body["vet_id"] == vet_id


def test_cancelacion_por_el_veterinario_asignado_responde_200(
    client: TestClient, unique_email: str
) -> None:
    """El veterinario asignado también puede cancelar el turno."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, vet_headers = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")
    creada = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 10, 0))
    assert creada.status_code == 201
    appointment_id = creada.json()["id"]

    response = client.post(
        f"/appointments/{appointment_id}/cancel", headers=vet_headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancelacion_por_un_cliente_no_relacionado_responde_403(
    client: TestClient, unique_email: str
) -> None:
    """Un cliente ajeno no puede cancelar el turno y este sigue agendado."""
    _, duenno_headers = _new_account(client, f"duenno-{unique_email}", "client")
    _, vecino_headers = _new_account(client, f"vecino-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, duenno_headers, "Firu")
    creada = _book(client, duenno_headers, pet_id, vet_id, _slot(MONDAY, 10, 0))
    assert creada.status_code == 201
    appointment_id = creada.json()["id"]

    response = client.post(
        f"/appointments/{appointment_id}/cancel", headers=vecino_headers
    )

    assert response.status_code == 403
    listado = client.get("/appointments", headers=duenno_headers)
    assert listado.json()[0]["status"] == "scheduled"


def test_cancelacion_por_un_veterinario_no_asignado_responde_403(
    client: TestClient, unique_email: str
) -> None:
    """Un veterinario que no tiene asignado el turno no puede cancelarlo."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    _, otro_vet_headers = _new_account(
        client, f"otro-veterinario-{unique_email}", "vet"
    )
    pet_id = _new_pet(client, client_headers, "Firu")
    creada = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 10, 0))
    assert creada.status_code == 201
    appointment_id = creada.json()["id"]

    response = client.post(
        f"/appointments/{appointment_id}/cancel", headers=otro_vet_headers
    )

    assert response.status_code == 403


def test_cancelacion_de_un_turno_inexistente_responde_404(
    client: TestClient, unique_email: str
) -> None:
    """Un identificador de turno que no existe se responde con 404."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")

    response = client.post("/appointments/999999/cancel", headers=client_headers)

    assert response.status_code == 404


def test_segunda_cancelacion_del_mismo_turno_responde_409(
    client: TestClient, unique_email: str
) -> None:
    """Un turno ya cancelado no se puede volver a cancelar."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")
    creada = _book(client, client_headers, pet_id, vet_id, _slot(MONDAY, 10, 0))
    assert creada.status_code == 201
    appointment_id = creada.json()["id"]

    primera = client.post(
        f"/appointments/{appointment_id}/cancel", headers=client_headers
    )
    assert primera.status_code == 200

    segunda = client.post(
        f"/appointments/{appointment_id}/cancel", headers=client_headers
    )

    assert segunda.status_code == 409
    listado = client.get("/appointments", headers=client_headers)
    assert [turno["status"] for turno in listado.json()] == ["cancelled"]


def test_reserva_de_una_franja_cancelada_responde_201(
    client: TestClient, unique_email: str
) -> None:
    """Cancelar un turno libera su franja para volver a reservarla."""
    _, client_headers = _new_account(client, f"duenno-{unique_email}", "client")
    vet_id, _ = _new_account(client, f"veterinario-{unique_email}", "vet")
    pet_id = _new_pet(client, client_headers, "Firu")
    inicio = _slot(MONDAY, 10, 0)
    creada = _book(client, client_headers, pet_id, vet_id, inicio)
    assert creada.status_code == 201

    cancelacion = client.post(
        f"/appointments/{creada.json()['id']}/cancel", headers=client_headers
    )
    assert cancelacion.status_code == 200

    nueva = _book(client, client_headers, pet_id, vet_id, inicio)

    assert nueva.status_code == 201
    assert nueva.json()["status"] == "scheduled"
    assert nueva.json()["id"] != creada.json()["id"]

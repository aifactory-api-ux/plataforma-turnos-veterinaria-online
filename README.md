# API de turnos — Clínica veterinaria

Backend REST de la clínica veterinaria. Permite dar de alta cuentas de
**clientes** y **veterinarios**, registrar las mascotas de cada cliente y
agendar, listar y cancelar turnos de 30 minutos con un veterinario.

- **API:** FastAPI (Python 3.11+)
- **Base de datos:** PostgreSQL 16 (SQLAlchemy 2)
- **Autenticación:** JWT (PyJWT) con cabecera `Authorization: Bearer`
- **Contenedores:** `Dockerfile` + `docker-compose.yml` en la raíz del repositorio

La API es de uso interno del equipo de la clínica.

---

## Índice

1. [Requisitos](#requisitos)
2. [Variables de entorno](#variables-de-entorno)
3. [Levantar la plataforma](#levantar-la-plataforma)
4. [Documentación interactiva](#documentación-interactiva)
5. [Ejemplos con curl](#ejemplos-con-curl)
6. [Reglas de la agenda](#reglas-de-la-agenda)
7. [Errores de la API](#errores-de-la-api)
8. [Pruebas](#pruebas)
9. [Estructura del proyecto](#estructura-del-proyecto)

---

## Requisitos

### Con Docker (recomendado)

- Docker Engine 24 o superior.
- Docker Compose v2 (`docker compose`).
- El puerto `8000` libre en el host.

No hace falta instalar PostgreSQL ni Python: la pila levanta ambos.

### Sin Docker (entorno local)

- Python 3.11 o superior.
- PostgreSQL 14 o superior accesible, o un servidor PostgreSQL local.
- `pip` y un entorno virtual.

---

## Variables de entorno

La configuración se lee del entorno o del archivo `.env` de la raíz. Copia
`.env.example` a `.env` y ajusta los valores si necesitas cambiar los
valores por defecto:

```bash
cp .env.example .env
```

| Variable | Valor por defecto | Descripción |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://vet:vet@db:5432/vetclinic` | Cadena de conexión a PostgreSQL. El valor por defecto apunta al servicio `db` de `docker-compose.yml`. |
| `JWT_SECRET` | `change-me-in-production` | Secreto con el que se firman los tokens de acceso. **Cámbialo antes de usar la API fuera del entorno de pruebas.** |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma de los tokens JWT. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | Vigencia del token de acceso, en minutos. |

> El esquema de la base de datos (`users`, `pets`, `appointments`) se crea
> automáticamente al arrancar la aplicación.

---

## Levantar la plataforma

### Opción 1 — Pila de contenedores (PostgreSQL + API)

Levanta PostgreSQL y la API a la vez. La API queda disponible en el puerto
`8000` del host:

```bash
docker compose up --build
```

Detalles de la pila:

- El servicio `db` usa la imagen `postgres:16-alpine` con las credenciales
  `vet` / `vet` y la base de datos `vetclinic`; guarda los datos en el
  volumen `pgdata` y expone un healthcheck con `pg_isready`.
- El servicio `api` se construye desde el `Dockerfile` de la raíz, espera a
  que la base de datos esté sana (`depends_on` con `condition:
  service_healthy`), recibe `DATABASE_URL` con la dirección de PostgreSQL y
  publica el puerto `8000:8000`.

Comprobación de que la API está en pie:

```bash
curl http://localhost:8000/health
```

Para detener la pila:

```bash
docker compose down        # conserva el volumen de datos
docker compose down -v     # elimina también el volumen `pgdata`
```

### Opción 2 — Ejecución local

Instala las dependencias en un entorno virtual y arranca el servidor ASGI
con recarga automática:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

export DATABASE_URL="postgresql+psycopg://vet:vet@localhost:5432/vetclinic"
export JWT_SECRET="change-me-in-production"

uvicorn app.main:app --reload
```

La API queda disponible en `http://localhost:8000`.

### Opción 3 — Atajo con `run.sh`

El script `run.sh` de la raíz del repositorio resume las operaciones habituales
del equipo. Crea el entorno virtual `.venv` e instala las dependencias si
hacen falta:

```bash
./run.sh install   # prepara el entorno virtual
./run.sh api       # levanta la API en local con uvicorn (puerto 8000)
./run.sh stack     # levanta la pila de contenedores (PostgreSQL + API)
./run.sh tests     # ejecuta la suite de pruebas
./run.sh help      # muestra la ayuda del script
```

`./run.sh api` respeta `DATABASE_URL` y `JWT_SECRET` del entorno o del archivo
`.env`. Si `DATABASE_URL` no está definida, usa una base SQLite local en
`.data/vetclinic.db` para que la API arranque sin ningún servidor adicional.

---

## Documentación interactiva

Con la aplicación en marcha:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- Esquema OpenAPI: <http://localhost:8000/openapi.json>

---

## Ejemplos con curl

Todos los ejemplos apuntan a `http://localhost:8000`. Salvo `GET /health`,
`POST /auth/register` y `POST /auth/login`, **todas las rutas exigen la
cabecera `Authorization: Bearer <token>`**.

Para extraer valores de las respuestas se usa `python`, que ya forma parte
del proyecto:

```bash
export API="http://localhost:8000"
```

### 1. `GET /health` — comprobación de disponibilidad

Ruta pública: no necesita token.

```bash
curl -s "$API/health"
```

```json
{"status":"ok"}
```

### 2. `POST /auth/register` — alta de cuenta

Ruta pública. `role` admite `"client"` o `"vet"` y la contraseña debe tener
al menos 8 caracteres.

```bash
curl -s -X POST "$API/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"ana@example.com","password":"secreto123","role":"client"}'
```

```json
{"id":1,"email":"ana@example.com","role":"client"}
```

Alta de un veterinario (el mismo cuerpo con `"role":"vet"`):

```bash
curl -s -X POST "$API/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"dra.solaris@example.com","password":"veterinaria1","role":"vet"}'
```

```json
{"id":2,"email":"dra.solaris@example.com","role":"vet"}
```

### 3. `POST /auth/login` — inicio de sesión

Ruta pública. Devuelve el token de acceso y su tipo de transporte.

```bash
curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"ana@example.com","password":"secreto123"}'
```

```json
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","token_type":"bearer"}
```

Guarda el token para las siguientes llamadas:

```bash
TOKEN=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"ana@example.com","password":"secreto123"}' \
  | python -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
```

### 4. `GET /vets` — directorio de veterinarios

Ruta protegida. Devuelve un objeto `{id, email}` por cada cuenta con rol
`vet`.

```bash
curl -s "$API/vets" \
  -H "Authorization: Bearer $TOKEN"
```

```json
[{"id":2,"email":"dra.solaris@example.com"}]
```

### 5. `POST /pets` — alta de mascota

Ruta protegida y **exclusiva de clientes** (un veterinario recibe `403`).
`species` admite `"dog"`, `"cat"` u `"other"` y `birth_date` no puede estar
en el futuro.

```bash
curl -s -X POST "$API/pets" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Firu","species":"dog","birth_date":"2021-05-04"}'
```

```json
{"id":1,"name":"Firu","species":"dog","birth_date":"2021-05-04","owner_id":1}
```

Guarda el identificador de la mascota para usarla en los turnos:

```bash
PET_ID=$(curl -s -X POST "$API/pets" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Michi","species":"cat","birth_date":"2023-01-15"}' \
  | python -c "import json,sys; print(json.load(sys.stdin)['id'])")
```

### 6. `GET /pets` — listado de mascotas

Ruta protegida. Solo devuelve las mascotas del cliente autenticado; un
veterinario obtiene `[]`.

```bash
curl -s "$API/pets" \
  -H "Authorization: Bearer $TOKEN"
```

```json
[{"id":1,"name":"Firu","species":"dog","birth_date":"2021-05-04","owner_id":1}]
```

### 7. `POST /appointments` — reserva de turno

Ruta protegida y **exclusiva de clientes**, y solo sobre mascotas propias.
`start_at` es una marca de tiempo ISO 8601 en UTC. La duración del turno es
de 30 minutos.

```bash
curl -s -X POST "$API/appointments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"pet_id":1,"vet_id":2,"start_at":"2030-06-10T10:00:00Z"}'
```

```json
{"id":1,"pet_id":1,"vet_id":2,"start_at":"2030-06-10T10:00:00Z","end_at":"2030-06-10T10:30:00Z","status":"scheduled"}
```

Un turno que empieza en y media:

```bash
curl -s -X POST "$API/appointments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"pet_id":1,"vet_id":2,"start_at":"2030-06-10T10:30:00Z"}'
```

```json
{"id":2,"pet_id":1,"vet_id":2,"start_at":"2030-06-10T10:30:00Z","end_at":"2030-06-10T11:00:00Z","status":"scheduled"}
```

### 8. `GET /appointments` — listado de turnos

Ruta protegida. Un cliente ve los turnos de sus mascotas y un veterinario
los turnos que tiene asignados.

```bash
curl -s "$API/appointments" \
  -H "Authorization: Bearer $TOKEN"
```

```json
[{"id":1,"pet_id":1,"vet_id":2,"start_at":"2030-06-10T10:00:00Z","end_at":"2030-06-10T10:30:00Z","status":"scheduled"}]
```

### 9. `POST /appointments/{id}/cancel` — cancelación de un turno

Ruta protegida. Puede cancelar el cliente dueño de la mascota o el
veterinario asignado al turno; cualquier otra cuenta recibe `403`. El turno
cancelado queda con `"status":"cancelled"` y su franja vuelve a estar
disponible.

```bash
curl -s -X POST "$API/appointments/1/cancel" \
  -H "Authorization: Bearer $TOKEN"
```

```json
{"id":1,"pet_id":1,"vet_id":2,"start_at":"2030-06-10T10:00:00Z","end_at":"2030-06-10T10:30:00Z","status":"cancelled"}
```

---

## Reglas de la agenda

Los turnos que devuelve `POST /appointments` cumplen siempre estas reglas:

| Regla | Valor |
| --- | --- |
| Duración | 30 minutos (`end_at` = `start_at` + 30 minutos) |
| Minuto de inicio | `00` o `30` |
| Días | De lunes a sábado (el domingo no se atiende) |
| Ventana horaria (UTC) | Inicio entre las `09:00` y las `17:30` (el último turno termina a las `18:00`) |
| Momento | No se admiten turnos en el pasado |
| Conflicto | Un veterinario no puede tener dos turnos activos en la misma franja (`409`) |

Las marcas de tiempo se devuelven siempre en UTC con el sufijo `Z`.

---

## Errores de la API

Los errores de negocio y de autorización responden con `{"detail": "..."}`.
Los errores de validación del cuerpo responden con `422` y el detalle de
FastAPI (`{"detail":[{"loc":[...],"msg":"...","type":"..."}]}`).

| Código | Cuándo ocurre | Ejemplo de respuesta |
| --- | --- | --- |
| `401 Unauthorized` | Faltan las credenciales, la cabecera no es `Bearer`, el token es inválido o ha expirado, o las credenciales del inicio de sesión no coinciden. | `{"detail":"Credenciales ausentes o inválidas"}` |
| `403 Forbidden` | La cuenta autenticada no tiene permisos: un veterinario intenta registrar una mascota o reservar un turno, se reserva el turno de una mascota ajena, o se cancela un turno ajeno. | `{"detail":"La cuenta no tiene permisos para esta operación"}` |
| `404 Not Found` | La referencia no existe: mascota, veterinario, o turno inexistente. | `{"detail":"La mascota no existe"}` |
| `409 Conflict` | El correo ya está registrado, el veterinario ya tiene un turno activo en esa franja, o el turno que se quiere cancelar ya estaba cancelado. | `{"detail":"El veterinario ya tiene un turno en ese horario"}` |
| `422 Unprocessable Content` | El cuerpo no cumple las reglas de validación: contraseña de menos de 8 caracteres, `role` distinto de `client`/`vet`, `species` distinta de `dog`/`cat`/`other`, `birth_date` futura o con formato inválido, `start_at` en el pasado, con un minuto distinto de `00`/`30`, en domingo o fuera de la ventana horaria. | `{"detail":[{"type":"string_too_short","loc":["body","password"],"msg":"String should have at least 8 characters"}]}` |

Las rutas `/health`, `/auth/register` y `/auth/login` son públicas; el resto
responde `401` si no recibe una cabecera `Authorization: Bearer <token>`
válida.

---

## Pruebas

La suite usa `pytest` y se ejecuta desde la raíz del repositorio. Si no hay
ninguna variable `DATABASE_URL` definida, las pruebas usan una base de datos
SQLite temporal, de modo que **no hacen falta Docker ni PostgreSQL**:

```bash
pytest -q
```

Para ejecutar la suite contra un PostgreSQL concreto:

```bash
DATABASE_URL="postgresql+psycopg://vet:vet@localhost:5432/vetclinic" pytest -q
```

La imagen del contenedor incluye las dependencias de desarrollo y la suite,
así que también puede ejecutarse dentro del contenedor:

```bash
docker compose exec api pytest -q
```

Con el atajo del repositorio, que prepara el entorno virtual antes de
ejecutar la suite:

```bash
./run.sh tests
```

---

## Estructura del proyecto

```text
.
├── app/
│   ├── config.py           # ajustes leídos del entorno o de `.env`
│   ├── database.py         # engine, sesión y tipos de columna
│   ├── dependencies.py     # autenticación y autorización por rol
│   ├── main.py             # aplicación FastAPI y creación del esquema
│   ├── models.py           # modelos ORM `User`, `Pet`, `Appointment`
│   ├── routers/            # una ruta por capacidad
│   │   ├── appointments.py
│   │   ├── auth.py
│   │   ├── health.py
│   │   ├── pets.py
│   │   └── vets.py
│   ├── schemas.py          # esquemas de entrada y salida (Pydantic)
│   ├── security.py         # hash de contraseñas y tokens JWT
│   └── services/
│       └── scheduling.py   # reglas puras de las franjas horarias
├── tests/                  # suite de pruebas con pytest
├── Dockerfile              # imagen de la API
├── docker-compose.yml      # pila API + PostgreSQL
├── run.sh                  # atajos de arranque y de pruebas
├── requirements.txt        # dependencias de ejecución
├── requirements-dev.txt    # dependencias de desarrollo y pruebas
├── .env.example            # variables de entorno con sus valores por defecto
└── README.md
```

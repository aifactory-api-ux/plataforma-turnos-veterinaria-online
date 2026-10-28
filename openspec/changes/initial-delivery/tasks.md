# Tasks

Team: the Developer agent implements and writes the tests of every group (no QA or DevSec in this delivery). No task may run `docker build` or `docker compose up` — the delivery environment has no Docker daemon, so the container files are verified statically.

## 1. Project scaffolding and dependencies

- [x] 1.1 Create `requirements.txt` (fastapi, uvicorn[standard], sqlalchemy>=2.0, psycopg[binary], pydantic>=2, pydantic-settings, pyjwt, bcrypt, email-validator) and `requirements-dev.txt` (pytest, httpx, pyyaml) and verify that `pip install -r requirements.txt -r requirements-dev.txt` succeeds in the project virtualenv
- [x] 1.2 Create the `app/` package skeleton (`app/__init__.py`, `app/config.py` with the `DATABASE_URL`/`JWT_SECRET`/`JWT_ALGORITHM`/`ACCESS_TOKEN_EXPIRE_MINUTES` settings, `app/database.py` with the engine, `SessionLocal`, `Base` and the `UTCDateTime` type, `app/models.py` with `User`/`Pet`/`Appointment`, `app/schemas.py`, `app/security.py`, `app/dependencies.py`, `app/routers/__init__.py`, `app/services/__init__.py`, `app/main.py` creating the FastAPI app and the tables on startup) and verify that `python -c "from app.main import app"` succeeds and that `python -c "from app.config import settings; print(settings.database_url)"` prints the configured URL
- [x] 1.3 Create `tests/__init__.py` and `tests/conftest.py` (temporary SQLite `DATABASE_URL` set before importing `app.*`, schema creation, `TestClient` fixture, helper fixtures for a registered client, a registered vet and their bearer tokens) and verify that `pytest` collects the suite without collection errors
- [x] 1.4 Create `.env.example` (the four variables with their default values) and `.dockerignore` (excluding `.venv`, `__pycache__`, `.git`, `.env`) and verify that `.env.example` names every variable read by `app/config.py`

## 2. Health probe

- [x] 2.1 Implement `app/routers/health.py` with `GET /health` returning `{"status": "ok"}` and include the router in `app/main.py`, and verify that a request to `/health` answers HTTP 200 with the body `{"status": "ok"}` and that it needs no `Authorization` header
- [x] 2.2 Add `tests/test_health.py` asserting HTTP 200 and the body `{"status": "ok"}` without credentials, and HTTP 200 with the same body when an invalid bearer token is sent, and verify that `pytest tests/test_health.py` passes

## 3. Authentication and authorization

- [x] 3.1 Implement the request/response schemas of `app/schemas.py` (`RegisterRequest` with `password` of at least 8 characters and `role` limited to `client`/`vet`, `LoginRequest`, `UserOut` with `id`/`email`/`role`, `TokenOut` with `access_token`/`token_type`) and verify that a payload with the role `admin` or a 7-character password raises a validation error
- [x] 3.2 Implement `app/security.py` (bcrypt password hashing/verification and PyJWT token creation/verification carrying `sub`, `role`, `iat`, `exp`) and `app/dependencies.py` (`get_current_user` answering HTTP 401 with `WWW-Authenticate: Bearer` for a missing header, a non-Bearer scheme, a malformed token, a token signed with another secret and an expired token) and verify that a token signed with a wrong secret is rejected
- [x] 3.3 Implement `app/routers/auth.py` (`POST /auth/register` answering 201 with `{"id", "email", "role"}`, 409 for a duplicate email and 422 for an invalid payload; `POST /auth/login` answering 200 with `{"access_token", "token_type": "bearer"}` and 401 for wrong credentials) and include the router in `app/main.py`, and verify the behaviors with the tests added in task 3.4
- [x] 3.4 Add `tests/test_auth.py` covering: registration of a client (201) and of a vet (201), duplicate email (409), password of 7 characters (422), role `admin` (422), login with valid credentials (200 and `token_type` `bearer`), wrong password (401), unknown email (401), protected endpoint without header (401), with a malformed header (401), with an invalid token (401) and with an expired token (401), and verify that `pytest tests/test_auth.py` passes

## 4. Veterinarian directory

- [x] 4.1 Implement `GET /vets` in `app/routers/vets.py` returning the accounts with role `vet` as `{"id", "email"}` objects and include the router in `app/main.py`, and verify the behaviors with the tests added in task 4.2
- [x] 4.2 Add `tests/test_vets.py` covering: a valid token returns only the veterinarians (no client account in the list), an empty list when no vet exists, HTTP 401 without a token and HTTP 401 with an invalid token, and verify that `pytest tests/test_vets.py` passes

## 5. Pets

- [x] 5.1 Implement `POST /pets` and `GET /pets` in `app/routers/pets.py` (`POST` answering 201 with `{"id", "name", "species", "birth_date", "owner_id"}`, HTTP 403 for a vet, HTTP 422 for a species other than `dog`/`cat`/`other` and for a future `birth_date`; `GET` returning only the pets owned by the authenticated account) and include the router in `app/main.py`, and verify the behaviors with the tests added in task 5.2
- [x] 5.2 Add `tests/test_pets.py` covering: registering a dog, a cat and a pet with species `other` (201 each), a species `hamster` (422), a species `DOG` (422), a future `birth_date` (422), today's `birth_date` (201), a missing `name` (422), a malformed `birth_date` (422), a vet registering a pet (403), the owner-scoped listing (own pets only, pets of another client hidden, a vet gets `[]`) and HTTP 401 without a token, and verify that `pytest tests/test_pets.py` passes

## 6. Appointment scheduling

- [x] 6.1 Implement `app/services/scheduling.py` with the pure slot rules (`SLOT_MINUTES = 30`, opening 09:00, last start 17:30, Monday–Saturday, minute in {0, 30}, no past instant, `slot_end` returning start + 30 minutes) and verify them with the slot-rule unit tests added in task 6.4
- [x] 6.2 Implement `POST /appointments` in `app/routers/appointments.py` following the check order of the design (403 role, 404 pet, 404 vet, 403 foreign pet, 422 slot, 409 conflict) and answering 201 with `{"id", "pet_id", "vet_id", "start_at", "end_at", "status": "scheduled"}`, and verify the behaviors with the tests added in task 6.4
- [x] 6.3 Implement `GET /appointments` (client sees the appointments of their own pets, vet sees the appointments assigned to them) and `POST /appointments/{id}/cancel` (404 unknown id, 403 unrelated user, 409 already cancelled, 200 with `status` `cancelled`) in `app/routers/appointments.py`, and verify the behaviors with the tests added in task 6.4
- [x] 6.4 Add `tests/test_appointments.py` covering the slot-rule unit cases and the endpoint cases: booking an own pet (201 with `end_at` = start + 30 minutes and `status` `scheduled`), a start at `:30`, a vet booking (403), a foreign pet (403), an unknown pet (404), an unknown vet (404), a `vet_id` of a client account (404), a start at 10:15 and at 10:45 (422), a Sunday (422), a Saturday (201), a start at 08:30 (422), a start at 18:00 (422), a start at 17:30 (201 with `end_at` 18:00), a past date (422), a double booking of the same vet with the same and with another pet (409), the same slot with another vet (201), the client-scoped and vet-scoped listings, cancellation by the owner and by the assigned vet (200 with `status` `cancelled`), cancellation by an unrelated user (403), cancellation of an unknown id (404), a second cancellation (409) and the rebooking of a cancelled slot (201), and verify that `pytest tests/test_appointments.py` passes

## 7. Container delivery

- [x] 7.1 Create the root `Dockerfile` (`python:3.11-slim` base, `WORKDIR /app`, installation of `requirements.txt` and `requirements-dev.txt`, `COPY app`, `COPY tests`, `EXPOSE 8000`, `CMD uvicorn app.main:app --host 0.0.0.0 --port 8000`) and verify that every `COPY` source of the file exists in the repository root and that the default command starts the application module
- [x] 7.2 Create the root `docker-compose.yml` with a `db` service (`postgres:16-alpine`, `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`, the `pgdata` volume and a `pg_isready` healthcheck) and an `api` service (`build.context: .`, `build.dockerfile: Dockerfile`, `DATABASE_URL=postgresql+psycopg://vet:vet@db:5432/vetclinic`, `depends_on: db` with `condition: service_healthy`, `ports: "8000:8000"`) and verify with a YAML parse (`python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"`) that the file parses and that the services, the build context, the dependency and the published port are the expected ones — without running any `docker` command
- [x] 7.3 Run the static verification of the container files: a command that extracts the `COPY` sources of the `Dockerfile` and asserts each of them exists in the repository root, plus a re-parse of `docker-compose.yml`, and verify both checks pass without a Docker daemon; keep these checks out of the pytest suite

## 8. Documentation and final verification

- [x] 8.1 Write the root `README.md` in Spanish with: the requirements, the environment variables and their defaults, `docker compose up --build` to raise the API on port 8000 with PostgreSQL, the local run with `uvicorn app.main:app --reload`, a curl example per endpoint (`GET /health`, `POST /auth/register`, `POST /auth/login`, `GET /vets`, `POST /pets`, `GET /pets`, `POST /appointments`, `GET /appointments`, `POST /appointments/{id}/cancel`) including the `Authorization: Bearer` header on the protected calls, and the table of error responses (401, 403, 404, 409, 422); verify by re-reading the file that every route of the API has a curl example and that the payloads and field names match the implemented schemas
- [x] 8.2 Run `pytest -q` from the repository root and verify that the whole suite passes, and run a local smoke check of the server started in the background (`uvicorn app.main:app --port 8000 & PID=$!` … `kill $PID`, stopping only that PID, never `pkill`/`killall`, never port 8202) verifying that `GET /health` answers HTTP 200 with `{"status": "ok"}`

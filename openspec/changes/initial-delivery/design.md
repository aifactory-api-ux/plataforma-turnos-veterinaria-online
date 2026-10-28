# Design

## Context

Empty repository: the project starts from zero, so every file listed below is created by this change. See `proposal.md` for the motivation and `specs/` for the behaviors to implement.

Constraints that shape the approach:

- The delivery environment has **no Docker daemon**. Container artifacts must therefore be verifiable by static inspection only (`docker-compose.yml` parses as YAML, every `COPY` source of the `Dockerfile` exists in the repository). No task may run `docker build` or `docker compose up`.
- The target runtime is **FastAPI + PostgreSQL**, while the test suite must run on a machine without a PostgreSQL server and without Docker. The database connection is therefore resolved from an environment variable that the test fixtures override.
- Internal tool only: no public signup funnel, no frontend, no third-party identity provider.
- Process safety when a server is started for a manual smoke check: run it in the background, keep its PID (`$!`) and stop only that PID (never `pkill`/`killall`); the API uses port `8000` (port `8202` is off limits).

## Goals / Non-Goals

**Goals:**

- One small FastAPI application package (`app/`) with a router per capability, a SQLAlchemy data layer and a pytest suite under `tests/`.
- A single source of truth for the slot rules (30-minute length, `:00`/`:30` starts, Monday–Saturday, 09:00–17:30 window, no past slots, no double booking) implemented in one pure module (`app/services/scheduling.py`) so it can be unit-tested in isolation and reused by the router.
- Reproducible container delivery: root `Dockerfile` + root `docker-compose.yml` (API + PostgreSQL) and a README with curl examples.
- A deterministic rule for *which* error wins when a request violates several rules at once, so the API answers are predictable and testable.

**Non-Goals:**

- No frontend, no admin panel, no email/SMS notifications, no payment handling, no analytics.
- No authentication provider beyond this API's own JWT, no refresh tokens, no password reset, no role other than `client` and `vet`.
- No migration tool (Alembic): for this first delivery the schema is created at startup from the SQLAlchemy metadata.
- No availability/search endpoint beyond the ones specified (`GET /vets`, `GET /appointments`), no recurring appointments, no appointment rescheduling (cancellation + new booking covers it).
- No multi-tenant clinic model and no per-appointment notes.

## Decisions

### 1. Layered single-package layout with one router per capability

Exact files to create:

```
/README.md
/Dockerfile
/docker-compose.yml
/requirements.txt
/requirements-dev.txt
/.env.example
/.dockerignore
/app/__init__.py
/app/main.py
/app/config.py
/app/database.py
/app/models.py
/app/schemas.py
/app/security.py
/app/dependencies.py
/app/routers/__init__.py
/app/routers/health.py
/app/routers/auth.py
/app/routers/vets.py
/app/routers/pets.py
/app/routers/appointments.py
/app/services/__init__.py
/app/services/scheduling.py
/tests/__init__.py
/tests/conftest.py
/tests/test_health.py
/tests/test_auth.py
/tests/test_vets.py
/tests/test_pets.py
/tests/test_appointments.py
```

`app/main.py` builds the FastAPI instance and includes the routers (`app/routers/health.py` → `/health`, `app/routers/auth.py` → `/auth`, `app/routers/vets.py` → `/vets`, `app/routers/pets.py` → `/pets`, `app/routers/appointments.py` → `/appointments`). `app/config.py` holds the settings, `app/database.py` the engine/session/metadata, `app/models.py` the ORM models, `app/schemas.py` the Pydantic request/response models, `app/security.py` the password hashing and JWT helpers, `app/dependencies.py` the authentication dependencies, `app/services/scheduling.py` the slot rules.

*Alternative considered*: a single `app/main.py` with everything inline. Rejected because the rule "each task group lands its own tests" maps cleanly onto one router module + one test module per capability, and because the slot rules deserve an isolated pure module.

### 2. Configuration through environment variables, PostgreSQL in production and SQLite in tests

`app/config.py` uses `pydantic-settings` with:

| Variable | Default | Used by |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://vet:vet@db:5432/vetclinic` | `app/database.py` engine URL (SQLAlchemy 2 URL syntax) |
| `JWT_SECRET` | `change-me-in-production` | `app/security.py` token signing |
| `JWT_ALGORITHM` | `HS256` | `app/security.py` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | `app/security.py` token expiry |

`app/database.py` exposes `engine`, `SessionLocal` and `Base`; the routers get their session through a `get_db` dependency, which the tests override.

`tests/conftest.py` sets `DATABASE_URL` to a temporary SQLite file **before** importing `app.*` (the settings are read at import time), creates the schema with `Base.metadata.create_all()` and yields a `TestClient` bound to the application. The application code never assumes PostgreSQL-specific features (no `ARRAY`, no `JSONB`, no server-side defaults), so the same code paths run on both engines.

*Alternative considered*: requiring a local PostgreSQL for the tests. Rejected: the delivery environment has neither a PostgreSQL server nor a Docker daemon, so the suite would be unrunnable. The `DATABASE_URL` override keeps PostgreSQL as the delivered runtime while remaining testable.

### 3. Data model

`app/models.py` (SQLAlchemy 2 declarative, `Mapped`/`mapped_column`):

- `User`: `id` (PK, autoincrement), `email` (`String(320)`, unique, indexed), `password_hash` (`String(255)`), `role` (`String(16)`, `"client"`/`"vet"`), `created_at`.
- `Pet`: `id` (PK), `name` (`String(120)`), `species` (`String(16)`, `"dog"`/`"cat"`/`"other"`), `birth_date` (`Date`), `owner_id` (FK `users.id`, indexed), `created_at`.
- `Appointment`: `id` (PK), `pet_id` (FK `pets.id`, indexed), `vet_id` (FK `users.id`, indexed), `start_at` (UTC `DateTime`), `end_at` (UTC `DateTime`), `status` (`String(16)`, `"scheduled"`/`"cancelled"`), `created_at`.

`start_at`/`end_at` use a `TypeDecorator` (`UTCDateTime` in `app/database.py`) that normalizes to UTC on write and re-attaches `tzinfo=UTC` on read, so PostgreSQL and SQLite both return timezone-aware UTC values and the API always serializes `...Z` timestamps.

Uniqueness of the slot is enforced in the service layer (query `vet_id` + `start_at` + `status == "scheduled"`), not with a partial unique index, because SQLite does not support partial indexes. The check-and-insert runs inside the same request/transaction, which is sufficient for the single-instance deployment of this internal tool.

*Alternative considered*: a PostgreSQL partial unique index `(vet_id, start_at) WHERE status = 'scheduled'`. Rejected for portability with the SQLite test database; the trade-off is documented in Risks.

### 4. Authentication: manual bearer parsing that always answers 401

`app/dependencies.py` exposes `get_current_user`, which reads the `Authorization` header, requires the `Bearer` scheme, decodes the JWT with `app/security.py` and loads the user from the database, raising `HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})` in every failure mode: missing header, wrong scheme, malformed token, bad signature, expired token, unknown subject.

*Alternative considered*: FastAPI's `HTTPBearer(auto_error=True)` dependency. **Rejected**: it answers **403** for a missing/invalid header, while the specification requires **401**. The dependency is therefore hand-written (or uses `HTTPBearer(auto_error=False)` plus an explicit check) so the status code is always 401.

`app/security.py` uses `bcrypt` directly (`hashpw`/`checkpw`) instead of `passlib`, because `passlib` is unmaintained and breaks with recent `bcrypt` releases; the raw `bcrypt` API is two functions and needs no wrapper library. Tokens are signed with `PyJWT` (`HS256`) and carry `sub` (user id), `role`, `iat` and `exp`; `token_type` is always the literal `"bearer"`.

`app/schemas.py` validates the payloads with Pydantic v2 so that the invalid-input cases become 422 responses instead of manual `if` chains:

- `RegisterRequest`: `email: EmailStr`, `password: str` with `min_length=8`, `role: Literal["client", "vet"]` → short password, unknown role and missing fields are 422.
- `LoginRequest`: `email: EmailStr`, `password: str`.
- `PetCreate`: `name: str` (`min_length=1`), `species: Literal["dog", "cat", "other"]`, `birth_date: date`.
- `AppointmentCreate`: `pet_id: int`, `vet_id: int`, `start_at: datetime`.

Duplicate emails are detected by querying first and answering 409 (the unique constraint remains the safety net).

### 5. Slot rules live in one pure module

`app/services/scheduling.py` exposes pure functions with no database access:

- `SLOT_MINUTES = 30`, `OPENING_TIME = time(9, 0)`, `LAST_START_TIME = time(17, 30)`, `BOOKABLE_WEEKDAYS = {0, 1, 2, 3, 4, 5}` (Monday–Saturday).
- `validate_slot(start_at: datetime, now: datetime) -> None` raising `SlotValidationError` when: the instant is in the past, the minute is not `00`/`30`, the weekday is Sunday, or the UTC time is outside `09:00`–`17:30`.
- `slot_end(start_at: datetime) -> datetime` returning `start_at + 30 minutes`.

`app/routers/appointments.py` converts the error into HTTP 422. `start_at` is parsed as ISO 8601 by Pydantic, converted to UTC when it carries an offset, and treated as UTC when it carries none; the response always renders UTC `Z` timestamps.

### 6. Deterministic order of checks (error precedence)

When a request violates several rules, the API answers with the first failure in this order, so the status codes are stable and testable:

| Order | Check | Status |
|---|---|---|
| 1 | Caller role is `client` | 403 |
| 2 | `pet_id` exists | 404 |
| 3 | `vet_id` exists and has role `vet` | 404 |
| 4 | Pet belongs to the caller | 403 |
| 5 | Slot window (past, minute, weekday, hours) | 422 |
| 6 | The vet has an active appointment in that slot | 409 |

For `POST /appointments/{id}/cancel`: unknown id → 404, caller is neither the pet owner nor the assigned vet → 403, appointment already `cancelled` → 409, otherwise 200 with the cancelled appointment.

### 7. Listing scoping

`GET /pets` filters by `owner_id == current_user.id` (a vet owns no pet, so the answer is `[]`). `GET /appointments` filters by role: a client gets the appointments of the pets it owns (join through `pets`), a vet gets the appointments whose `vet_id` is its own id.

### 8. Containerization: one image, two services

`/Dockerfile` (root): `python:3.11-slim` base, `WORKDIR /app`, installs `requirements.txt` **and** `requirements-dev.txt` (so the suite can run inside the image), copies `app/` and `tests/`, exposes `8000` and runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Every `COPY` source (`requirements.txt`, `requirements-dev.txt`, `app`, `tests`) exists in the repository root.

`/docker-compose.yml` (root): a `db` service (`postgres:16-alpine`, user/password/database `vet`/`vet`/`vetclinic`, named volume `pgdata`, `pg_isready` healthcheck) and an `api` service built from the root `Dockerfile` (`build.context: .`, `build.dockerfile: Dockerfile`) with `DATABASE_URL=postgresql+psycopg://vet:vet@db:5432/vetclinic`, `depends_on: db (condition: service_healthy)` and the port mapping `"8000:8000"`.

The API is a server, so the container runs the API; the image additionally ships the test suite so `pytest` can be executed inside it.

*Alternative considered*: running PostgreSQL only as an external service. Rejected: the delivery must be reproducible with a single `docker compose up`, so the database travels with the stack.

### 9. Static verification of the container files (no Docker daemon)

The container artifacts are checked without Docker by:

1. parsing `/docker-compose.yml` with a YAML parser and asserting the `api` and `db` services, the `build.dockerfile` reference, the `DATABASE_URL` wiring, the `depends_on` relation and the published port;
2. resolving every `COPY` source of `/Dockerfile` against the repository root and asserting the path exists.

These checks are run as one-off commands by the developer during the delivery; they are **not** pytest tests (a test that reads `Dockerfile`/`docker-compose.yml` would prove nothing inside the container). The pytest suite only asserts on HTTP behavior.

### 10. README in Spanish

`/README.md` is written in Spanish (the language of the clinic team): how to raise the stack with `docker compose up --build`, how to run the API locally (`uvicorn app.main:app --reload`), the environment variables with their defaults, a curl example per endpoint (including the `Authorization: Bearer` header on the protected calls) and the table of error responses (401, 403, 404, 409, 422).

## Risks / Trade-offs

- **[No Docker daemon in the delivery environment]** → The container files are verified statically (YAML parse + `COPY` sources) and the suite runs on SQLite; `docker build` / `docker compose up` are not part of any task, so the image is validated by inspection only.
- **[SQLite in tests vs PostgreSQL in production]** → The application code avoids engine-specific features and normalizes datetimes with `UTCDateTime`, but a dialect-specific bug would not be caught by the suite → the compose stack is documented in the README for the team to validate manually before the first internal use.
- **[Race between two simultaneous bookings of the same slot]** → The check-and-insert is not atomic across concurrent requests → for a single-instance internal deployment this is acceptable; a unique index on `(vet_id, start_at)` filtered by `status = 'scheduled'` would be the hardening step if the API ever runs with multiple workers.
- **[Table creation at startup instead of migrations]** → Schema changes will need an explicit migration story later → the models are kept minimal and centralised in `app/models.py` to keep that migration cheap.
- **[Tokens signed with a default secret]** → `JWT_SECRET` has a development default → the README and `.env.example` state that the secret must be changed, and `docker-compose.yml` allows overriding it through the environment.
- **[`bcrypt` truncates passwords beyond 72 bytes]** → A password longer than 72 bytes is silently truncated → the registration schema rejects passwords longer than 72 characters to avoid two different passwords collapsing into the same hash.

## Migration Plan

First delivery, no data to migrate: the schema (`users`, `pets`, `appointments`) is created on application startup. Deployment for the clinic team is `docker compose up --build` on the internal host, which starts PostgreSQL and the API on port `8000`; `GET /health` confirms readiness. Rollback is removing the compose stack (`docker compose down -v` also drops the `pgdata` volume); no application data needs to be preserved during the internal pilot.

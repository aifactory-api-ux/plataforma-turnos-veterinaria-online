# Proposal

## Why

The clinic has no system at all to register its clients, keep track of the pets they own, or book and cancel veterinary appointments, so every booking is handled by hand over the phone and the same vet can end up double-booked. The internal team needs a single backend that exposes those workflows over HTTP so the clinic staff can stop doing manual coordination and so appointment slots are guaranteed to be unique per veterinarian.

## What Changes

- Add a FastAPI REST API backed by PostgreSQL that serves the whole booking flow: health probe, account registration/login, veterinarian directory, pet registry and appointment scheduling.
- Add JWT bearer authentication: `POST /auth/register` (roles `client`/`vet`), `POST /auth/login` (JWT access token, `token_type: "bearer"`), and mandatory `Authorization: Bearer` on every endpoint except `/health`, `/auth/register` and `/auth/login`.
- Add pet registration restricted to clients, with `species` restricted to `dog`/`cat`/`other` and `birth_date` restricted to non-future dates, plus owner-scoped listing of pets.
- Add appointment scheduling restricted to clients and to their own pets: 30-minute slots that start on the hour or half hour, Monday through Saturday, with a last start at 17:30, duplicate-slot protection per veterinarian (HTTP 409), owner/vet-scoped listing and cancellation that frees the slot again.
- Add a root `Dockerfile` and a root `docker-compose.yml` that build and run the project (API service plus PostgreSQL service) so the delivery is containerized and reproducible.
- Add a pytest suite that exercises the HTTP behaviors of every endpoint, and a README that documents how to run the stack and shows curl examples for each endpoint.

## Capabilities

### New Capabilities

- `service-health`: Public liveness probe of the API (`GET /health`).
- `user-auth`: Account registration, login issuing JWT access tokens, and bearer-token enforcement on protected endpoints.
- `vet-directory`: Listing of the veterinarians a client or another vet can book an appointment with.
- `pet-management`: Registration of pets owned by a client and owner-scoped listing of pets.
- `appointment-scheduling`: Creation, listing and cancellation of 30-minute veterinary appointments with slot-window and conflict rules.
- `container-delivery`: Root `Dockerfile` and `docker-compose.yml` that build and run the project, verifiable statically without a Docker daemon.
- `automated-testing`: pytest suite that exercises the HTTP API behaviors and runs without a Docker daemon.
- `api-documentation`: README with run instructions and curl examples for every endpoint.

### Modified Capabilities

None. This is the first delivery of the project, so there are no existing capabilities whose requirements change.

## Impact

- New Python package (`app/`) with the FastAPI application, SQLAlchemy models, Pydantic schemas, JWT/password security helpers and routers for health, auth, vets, pets and appointments.
- New PostgreSQL database with tables for users, pets and appointments, created on application startup for this delivery.
- New dependencies: FastAPI, Uvicorn, SQLAlchemy, Pydantic settings, PyJWT (or python-jose), password hashing library, PostgreSQL driver; pytest and HTTPX for the test suite.
- New root-level delivery files: `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `requirements-dev.txt`, `.env.example`, `README.md`.
- New test package (`tests/`) with a shared fixture set and one test module per capability.
- No frontend, no authentication provider outside this API, no external services other than the PostgreSQL instance started by docker-compose.


<!-- specs/api-documentation/spec.md -->
# Spec Delta

## Purpose

README of the project for the internal clinic team, explaining how to raise the platform and how to call every endpoint with curl.

## ADDED Requirements

### Requirement: The README explains how to run the project
The repository SHALL contain a `README.md` at its root describing how to raise the platform with the container stack, how to run the API locally, and which environment variables the service needs.

#### Scenario: The README is at the repository root
- **WHEN** the repository root is inspected
- **THEN** a file named `README.md` exists at the root of the repository

#### Scenario: The README documents the environment variables
- **WHEN** the content of the `README.md` is inspected
- **THEN** it names the `DATABASE_URL` environment variable and the secret used to sign the access tokens, and states the default values

#### Scenario: The README documents the run commands
- **WHEN** the content of the `README.md` is inspected
- **THEN** it contains the command that raises the API with the container stack and the command that starts the API locally with an ASGI server

### Requirement: The README shows curl examples for every endpoint
The `README.md` SHALL contain a curl example for each endpoint of the API, covering the health probe, registration, login, the veterinarian directory, pet registration, pet listing, appointment booking, appointment listing and appointment cancellation.

#### Scenario: A curl example per endpoint
- **WHEN** the content of the `README.md` is inspected
- **THEN** it contains at least one curl command for each of `GET /health`, `POST /auth/register`, `POST /auth/login`, `GET /vets`, `POST /pets`, `GET /pets`, `POST /appointments`, `GET /appointments` and `POST /appointments/{id}/cancel`

#### Scenario: The examples carry the authentication header
- **WHEN** the curl examples that call protected endpoints are inspected
- **THEN** they include the `Authorization: Bearer <token>` header

#### Scenario: The examples show the expected errors
- **WHEN** the content of the `README.md` is inspected
- **THEN** it documents the error responses of the API, including the HTTP 401, 403, 404, 409 and 422 cases


<!-- specs/appointment-scheduling/spec.md -->
# Spec Delta

## Purpose

Booking, listing and cancellation of the 30-minute veterinary appointments, including the slot window the clinic accepts, the ownership rules that restrict who may book and who may cancel, and the conflict protection that keeps a veterinarian from being double-booked.

## ADDED Requirements

### Requirement: A client books an appointment for one of their pets
The API SHALL expose `POST /appointments` behind bearer authentication and SHALL accept the JSON body `{"pet_id": <id>, "vet_id": <id>, "start_at": "YYYY-MM-DDTHH:MM:SSZ"}` from an account with role `"client"`, answering with HTTP 201 and the JSON body `{"id": <id>, "pet_id": <pet_id>, "vet_id": <vet_id>, "start_at": <start_at>, "end_at": <end_at>, "status": "scheduled"}` where `end_at` is `start_at` plus 30 minutes.

#### Scenario: Book a slot with an own pet
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <id of a registered vet>, "start_at": "2030-06-10T10:00:00Z"}`, where `2030-06-10` is a Monday
- **THEN** the API responds with HTTP 201 and the JSON body `{"id": <id>, "pet_id": <pet of the client>, "vet_id": <vet>, "start_at": "2030-06-10T10:00:00Z", "end_at": "2030-06-10T10:30:00Z", "status": "scheduled"}`

#### Scenario: Book a slot that starts at half past
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <id of a registered vet>, "start_at": "2030-06-10T10:30:00Z"}`
- **THEN** the API responds with HTTP 201 and the appointment has `start_at` `"2030-06-10T10:30:00Z"` and `end_at` `"2030-06-10T11:00:00Z"`

### Requirement: Only clients may book appointments
The API SHALL answer HTTP 403 when `POST /appointments` is requested by an account whose role is `"vet"`.

#### Scenario: A vet tries to book an appointment
- **WHEN** a user with role `"vet"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id>, "vet_id": <id of a vet>, "start_at": "2030-06-10T10:00:00Z"}`
- **THEN** the API responds with HTTP 403 and no appointment is created

### Requirement: An appointment can only be booked for a pet of the caller
The API SHALL answer HTTP 403 when `POST /appointments` references a pet that exists but is owned by a different account.

#### Scenario: Booking a pet of another client
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of a pet owned by another client>, "vet_id": <id of a registered vet>, "start_at": "2030-06-10T10:00:00Z"}`
- **THEN** the API responds with HTTP 403 and no appointment is created

### Requirement: Unknown pets and unknown veterinarians are reported as not found
The API SHALL answer HTTP 404 when `POST /appointments` references a `pet_id` that does not exist, or a `vet_id` that does not exist or does not belong to an account with role `"vet"`.

#### Scenario: Unknown pet id
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": 999999, "vet_id": <id of a registered vet>, "start_at": "2030-06-10T10:00:00Z"}`
- **THEN** the API responds with HTTP 404 and no appointment is created

#### Scenario: Unknown vet id
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": 999999, "start_at": "2030-06-10T10:00:00Z"}`
- **THEN** the API responds with HTTP 404 and no appointment is created

#### Scenario: Vet id that belongs to a client account
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <id of an account with role "client">, "start_at": "2030-06-10T10:00:00Z"}`
- **THEN** the API responds with HTTP 404 and no appointment is created

### Requirement: Appointments start on the hour or on the half hour
The API SHALL answer HTTP 422 when the minute of `start_at` is neither `00` nor `30`.

#### Scenario: Minute 15 is rejected
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <id of a registered vet>, "start_at": "2030-06-10T10:15:00Z"}`
- **THEN** the API responds with HTTP 422 and no appointment is created

#### Scenario: Minute 45 is rejected
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <id of a registered vet>, "start_at": "2030-06-10T10:45:00Z"}`
- **THEN** the API responds with HTTP 422 and no appointment is created

### Requirement: Appointments are only booked from Monday to Saturday
The API SHALL answer HTTP 422 when the weekday of `start_at` is Sunday.

#### Scenario: Sunday is rejected
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <id of a registered vet>, "start_at": "2030-06-09T10:00:00Z"}`, where `2030-06-09` is a Sunday
- **THEN** the API responds with HTTP 422 and no appointment is created

#### Scenario: Saturday is accepted
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <id of a registered vet>, "start_at": "2030-06-08T10:00:00Z"}`, where `2030-06-08` is a Saturday
- **THEN** the API responds with HTTP 201

### Requirement: Appointments start between 09:00 and 17:30 UTC
The API SHALL answer HTTP 422 when `start_at` is earlier than 09:00 UTC or later than 17:30 UTC, and SHALL accept a start at 17:30 UTC whose end falls exactly at 18:00 UTC.

#### Scenario: Start before 09:00 is rejected
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <id of a registered vet>, "start_at": "2030-06-10T08:30:00Z"}`
- **THEN** the API responds with HTTP 422 and no appointment is created

#### Scenario: Start at 18:00 is rejected
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <id of a registered vet>, "start_at": "2030-06-10T18:00:00Z"}`
- **THEN** the API responds with HTTP 422 and no appointment is created

#### Scenario: Last accepted start is 17:30
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <id of a registered vet>, "start_at": "2030-06-10T17:30:00Z"}`
- **THEN** the API responds with HTTP 201 and the appointment has `end_at` `"2030-06-10T18:00:00Z"`

### Requirement: Appointments cannot be booked in the past
The API SHALL answer HTTP 422 when `start_at` is earlier than the moment of the request.

#### Scenario: A past date is rejected
- **WHEN** a client with role `"client"` sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <id of a registered vet>, "start_at": "2020-01-01T10:00:00Z"}`
- **THEN** the API responds with HTTP 422 and no appointment is created

### Requirement: A veterinarian cannot hold two active appointments in the same slot
The API SHALL answer HTTP 409 when the veterinarian of the request already has an appointment that is not cancelled for the same `start_at`.

#### Scenario: The same slot is already taken by the same vet
- **WHEN** the veterinarian `<vet>` already has an appointment with `start_at` `"2030-06-10T10:00:00Z"` and a client sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <vet>, "start_at": "2030-06-10T10:00:00Z"}`
- **THEN** the API responds with HTTP 409 and no second appointment is created

#### Scenario: The conflict is detected for a different pet of the same vet
- **WHEN** the veterinarian `<vet>` already has an appointment for one pet with `start_at` `"2030-06-10T10:00:00Z"` and a client sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of another own pet>, "vet_id": <vet>, "start_at": "2030-06-10T10:00:00Z"}`
- **THEN** the API responds with HTTP 409 and no second appointment is created

#### Scenario: Another veterinarian can take the same slot
- **WHEN** the veterinarian `<vet A>` already has an appointment with `start_at` `"2030-06-10T10:00:00Z"` and a client sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <id of vet B>, "start_at": "2030-06-10T10:00:00Z"}`
- **THEN** the API responds with HTTP 201

### Requirement: Listing appointments is scoped by role
The API SHALL expose `GET /appointments` behind bearer authentication and SHALL answer with HTTP 200 and a JSON array of appointment objects `{"id": <id>, "pet_id": <pet_id>, "vet_id": <vet_id>, "start_at": <start_at>, "end_at": <end_at>, "status": <status>}` containing only the appointments the caller is entitled to see.

#### Scenario: A client sees the appointments of their own pets
- **WHEN** a client with role `"client"` sends `GET /appointments` with the header `Authorization: Bearer <jwt>` and owns the pet used in one appointment while another client owns the pet used in another appointment
- **THEN** the API responds with HTTP 200 and the JSON array contains the appointment of the own pet and excludes the appointment of the pet of the other client

#### Scenario: A vet sees the appointments assigned to them
- **WHEN** a user with role `"vet"` sends `GET /appointments` with the header `Authorization: Bearer <jwt>` and has appointments booked with them
- **THEN** the API responds with HTTP 200 and the JSON array contains exactly the appointments whose `vet_id` is the identifier of that veterinarian

#### Scenario: Listing appointments requires a token
- **WHEN** a client sends `GET /appointments` with no `Authorization` header
- **THEN** the API responds with HTTP 401

### Requirement: The owner of the pet or the veterinarian of the slot may cancel an appointment
The API SHALL expose `POST /appointments/{id}/cancel` behind bearer authentication and SHALL answer with HTTP 200 and the JSON body of the appointment `{"id": <id>, "pet_id": <pet_id>, "vet_id": <vet_id>, "start_at": <start_at>, "end_at": <end_at>, "status": "cancelled"}` when the caller is the client who owns the pet or the veterinarian assigned to the appointment.

#### Scenario: The owner client cancels
- **WHEN** a client with role `"client"` who owns the pet sends `POST /appointments/<id>/cancel` with the header `Authorization: Bearer <jwt>` for an appointment with status `"scheduled"`
- **THEN** the API responds with HTTP 200 and the JSON body `{"id": <id>, "pet_id": <pet_id>, "vet_id": <vet_id>, "start_at": <start_at>, "end_at": <end_at>, "status": "cancelled"}`

#### Scenario: The veterinarian of the slot cancels
- **WHEN** the veterinarian assigned to an appointment sends `POST /appointments/<id>/cancel` with the header `Authorization: Bearer <jwt>` for an appointment with status `"scheduled"`
- **THEN** the API responds with HTTP 200 and the JSON body of the appointment with `"status": "cancelled"`

#### Scenario: An unrelated user cannot cancel
- **WHEN** a client who does not own the pet of the appointment, or a veterinarian who is not assigned to it, sends `POST /appointments/<id>/cancel` with the header `Authorization: Bearer <jwt>`
- **THEN** the API responds with HTTP 403 and the appointment keeps its previous status

#### Scenario: An unknown appointment cannot be cancelled
- **WHEN** a client sends `POST /appointments/999999/cancel` with the header `Authorization: Bearer <jwt>`
- **THEN** the API responds with HTTP 404

### Requirement: An appointment cannot be cancelled twice
The API SHALL answer HTTP 409 when `POST /appointments/{id}/cancel` is requested for an appointment whose status is already `"cancelled"`.

#### Scenario: Cancelling an already cancelled appointment
- **WHEN** an appointment already has the status `"cancelled"` and its owner sends `POST /appointments/<id>/cancel` with the header `Authorization: Bearer <jwt>`
- **THEN** the API responds with HTTP 409 and the appointment keeps the status `"cancelled"`

### Requirement: A cancelled slot becomes bookable again
The API SHALL allow a new appointment on a slot whose previous appointment was cancelled, and SHALL report HTTP 409 only for slots that hold an appointment whose status is not `"cancelled"`.

#### Scenario: Booking a slot that was cancelled before
- **WHEN** the veterinarian `<vet>` had an appointment with `start_at` `"2030-06-10T10:00:00Z"` that was cancelled and a client sends `POST /appointments` with the header `Authorization: Bearer <jwt>` and the body `{"pet_id": <id of an own pet>, "vet_id": <vet>, "start_at": "2030-06-10T10:00:00Z"}`
- **THEN** the API responds with HTTP 201 and the new appointment has the status `"scheduled"`



<!-- specs/automated-testing/spec.md -->
# Spec Delta

## Purpose

Automated regression coverage of the API behaviors through a pytest suite that runs locally and inside the container image without requiring a Docker daemon.

## ADDED Requirements

### Requirement: The project ships a pytest suite
The repository SHALL contain a pytest test suite that exercises the HTTP behaviors of the API and SHALL be runnable with `pytest` from the root of the repository.

#### Scenario: The suite is executed from the repository root
- **WHEN** `pytest` is executed from the root of the repository
- **THEN** the suite is collected and every test passes without errors

#### Scenario: The suite lives in the repository
- **WHEN** the repository root is inspected
- **THEN** a test package exists containing at least one test module per group of API endpoints (health, authentication, veterinarians, pets and appointments)

### Requirement: The suite covers every endpoint of the API
The suite SHALL contain tests for the health probe, for registration and login, for the veterinarian directory, for pet registration and listing, and for the creation, listing and cancellation of appointments.

#### Scenario: Health probe is covered
- **WHEN** the test suite is inspected
- **THEN** it contains a test that requests `GET /health` and asserts the HTTP 200 response and the body `{"status": "ok"}`

#### Scenario: Authentication is covered
- **WHEN** the test suite is inspected
- **THEN** it contains tests that assert the HTTP 201 of a registration, the HTTP 409 of a duplicate email, the HTTP 422 of a short password and of an invalid role, the HTTP 200 of a login with its `token_type` `"bearer"`, the HTTP 401 of wrong credentials and the HTTP 401 of a protected endpoint without or with an invalid token

#### Scenario: Pets are covered
- **WHEN** the test suite is inspected
- **THEN** it contains tests that assert the HTTP 201 of a pet registration, the HTTP 422 of an unsupported species and of a future birth date, the HTTP 403 of a vet registering a pet and the owner scoping of the pet listing

#### Scenario: Appointments are covered
- **WHEN** the test suite is inspected
- **THEN** it contains tests that assert the HTTP 201 of a booking with its `end_at` and `status`, the HTTP 422 of an invalid slot window, the HTTP 409 of a double booking, the HTTP 403 of a foreign pet or of a user without rights, the HTTP 200 of a cancellation and the HTTP 409 of a second cancellation

### Requirement: The suite runs without a Docker daemon
The suite SHALL obtain its database from the `DATABASE_URL` environment variable and SHALL fall back to a temporary SQLite database managed by the test fixtures when the variable is not set, so that `pytest` runs in an environment where no Docker daemon is available.

#### Scenario: Running the suite without a Docker daemon
- **WHEN** `pytest` is executed in an environment with no Docker daemon and no `DATABASE_URL` set
- **THEN** the suite runs against a temporary SQLite database and passes

#### Scenario: Running the suite against PostgreSQL
- **WHEN** `DATABASE_URL` points to a PostgreSQL database and `pytest` is executed
- **THEN** the suite runs against that PostgreSQL database and passes

### Requirement: The tests assert on behavior, not on project files
The tests SHALL assert only on the responses returned by the API and SHALL NOT read or assert on `Dockerfile`, `docker-compose.yml`, `README.md` or any other project file.

#### Scenario: A test reads no project file
- **WHEN** the test suite is inspected
- **THEN** no test reads, parses or asserts on the content of `Dockerfile`, `docker-compose.yml`, `README.md` or the dependency manifests


<!-- specs/container-delivery/spec.md -->
# Spec Delta

## Purpose

Containerized delivery of the veterinary clinic API: a root `Dockerfile` that builds the image and a root `docker-compose.yml` that runs the API together with its PostgreSQL database, verifiable without a Docker daemon.

## ADDED Requirements

### Requirement: A root Dockerfile builds the project image
The repository SHALL contain a `Dockerfile` at its root that declares a base image, installs the runtime dependencies of the project, copies the application source into the image and sets the default command of the container to start the API server.

#### Scenario: The Dockerfile lives at the repository root
- **WHEN** the repository root is inspected
- **THEN** a file named `Dockerfile` exists at the root of the repository

#### Scenario: The container starts the API server
- **WHEN** the `Dockerfile` is inspected
- **THEN** it declares a `CMD` (or `ENTRYPOINT`) that starts the API application with an ASGI server on the container port `8000`

#### Scenario: The application source is copied into the image
- **WHEN** the `COPY` instructions of the `Dockerfile` are inspected
- **THEN** they copy the application package and the dependency manifest into the image

### Requirement: Every source copied by the Dockerfile exists in the repository
The repository SHALL contain, at the path used by every `COPY` instruction of the `Dockerfile`, the file or directory being copied.

#### Scenario: A copy source is missing
- **WHEN** each path referenced by a `COPY` instruction of the `Dockerfile` is resolved against the repository root
- **THEN** every one of those paths exists in the repository

### Requirement: A root docker-compose.yml builds and runs the project
The repository SHALL contain a `docker-compose.yml` at its root that defines an API service built from the root `Dockerfile` and a PostgreSQL service, wiring the API to the database and exposing the API port.

#### Scenario: The compose file lives at the repository root
- **WHEN** the repository root is inspected
- **THEN** a file named `docker-compose.yml` exists at the root of the repository

#### Scenario: The compose file defines the API and the database
- **WHEN** the `docker-compose.yml` is parsed
- **THEN** it defines one service that builds the project from the root `Dockerfile` and one service that runs a PostgreSQL server, and the API service receives the database connection string of the PostgreSQL service through the `DATABASE_URL` environment variable

#### Scenario: The compose file publishes the API port
- **WHEN** the `docker-compose.yml` is parsed
- **THEN** the API service publishes the container port `8000` to a host port

#### Scenario: The compose file starts the API against the database
- **WHEN** the `docker-compose.yml` is parsed
- **THEN** the API service declares a dependency on the PostgreSQL service

### Requirement: The container files are verifiable without a Docker daemon
The container definition SHALL be verifiable by static inspection alone, so that the delivery can be reviewed in an environment where no Docker daemon is available.

#### Scenario: Static verification of the compose file
- **WHEN** the `docker-compose.yml` is parsed with a YAML parser
- **THEN** the file parses successfully and yields the expected service definitions, with no need to run `docker build` or `docker compose up`

#### Scenario: Static verification of the copy sources
- **WHEN** the `COPY` instructions of the `Dockerfile` are resolved against the repository root
- **THEN** every referenced path is found, with no need to run `docker build`

### Requirement: The image contains the test suite and the API source
The `Dockerfile` SHALL install the development dependencies (including the test runner) and SHALL copy the test package into the image, so that the automated test suite can be executed inside the running container.

#### Scenario: The image ships the tests
- **WHEN** the `COPY` instructions of the `Dockerfile` are inspected
- **THEN** they include the test package of the repository

#### Scenario: The image installs the test runner
- **WHEN** the dependency installation instructions of the `Dockerfile` are inspected
- **THEN** they install the test runner and the HTTP client library used by the test suite


<!-- specs/pet-management/spec.md -->
# Spec Delta

## Purpose

Registry of the pets owned by the clients of the clinic, including the validation rules that keep the species and birth date meaningful and the ownership scoping that prevents clients from seeing or using pets of somebody else.

## ADDED Requirements

### Requirement: A client registers a pet
The API SHALL expose `POST /pets` behind bearer authentication and SHALL accept the JSON body `{"name": <string>, "species": "dog" | "cat" | "other", "birth_date": "YYYY-MM-DD"}` from an account with role `"client"`, answering with HTTP 201 and the JSON body `{"id": <id>, "name": <name>, "species": <species>, "birth_date": <birth_date>, "owner_id": <owner_id>}` where `owner_id` is the identifier of the authenticated client.

#### Scenario: Register a dog
- **WHEN** a client with role `"client"` sends `POST /pets` with the header `Authorization: Bearer <jwt>` and the body `{"name": "Firu", "species": "dog", "birth_date": "2021-05-04"}`
- **THEN** the API responds with HTTP 201 and the JSON body `{"id": <id>, "name": "Firu", "species": "dog", "birth_date": "2021-05-04", "owner_id": <owner_id of the authenticated client>}`

#### Scenario: Register a cat
- **WHEN** a client with role `"client"` sends `POST /pets` with the header `Authorization: Bearer <jwt>` and the body `{"name": "Michi", "species": "cat", "birth_date": "2023-01-15"}`
- **THEN** the API responds with HTTP 201 and the JSON body `{"id": <id>, "name": "Michi", "species": "cat", "birth_date": "2023-01-15", "owner_id": <owner_id of the authenticated client>}`

#### Scenario: Register a pet of another species
- **WHEN** a client with role `"client"` sends `POST /pets` with the header `Authorization: Bearer <jwt>` and the body `{"name": "Pepita", "species": "other", "birth_date": "2022-09-30"}`
- **THEN** the API responds with HTTP 201 and the JSON body `{"id": <id>, "name": "Pepita", "species": "other", "birth_date": "2022-09-30", "owner_id": <owner_id of the authenticated client>}`

### Requirement: Only clients may register pets
The API SHALL answer HTTP 403 when `POST /pets` is requested by an account whose role is `"vet"`.

#### Scenario: A vet tries to register a pet
- **WHEN** a user with role `"vet"` sends `POST /pets` with the header `Authorization: Bearer <jwt>` and the body `{"name": "Firu", "species": "dog", "birth_date": "2021-05-04"}`
- **THEN** the API responds with HTTP 403 and no pet is created

### Requirement: The species must be dog, cat or other
The API SHALL answer HTTP 422 when the `species` of `POST /pets` is any value other than `"dog"`, `"cat"` or `"other"`.

#### Scenario: Unsupported species value
- **WHEN** a client with role `"client"` sends `POST /pets` with the header `Authorization: Bearer <jwt>` and the body `{"name": "Ham", "species": "hamster", "birth_date": "2021-05-04"}`
- **THEN** the API responds with HTTP 422 and no pet is created

#### Scenario: Species is case sensitive
- **WHEN** a client with role `"client"` sends `POST /pets` with the header `Authorization: Bearer <jwt>` and the body `{"name": "Firu", "species": "DOG", "birth_date": "2021-05-04"}`
- **THEN** the API responds with HTTP 422 and no pet is created

### Requirement: The birth date cannot be in the future
The API SHALL answer HTTP 422 when the `birth_date` of `POST /pets` is later than the current date, and SHALL accept a `birth_date` equal to the current date.

#### Scenario: Birth date in the future
- **WHEN** a client with role `"client"` sends `POST /pets` with the header `Authorization: Bearer <jwt>` and the body `{"name": "Firu", "species": "dog", "birth_date": "2999-01-01"}`
- **THEN** the API responds with HTTP 422 and no pet is created

#### Scenario: Birth date equal to today
- **WHEN** a client with role `"client"` sends `POST /pets` with the header `Authorization: Bearer <jwt>` and the body `{"name": "Firu", "species": "dog", "birth_date": <today's date in YYYY-MM-DD>}`
- **THEN** the API responds with HTTP 201

### Requirement: The registration payload is fully validated
The API SHALL answer HTTP 422 when `POST /pets` omits `name`, `species` or `birth_date`, or when `birth_date` is not a valid `YYYY-MM-DD` date.

#### Scenario: Missing name
- **WHEN** a client with role `"client"` sends `POST /pets` with the header `Authorization: Bearer <jwt>` and the body `{"species": "dog", "birth_date": "2021-05-04"}`
- **THEN** the API responds with HTTP 422 and no pet is created

#### Scenario: Malformed birth date
- **WHEN** a client with role `"client"` sends `POST /pets` with the header `Authorization: Bearer <jwt>` and the body `{"name": "Firu", "species": "dog", "birth_date": "04-05-2021"}`
- **THEN** the API responds with HTTP 422 and no pet is created

### Requirement: Listing pets returns only the pets of the caller
The API SHALL expose `GET /pets` behind bearer authentication and SHALL answer with HTTP 200 and a JSON array containing only the pets whose `owner_id` is the identifier of the authenticated account.

#### Scenario: A client lists their own pets
- **WHEN** a client with role `"client"` sends `GET /pets` with the header `Authorization: Bearer <jwt>` and owns the pets `{"id": 1, "name": "Firu", "species": "dog", "birth_date": "2021-05-04"}` and `{"id": 2, "name": "Michi", "species": "cat", "birth_date": "2023-01-15"}`
- **THEN** the API responds with HTTP 200 and the JSON array `["Firu", "Michi"]` with their `id`, `name`, `species`, `birth_date` and `owner_id` fields

#### Scenario: Pets of another client are hidden
- **WHEN** a client with role `"client"` sends `GET /pets` with the header `Authorization: Bearer <jwt>` and another client owns the pet `{"id": 3, "name": "Pepita", "species": "other", "birth_date": "2022-09-30"}`
- **THEN** the API responds with HTTP 200 and the pet named `Pepita` is absent from the array

#### Scenario: A vet owns no pets
- **WHEN** a user with role `"vet"` sends `GET /pets` with the header `Authorization: Bearer <jwt>`
- **THEN** the API responds with HTTP 200 and the JSON array `[]`

#### Scenario: Listing pets requires a token
- **WHEN** a client sends `GET /pets` with no `Authorization` header
- **THEN** the API responds with HTTP 401


<!-- specs/service-health/spec.md -->
# Spec Delta

## Purpose

Public liveness probe of the veterinary clinic API, used by the clinic team and by the container health check to confirm the service is up and reachable.

## ADDED Requirements

### Requirement: Health endpoint is public
The API SHALL expose `GET /health` without requiring an `Authorization` header, and SHALL answer with HTTP 200 and the JSON body `{"status": "ok"}`.

#### Scenario: Health check without credentials
- **WHEN** a client sends `GET /health` with no `Authorization` header
- **THEN** the API responds with HTTP 200 and the JSON body `{"status": "ok"}`

#### Scenario: Health check ignores an invalid bearer token
- **WHEN** a client sends `GET /health` with the header `Authorization: Bearer not-a-real-token`
- **THEN** the API responds with HTTP 200 and the JSON body `{"status": "ok"}` instead of HTTP 401

#### Scenario: Health check is not protected
- **WHEN** a client sends `GET /health` with a valid `Authorization: Bearer <jwt>` header
- **THEN** the API responds with HTTP 200 and the JSON body `{"status": "ok"}`


<!-- specs/user-auth/spec.md -->
# Spec Delta

## Purpose

Account creation and session handling for the two roles of the clinic platform (`client` and `vet`), including JWT access tokens and the bearer authentication guard that protects every non-public endpoint.

## ADDED Requirements

### Requirement: Register a client account
The API SHALL expose `POST /auth/register` accepting the JSON body `{"email": <string>, "password": <string>, "role": "client"}` and SHALL create the account, answering with HTTP 201 and the JSON body `{"id": <id>, "email": <email>, "role": "client"}`.

#### Scenario: Register a client
- **WHEN** a client sends `POST /auth/register` with body `{"email": "ana@example.com", "password": "secreto123", "role": "client"}`
- **THEN** the API responds with HTTP 201 and the JSON body `{"id": <id>, "email": "ana@example.com", "role": "client"}` where `<id>` is the identifier of the newly created account

#### Scenario: Password of fewer than 8 characters is rejected
- **WHEN** a client sends `POST /auth/register` with body `{"email": "ana@example.com", "password": "corto7", "role": "client"}`
- **THEN** the API responds with HTTP 422 and no account is created

#### Scenario: Invalid role is rejected
- **WHEN** a client sends `POST /auth/register` with body `{"email": "ana@example.com", "password": "secreto123", "role": "admin"}`
- **THEN** the API responds with HTTP 422 and no account is created

#### Scenario: Duplicate email is rejected
- **WHEN** an account with email `ana@example.com` already exists and a client sends `POST /auth/register` with body `{"email": "ana@example.com", "password": "secreto123", "role": "client"}`
- **THEN** the API responds with HTTP 409 and no second account is created

### Requirement: Register a veterinarian account
The API SHALL accept `POST /auth/register` with role `"vet"` and SHALL create the account answering with HTTP 201 and the JSON body `{"id": <id>, "email": <email>, "role": "vet"}`.

#### Scenario: Register a vet
- **WHEN** a client sends `POST /auth/register` with body `{"email": "dra.solaris@example.com", "password": "veterinaria1", "role": "vet"}`
- **THEN** the API responds with HTTP 201 and the JSON body `{"id": <id>, "email": "dra.solaris@example.com", "role": "vet"}`

### Requirement: Log in and receive a JWT access token
The API SHALL expose `POST /auth/login` accepting the JSON body `{"email": <string>, "password": <string>}` and SHALL answer with HTTP 200 and the JSON body `{"access_token": <jwt>, "token_type": "bearer"}` when the credentials match an existing account.

#### Scenario: Login with valid credentials
- **WHEN** a client sends `POST /auth/login` with body `{"email": "ana@example.com", "password": "secreto123"}` for an existing account
- **THEN** the API responds with HTTP 200, the JSON body `{"access_token": <jwt>, "token_type": "bearer"}`, and `<jwt>` is a JSON Web Token that identifies the account and its role

#### Scenario: Login with a wrong password
- **WHEN** a client sends `POST /auth/login` with body `{"email": "ana@example.com", "password": "incorrecta9"}` for an existing account
- **THEN** the API responds with HTTP 401

#### Scenario: Login with an unknown email
- **WHEN** a client sends `POST /auth/login` with body `{"email": "nadie@example.com", "password": "secreto123"}`
- **THEN** the API responds with HTTP 401

#### Scenario: Login is a public endpoint
- **WHEN** a client sends `POST /auth/login` with the body `{"email": "ana@example.com", "password": "secreto123"}` of an existing account and no `Authorization` header
- **THEN** the API responds with HTTP 200 and the JSON body `{"access_token": <jwt>, "token_type": "bearer"}`

### Requirement: Passwords are never stored in clear text
The API SHALL persist only a salted hash of the password of every account and SHALL never return a password or a password hash in any response body.

#### Scenario: Registration response hides credentials
- **WHEN** a client sends `POST /auth/register` with body `{"email": "ana@example.com", "password": "secreto123", "role": "client"}`
- **THEN** the HTTP 201 response body contains the keys `id`, `email` and `role` only, and the stored password is not the literal value `secreto123`

### Requirement: Protected endpoints require a bearer token
Every endpoint except `GET /health`, `POST /auth/register` and `POST /auth/login` SHALL require an `Authorization: Bearer <jwt>` header, and SHALL answer HTTP 401 when the header is missing, malformed, carries an invalid token, or carries an expired token.

#### Scenario: Protected endpoint without an Authorization header
- **WHEN** a client sends `GET /vets` with no `Authorization` header
- **THEN** the API responds with HTTP 401

#### Scenario: Protected endpoint with a malformed Authorization header
- **WHEN** a client sends `GET /vets` with the header `Authorization: Basic dXNlcjpwYXNz`
- **THEN** the API responds with HTTP 401

#### Scenario: Protected endpoint with an invalid token
- **WHEN** a client sends `GET /vets` with the header `Authorization: Bearer invalid.token.value`
- **THEN** the API responds with HTTP 401

#### Scenario: Protected endpoint with an expired token
- **WHEN** a client sends `GET /vets` with the header `Authorization: Bearer <jwt that expired before the request>`
- **THEN** the API responds with HTTP 401

#### Scenario: Protected endpoint with a valid token
- **WHEN** a client sends `GET /pets` with the header `Authorization: Bearer <jwt issued by the login endpoint>`
- **THEN** the API does not respond with HTTP 401 and continues processing the request


<!-- specs/vet-directory/spec.md -->
# Spec Delta

## Purpose

Directory of the veterinarians of the clinic, so that a client (or a colleague vet) can discover who is available to receive an appointment.

## ADDED Requirements

### Requirement: List the veterinarians
The API SHALL expose `GET /vets` behind bearer authentication and SHALL answer with HTTP 200 and a JSON array containing one object `{"id": <id>, "email": <email>}` per account whose role is `"vet"`.

#### Scenario: List vets with a valid token
- **WHEN** a client sends `GET /vets` with the header `Authorization: Bearer <jwt>` of a registered client
- **THEN** the API responds with HTTP 200 and a JSON array of objects `{"id": <id>, "email": <email>}`, one per registered veterinarian

#### Scenario: Clients are not part of the directory
- **WHEN** a client sends `GET /vets` with the header `Authorization: Bearer <jwt>` and the platform has one account with role `"client"` and one account with role `"vet"`
- **THEN** the API responds with HTTP 200 and a JSON array of exactly one object, and the email of the client account is absent from the array

#### Scenario: Empty directory
- **WHEN** a client sends `GET /vets` with the header `Authorization: Bearer <jwt>` and no veterinarian has been registered
- **THEN** the API responds with HTTP 200 and the JSON array `[]`

#### Scenario: Listing vets requires a token
- **WHEN** a client sends `GET /vets` with no `Authorization` header
- **THEN** the API responds with HTTP 401

#### Scenario: Listing vets rejects an invalid token
- **WHEN** a client sends `GET /vets` with the header `Authorization: Bearer invalid.token.value`
- **THEN** the API responds with HTTP 401


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

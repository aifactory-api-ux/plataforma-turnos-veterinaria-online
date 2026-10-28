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

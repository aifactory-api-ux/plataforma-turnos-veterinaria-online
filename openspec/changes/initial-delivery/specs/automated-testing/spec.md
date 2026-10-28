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

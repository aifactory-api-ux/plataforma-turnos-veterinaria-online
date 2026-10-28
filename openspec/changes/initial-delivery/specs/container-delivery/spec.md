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

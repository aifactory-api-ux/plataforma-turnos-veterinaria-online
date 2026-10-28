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

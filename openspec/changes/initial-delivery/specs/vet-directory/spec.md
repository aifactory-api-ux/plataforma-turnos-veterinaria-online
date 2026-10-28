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

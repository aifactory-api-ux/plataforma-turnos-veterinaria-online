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

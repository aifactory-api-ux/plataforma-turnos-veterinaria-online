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

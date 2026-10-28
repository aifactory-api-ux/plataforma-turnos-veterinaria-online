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

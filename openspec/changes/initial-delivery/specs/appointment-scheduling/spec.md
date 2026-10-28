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


"""Esquemas de entrada y salida de la API (Pydantic v2)."""

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_serializer, field_validator

Role = Literal["client", "vet"]
Species = Literal["dog", "cat", "other"]

# Límite de bcrypt: las contraseñas más largas se truncan en silencio.
MAX_PASSWORD_BYTES = 72


def _as_utc(value: datetime) -> datetime:
    """Convierte a UTC las marcas de tiempo, assumiendo UTC si no traen zona."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso_z(value: datetime) -> str:
    """Serializa una marca de tiempo UTC con el sufijo `Z`."""
    return _as_utc(value).isoformat().replace("+00:00", "Z")


class RegisterRequest(BaseModel):
    """Payload de alta de una cuenta."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)
    role: Role

    @field_validator("password")
    @classmethod
    def _check_password_size(cls, value: str) -> str:
        """Rechaza contraseñas que superen el límite de bytes de bcrypt."""
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(
                f"la contraseña no puede superar {MAX_PASSWORD_BYTES} bytes"
            )
        return value


class LoginRequest(BaseModel):
    """Payload de inicio de sesión."""

    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Datos públicos de una cuenta."""

    id: int
    email: EmailStr
    role: Role


class VetOut(BaseModel):
    """Entrada del directorio de veterinarios."""

    id: int
    email: EmailStr


class TokenOut(BaseModel):
    """Respuesta del inicio de sesión."""

    access_token: str
    token_type: str = "bearer"


class PetCreate(BaseModel):
    """Payload de alta de una mascota."""

    name: str = Field(min_length=1, max_length=120)
    species: Species
    birth_date: date

    @field_validator("birth_date")
    @classmethod
    def _check_birth_date(cls, value: date) -> date:
        """Impide registrar una fecha de nacimiento futura."""
        if value > date.today():
            raise ValueError("la fecha de nacimiento no puede ser futura")
        return value


class PetOut(BaseModel):
    """Datos de una mascota registrada."""

    id: int
    name: str
    species: Species
    birth_date: date
    owner_id: int


class AppointmentCreate(BaseModel):
    """Payload de reserva de un turno."""

    pet_id: int
    vet_id: int
    start_at: datetime

    @field_validator("start_at")
    @classmethod
    def _normalize_start_at(cls, value: datetime) -> datetime:
        """Normaliza la hora de inicio a UTC."""
        return _as_utc(value)


class AppointmentOut(BaseModel):
    """Datos de un turno agendado."""

    id: int
    pet_id: int
    vet_id: int
    start_at: datetime
    end_at: datetime
    status: str

    @field_serializer("start_at", "end_at")
    def _serialize_moment(self, value: datetime) -> str:
        """Expone las marcas de tiempo en UTC con el sufijo `Z`."""
        return _iso_z(value)

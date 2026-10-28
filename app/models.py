"""Modelos ORM de la clínica veterinaria: cuentas, mascotas y turnos."""

from datetime import date, datetime, timezone

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UTCDateTime


def utc_now() -> datetime:
    """Instante actual en UTC, usado como valor por defecto de `created_at`."""
    return datetime.now(timezone.utc)


class User(Base):
    """Cuenta de la plataforma: un cliente o un veterinario."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    pets: Mapped[list["Pet"]] = relationship(
        back_populates="owner",
        foreign_keys="Pet.owner_id",
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="vet",
        foreign_keys="Appointment.vet_id",
    )


class Pet(Base):
    """Mascota registrada por un cliente."""

    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    species: Mapped[str] = mapped_column(String(16))
    birth_date: Mapped[date] = mapped_column(Date)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    owner: Mapped["User"] = relationship(back_populates="pets", foreign_keys=[owner_id])
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="pet",
        foreign_keys="Appointment.pet_id",
    )


class Appointment(Base):
    """Turno de 30 minutos entre una mascota y un veterinario."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), index=True
    )
    vet_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    start_at: Mapped[datetime] = mapped_column(UTCDateTime)
    end_at: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String(16), default="scheduled")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    pet: Mapped["Pet"] = relationship(back_populates="appointments", foreign_keys=[pet_id])
    vet: Mapped["User"] = relationship(
        back_populates="appointments", foreign_keys=[vet_id]
    )

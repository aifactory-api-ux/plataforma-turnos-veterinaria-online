"""Router de la agenda de turnos.

Permite a los clientes reservar turnos de 30 minutos con un veterinario para
sus propias mascotas, consultar los turnos que les corresponden y cancelar
los que ya no van a necesitar. Solo las cuentas con rol `client` reservan
(un veterinario recibe HTTP 403); el listado y la cancelación aceptan
clientes y veterinarios. Todas las rutas exigen el token bearer que emite
`POST /auth/login`.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_client
from app.models import Appointment, Pet, User
from app.schemas import AppointmentCreate, AppointmentOut
from app.services.scheduling import SlotValidationError, slot_end, validate_slot

router = APIRouter(prefix="/appointments", tags=["appointments"])

VET_ROLE = "vet"
SCHEDULED_STATUS = "scheduled"
CANCELLED_STATUS = "cancelled"

PET_NOT_FOUND_DETAIL = "La mascota no existe"
VET_NOT_FOUND_DETAIL = "El veterinario no existe"
FOREIGN_PET_DETAIL = "La mascota pertenece a otra cuenta"
SLOT_NOT_FOUND_DETAIL = "El turno no existe"
SLOT_CONFLICT_DETAIL = "El veterinario ya tiene un turno en ese horario"
ALREADY_CANCELLED_DETAIL = "El turno ya está cancelado"


def _to_out(appointment: Appointment) -> AppointmentOut:
    """Construye la representación pública de un turno."""
    return AppointmentOut(
        id=appointment.id,
        pet_id=appointment.pet_id,
        vet_id=appointment.vet_id,
        start_at=appointment.start_at,
        end_at=appointment.end_at,
        status=appointment.status,
    )


@router.post(
    "",
    response_model=AppointmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Reserva de un turno para una mascota del cliente",
)
def create_appointment(
    payload: AppointmentCreate,
    current_user: User = Depends(require_client),
    db: Session = Depends(get_db),
) -> AppointmentOut:
    """Reserva un turno de 30 minutos para una mascota del cliente.

    Las comprobaciones se aplican en un orden estable: rol de la cuenta,
    existencia de la mascota, existencia del veterinario, pertenencia de la
    mascota, ventana horaria y, por último, conflicto de agenda.

    Args:
        payload: Mascota, veterinario e inicio del turno solicitados.
        current_user: Cuenta autenticada; solo los clientes pueden reservar.
        db: Sesión de base de datos de la petición.

    Returns:
        Los datos del turno creado, con su inicio, su fin y su estado.

    Raises:
        HTTPException: 404 si la mascota o el veterinario no existen, 403 si
            la mascota es de otra cuenta y 409 si el veterinario ya tiene un
            turno activo en esa franja.
    """
    pet = db.get(Pet, payload.pet_id)
    if pet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PET_NOT_FOUND_DETAIL
        )

    vet = db.get(User, payload.vet_id)
    if vet is None or vet.role != VET_ROLE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=VET_NOT_FOUND_DETAIL
        )

    if pet.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=FOREIGN_PET_DETAIL
        )

    try:
        validate_slot(payload.start_at, datetime.now(timezone.utc))
    except SlotValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        )

    taken = db.scalar(
        select(Appointment).where(
            Appointment.vet_id == vet.id,
            Appointment.start_at == payload.start_at,
            Appointment.status == SCHEDULED_STATUS,
        )
    )
    if taken is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=SLOT_CONFLICT_DETAIL
        )

    appointment = Appointment(
        pet_id=pet.id,
        vet_id=vet.id,
        start_at=payload.start_at,
        end_at=slot_end(payload.start_at),
        status=SCHEDULED_STATUS,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return _to_out(appointment)


@router.get(
    "",
    response_model=list[AppointmentOut],
    summary="Listado de los turnos de la cuenta autenticada",
)
def list_appointments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AppointmentOut]:
    """Devuelve los turnos que le corresponden a la cuenta autenticada.

    Un cliente ve los turnos de las mascotas que posee y un veterinario ve los
    turnos que tiene asignados.

    Args:
        current_user: Cuenta autenticada.
        db: Sesión de base de datos de la petición.

    Returns:
        La lista de turnos visibles para la cuenta, ordenada por identificador.
    """
    if current_user.role == VET_ROLE:
        query = select(Appointment).where(Appointment.vet_id == current_user.id)
    else:
        query = (
            select(Appointment)
            .join(Pet, Appointment.pet_id == Pet.id)
            .where(Pet.owner_id == current_user.id)
        )

    appointments = db.scalars(query.order_by(Appointment.id)).all()

    return [_to_out(appointment) for appointment in appointments]


@router.post(
    "/{id}/cancel",
    response_model=AppointmentOut,
    summary="Cancelación de un turno",
)
def cancel_appointment(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentOut:
    """Cancela un turno y libera su franja para volver a reservarla.

    Solo puede cancelar el dueño de la mascota o el veterinario asignado al
    turno.

    Args:
        id: Identificador del turno a cancelar.
        current_user: Cuenta autenticada.
        db: Sesión de base de datos de la petición.

    Returns:
        Los datos del turno cancelado.

    Raises:
        HTTPException: 404 si el turno no existe, 403 si la cuenta no es la
            dueña de la mascota ni el veterinario asignado y 409 si el turno
            ya estaba cancelado.
    """
    appointment = db.get(Appointment, id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=SLOT_NOT_FOUND_DETAIL
        )

    pet = db.get(Pet, appointment.pet_id)
    es_dueno = pet is not None and pet.owner_id == current_user.id
    es_veterinario = appointment.vet_id == current_user.id
    if not es_dueno and not es_veterinario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el dueño de la mascota o el veterinario pueden cancelar el turno",
        )

    if appointment.status == CANCELLED_STATUS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ALREADY_CANCELLED_DETAIL
        )

    appointment.status = CANCELLED_STATUS
    db.commit()
    db.refresh(appointment)

    return _to_out(appointment)

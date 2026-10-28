"""Router del registro de mascotas.

Permite a los clientes dar de alta sus mascotas y consultar las suyas. El
alta está reservada a las cuentas con rol `client` (un veterinario recibe
HTTP 403) y el listado solo devuelve las mascotas propiedad de la cuenta
autenticada. Ambas rutas exigen el token bearer que emite
`POST /auth/login`.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_client
from app.models import Pet, User
from app.schemas import PetCreate, PetOut

router = APIRouter(prefix="/pets", tags=["pets"])


@router.post(
    "",
    response_model=PetOut,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de una mascota a nombre del cliente autenticado",
)
def create_pet(
    payload: PetCreate,
    current_user: User = Depends(require_client),
    db: Session = Depends(get_db),
) -> PetOut:
    """Registra una mascota y la asigna al cliente autenticado.

    Args:
        payload: Datos de la mascota, ya validados por el esquema de entrada.
        current_user: Cuenta autenticada; solo los clientes pueden dar de
            alta mascotas.
        db: Sesión de base de datos de la petición.

    Returns:
        Los datos de la mascota creada, incluido el identificador de su
        propietario.
    """
    pet = Pet(
        name=payload.name,
        species=payload.species,
        birth_date=payload.birth_date,
        owner_id=current_user.id,
    )
    db.add(pet)
    db.commit()
    db.refresh(pet)

    return PetOut(
        id=pet.id,
        name=pet.name,
        species=pet.species,
        birth_date=pet.birth_date,
        owner_id=pet.owner_id,
    )


@router.get(
    "",
    response_model=list[PetOut],
    summary="Listado de las mascotas de la cuenta autenticada",
)
def list_pets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PetOut]:
    """Devuelve únicamente las mascotas propiedad de la cuenta autenticada.

    Args:
        current_user: Cuenta autenticada; un veterinario no es dueño de
            ninguna mascota, por lo que su listado es una lista vacía.
        db: Sesión de base de datos de la petición.

    Returns:
        La lista de mascotas de la cuenta, ordenadas por identificador.
    """
    pets = db.scalars(
        select(Pet).where(Pet.owner_id == current_user.id).order_by(Pet.id)
    ).all()

    return [
        PetOut(
            id=pet.id,
            name=pet.name,
            species=pet.species,
            birth_date=pet.birth_date,
            owner_id=pet.owner_id,
        )
        for pet in pets
    ]

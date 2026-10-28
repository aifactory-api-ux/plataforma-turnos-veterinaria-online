"""Router del directorio de veterinarios.

Expone las cuentas con rol `vet` para que un cliente (o un colega
veterinario) pueda saber con quién agendar un turno. La ruta está protegida
con el token bearer que emite `POST /auth/login`.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import VetOut

router = APIRouter(prefix="/vets", tags=["vets"])

VET_ROLE = "vet"


@router.get(
    "",
    response_model=list[VetOut],
    summary="Listado de los veterinarios de la clínica",
)
def list_vets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VetOut]:
    """Devuelve las cuentas con rol `vet`.

    Args:
        current_user: Cuenta autenticada; cualquier rol puede consultar el
            directorio.
        db: Sesión de base de datos de la petición.

    Returns:
        La lista de veterinarios con su identificador y su correo.
    """
    vets = db.scalars(
        select(User).where(User.role == VET_ROLE).order_by(User.id)
    ).all()

    return [VetOut(id=vet.id, email=vet.email) for vet in vets]

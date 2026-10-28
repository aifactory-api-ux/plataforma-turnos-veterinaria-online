"""Sonda de disponibilidad de la API de la clínica veterinaria.

El endpoint es público: no aplica la dependencia de autenticación, de modo
que la comprobación de vida del servicio funcione sin credenciales.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Comprobación de disponibilidad de la API")
def health_check() -> dict[str, str]:
    """Indica que el servicio está operativo.

    Returns:
        El cuerpo `{"status": "ok"}` con el que la API confirma su estado.
    """
    return {"status": "ok"}

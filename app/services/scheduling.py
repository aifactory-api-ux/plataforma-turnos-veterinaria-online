"""Reglas puras de las franjas horarias reservables.

El módulo no toca la base de datos: solo decide si un instante cumple las
condiciones de la clínica (turnos de 30 minutos que empiezan en punto o en
y media, de lunes a sábado, con inicio entre las 09:00 y las 17:30 UTC y
nunca en el pasado) y calcula el final del turno. El router de turnos
traduce el error de validación en una respuesta HTTP 422.
"""

from datetime import datetime, time, timedelta, timezone

# Duración de cada turno.
SLOT_MINUTES = 30
# Primera hora de inicio admitida (09:00 UTC).
OPENING_TIME = time(9, 0)
# Última hora de inicio admitida (17:30 UTC): el turno termina a las 18:00.
LAST_START_TIME = time(17, 30)
# Días reservables: de lunes (0) a sábado (5); el domingo queda excluido.
BOOKABLE_WEEKDAYS = {0, 1, 2, 3, 4, 5}
# Minutos admitidos para el inicio de un turno.
ALLOWED_START_MINUTES = {0, 30}


class SlotValidationError(ValueError):
    """La franja solicitada no cumple las reglas de agenda de la clínica."""


def _as_utc(value: datetime) -> datetime:
    """Convierte a UTC una marca de tiempo, asumiendo UTC si no trae zona."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def validate_slot(start_at: datetime, now: datetime) -> None:
    """Comprueba que el inicio del turno cumple todas las reglas de la clínica.

    Args:
        start_at: Instante de inicio del turno.
        now: Instante de referencia para descartar los turnos en el pasado.

    Raises:
        SlotValidationError: Si el turno ya pasó, no empieza en punto o en
            y media, cae en domingo o está fuera de la franja horaria.
    """
    inicio = _as_utc(start_at)
    referencia = _as_utc(now)

    if inicio < referencia:
        raise SlotValidationError("el turno no puede reservarse en el pasado")
    if inicio.minute not in ALLOWED_START_MINUTES:
        raise SlotValidationError("los turnos empiezan en punto o en y media")
    if inicio.weekday() not in BOOKABLE_WEEKDAYS:
        raise SlotValidationError("la clínica atiende de lunes a sábado")
    if not OPENING_TIME <= inicio.time() <= LAST_START_TIME:
        raise SlotValidationError(
            "los turnos empiezan entre las 09:00 y las 17:30 (UTC)"
        )


def slot_end(start_at: datetime) -> datetime:
    """Devuelve el instante de fin del turno que empieza en `start_at`.

    Args:
        start_at: Instante de inicio del turno.

    Returns:
        El inicio del turno desplazado 30 minutos.
    """
    return start_at + timedelta(minutes=SLOT_MINUTES)

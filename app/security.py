"""Hash de contraseñas y emisión y verificación de tokens JWT."""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config import settings

# Tipo de token devuelto en las respuestas de autenticación.
TOKEN_TYPE = "bearer"


def hash_password(password: str) -> str:
    """Devuelve el hash con sal de una contraseña en texto plano."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Comprueba una contraseña contra su hash, sin propagar errores del motor."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (TypeError, ValueError):
        return False


def create_access_token(
    subject: int | str,
    role: str,
    expires_minutes: int | None = None,
) -> str:
    """Firma un token de acceso con `sub`, `role`, `iat` y `exp`."""
    now = datetime.now(timezone.utc)
    minutes = (
        settings.access_token_expire_minutes
        if expires_minutes is None
        else expires_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Verifica la firma y la caducidad del token, devolviendo su payload."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )

"""Dependencias de autenticación y autorización de la API."""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

# Se desactiva el error automático de FastAPI para responder siempre 401.
bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR_DETAIL = "Credenciales ausentes o inválidas"


def _unauthorized() -> HTTPException:
    """Construye el error 401 con la cabecera de autenticación bearer."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=CREDENTIALS_ERROR_DETAIL,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resuelve la cuenta autenticada a partir de la cabecera `Authorization`."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _unauthorized()

    subject = payload.get("sub")
    if subject is None:
        raise _unauthorized()

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise _unauthorized()

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized()

    return user


def require_roles(*roles: str):
    """Crea una dependencia que exige uno de los roles indicados."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La cuenta no tiene permisos para esta operación",
            )
        return current_user

    return dependency


require_client = require_roles("client")

"""Router de autenticación: alta de cuentas e inicio de sesión.

Las dos rutas son públicas. El resto de la API se protege con el token
bearer que emite `POST /auth/login`, a través de `get_current_user`.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenOut, UserOut
from app.security import (
    TOKEN_TYPE,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

DUPLICATE_EMAIL_DETAIL = "El correo ya está registrado"
CREDENTIALS_ERROR_DETAIL = "Credenciales incorrectas"


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de una cuenta de cliente o veterinario",
)
def register_account(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserOut:
    """Crea una cuenta nueva y guarda la contraseña como hash con sal.

    Args:
        payload: Datos del alta, ya validados por el esquema de entrada.
        db: Sesión de base de datos de la petición.

    Returns:
        Los datos públicos de la cuenta creada.

    Raises:
        HTTPException: 409 si el correo ya está registrado.
    """
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_EMAIL_DETAIL,
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # La restricción de unicidad es la red de seguridad ante altas simultáneas.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_EMAIL_DETAIL,
        )
    db.refresh(user)

    return UserOut(id=user.id, email=user.email, role=user.role)


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Inicio de sesión de una cuenta",
)
def login_account(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenOut:
    """Verifica las credenciales y emite un token de acceso JWT.

    Args:
        payload: Correo y contraseña de la cuenta.
        db: Sesión de base de datos de la petición.

    Returns:
        El token de acceso y su tipo de transporte.

    Raises:
        HTTPException: 401 si el correo no existe o la contraseña no coincide.
    """
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=CREDENTIALS_ERROR_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id, user.role)
    return TokenOut(access_token=access_token, token_type=TOKEN_TYPE)

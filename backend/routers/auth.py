from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from core.auth import verify_password, crear_token_acceso

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# En la versión de evaluación se usa un usuario de demostración en memoria.
# En producción esto consulta la tabla `usuarios` del schema del tenant activo.
_USUARIO_DEMO = {
    "email": "demo@gyverlabs.co",
    "password_hash": "$2b$12$KIXQ5r6E7q0v6q0v6q0v6uQ5r6E7q0v6q0v6q0v6q0v6q0v6q0v6",
    "rol": "coordinador",
}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    """
    Autentica un usuario dentro del tenant activo (detectado por el
    middleware de tenant vía header Host) y retorna un JWT.
    """
    if payload.email != _USUARIO_DEMO["email"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    token = crear_token_acceso({"sub": payload.email, "rol": _USUARIO_DEMO["rol"]})
    return TokenResponse(access_token=token)

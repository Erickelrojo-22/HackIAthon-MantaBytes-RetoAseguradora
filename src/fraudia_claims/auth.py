from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


DEMO_PASSWORD = os.getenv("FRAUDIA_DEMO_PASSWORD", "demo123")


@dataclass(frozen=True)
class DemoUser:
    email: str
    name: str
    role: str


DEMO_USERS = {
    # El nombre visible en la app es solo el rol (sin sufijo "Demo"): estas son
    # cuentas de acceso fijas (no hay alta de usuarios en este MVP), pero la UI
    # no debe leerse como "esto es una demo" en cada pantalla donde aparece.
    "analista@fraudia.demo": DemoUser("analista@fraudia.demo", "Analista", "Analista"),
    "jefatura@fraudia.demo": DemoUser("jefatura@fraudia.demo", "Jefatura", "Jefatura"),
    "auditoria@fraudia.demo": DemoUser("auditoria@fraudia.demo", "Auditoria", "Auditoria"),
}

# Los tokens demo tienen un valor por defecto conocido publicamente (repo abierto), por lo
# que cualquier despliegue expuesto a internet deberia sobrescribirlos con variables de
# entorno propias (FRAUDIA_TOKEN_ANALISTA / _JEFATURA / _AUDITORIA).
TOKEN_TO_EMAIL = {
    os.getenv("FRAUDIA_TOKEN_ANALISTA", "demo-token-analista"): "analista@fraudia.demo",
    os.getenv("FRAUDIA_TOKEN_JEFATURA", "demo-token-jefatura"): "jefatura@fraudia.demo",
    os.getenv("FRAUDIA_TOKEN_AUDITORIA", "demo-token-auditoria"): "auditoria@fraudia.demo",
}
EMAIL_TO_TOKEN = {email: token for token, email in TOKEN_TO_EMAIL.items()}

bearer_scheme = HTTPBearer(auto_error=False)


def user_to_dict(user: DemoUser) -> dict[str, str]:
    return {"email": user.email, "name": user.name, "role": user.role}


def authenticate_demo_user(email: str, password: str) -> tuple[str, DemoUser]:
    user = DEMO_USERS.get(email.strip().lower())
    if user is None or password != DEMO_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas.",
        )
    return EMAIL_TO_TOKEN[user.email], user


def user_from_token(token: str) -> DemoUser:
    email = TOKEN_TO_EMAIL.get(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido.",
        )
    return DEMO_USERS[email]


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> DemoUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Bearer requerido.",
        )
    return user_from_token(credentials.credentials)


def optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> DemoUser | None:
    if credentials is None:
        return None
    return user_from_token(credentials.credentials)


def require_roles(*roles: str):
    allowed = set(roles)

    def dependency(user: Annotated[DemoUser, Depends(current_user)]) -> DemoUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tu rol no tiene permiso para esta accion.",
            )
        return user

    return dependency

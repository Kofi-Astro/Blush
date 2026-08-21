# The single admin login endpoint. There's only ever one admin account
# (configured via env vars, not stored in the database), so this just
# checks the submitted username/password and, if correct, hands back a
# signed login token for the dashboard to use on every future request.

from fastapi import APIRouter, HTTPException, status

from ..config import get_settings
from ..schemas import LoginRequest, TokenResponse
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    """POST /api/auth/login — checks admin credentials, returns a login token on success."""
    if payload.username != settings.admin_username or not verify_password(
        payload.password, settings.admin_password_hash
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    token = create_access_token(subject=payload.username)
    return TokenResponse(access_token=token)

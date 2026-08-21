# Low-level password + login-token helpers used by the admin login flow
# (routers/auth.py) and by the admin-only gatekeeper (deps.py).

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import get_settings

settings = get_settings()

JWT_ALGORITHM = "HS256"


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Checks a typed-in password against the stored bcrypt hash, without
    ever needing to know the real password."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject: str) -> str:
    """Issues a signed login token (JWT) after a successful admin login.
    The dashboard stores this and sends it back on every admin request;
    it expires automatically after `jwt_expire_minutes`."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Verifies a login token is genuine and not expired, returning the
    admin username if so, or None if the token is invalid/expired/tampered."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None

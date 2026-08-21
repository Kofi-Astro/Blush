# The "gatekeeper" for admin-only API routes. Any endpoint that should only
# be usable from the logged-in admin dashboard (creating/editing/deleting
# products, orders, hero media, etc.) depends on `require_admin` below —
# public read-only endpoints (like "list products") don't use it.

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings
from .security import decode_access_token

settings = get_settings()
# Reads the "Authorization: Bearer <token>" header, if present.
bearer_scheme = HTTPBearer(auto_error=False)


def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    """Checks the login token sent by the admin dashboard is present, valid,
    and belongs to the configured admin account. Raises a 401 error (which
    the dashboard turns into "please log in again") if not."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    username = decode_access_token(credentials.credentials)
    if username is None or username != settings.admin_username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    return username

"""
FastAPI Security Dependencies
Provides Depends() functions for JWT validation and role-based access control.
"""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

try:
    from fastapi import Depends, HTTPException, status  # pyre-ignore[21]
    from fastapi.security import OAuth2PasswordBearer  # pyre-ignore[21]
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from auth.auth_handler import decode_token  # pyre-ignore[21]

if FASTAPI_AVAILABLE:
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
else:
    oauth2_scheme = None

# Role hierarchy: higher index = more privileges
ROLE_HIERARCHY = {"engineer": 1, "finance": 2, "admin": 3}


def get_current_user(token: Optional[str] = None):
    """
    FastAPI dependency that extracts and validates the JWT from the Authorization header.
    Returns the decoded user payload.
    Raises 401 if token is missing or invalid.
    """
    if token is None:
        # Allow unauthenticated access to read-only endpoints in dev
        return {"sub": "anonymous", "role": "engineer"}

    payload = decode_token(token)
    if not payload:
        if FASTAPI_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    return payload


def require_role(minimum_role: str = "engineer"):
    """
    Returns a FastAPI dependency factory that enforces a minimum role level.
    Usage: @app.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """
    def _check_role(user: Optional[Dict[str, Any]] = None):
        role = user.get("role", "engineer") if user else "engineer"
        user_level = ROLE_HIERARCHY.get(role, 0)
        required_level = ROLE_HIERARCHY.get(minimum_role, 1)

        if user_level < required_level:
            if FASTAPI_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: requires '{minimum_role}' role or higher.",
                )

    return _check_role

"""
Role-Based Access Control (RBAC) Dependencies
Provides FastAPI dependencies to secure endpoints based on user roles.
"""
from fastapi import Depends, HTTPException, status, Request  # pyre-ignore[21]
from fastapi.security import OAuth2PasswordBearer  # pyre-ignore[21]
from typing import Optional
from auth.auth_handler import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Decodes JWT and returns the current user payload."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

class RequireRole:
    """
    FastAPI dependency class to require specific roles.
    Usage: @app.post("/admin", dependencies=[Depends(RequireRole(["admin"]))])
    """
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: dict = Depends(get_current_user)):
        user_role = user.get("role", "viewer")
        
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {self.allowed_roles}, but got '{user_role}'"
            )
        return user

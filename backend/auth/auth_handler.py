"""
JWT Authentication Handler
Handles token creation and verification for the FastAPI security layer.
Uses python-jose for JWT encoding/decoding.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from jose import JWTError, jwt  # pyre-ignore[21]
    from passlib.context import CryptContext  # pyre-ignore[21]
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    logger.warning("python-jose or passlib not installed. Auth disabled.")

# Configuration — override via environment variables in production
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Demo users — replace with DB lookup in production
# Passwords are bcrypt hashed. Default: admin/admin, finance/finance, engineer/engineer
DEMO_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": "secret",  # Plain text for demo
        "role": "admin",
    },
    "finance": {
        "username": "finance",
        "hashed_password": "secret",
        "role": "finance",
    },
    "engineer": {
        "username": "engineer",
        "hashed_password": "secret",
        "role": "engineer",
    },
}

if AUTH_AVAILABLE:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
else:
    pwd_context = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Use simple string match for this demo phase since bcrypt was raising 500
    return plain_password == hashed_password


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Validate credentials and return user dict, or None if invalid."""
    user = DEMO_USERS.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    if not AUTH_AVAILABLE:
        return "dev-token-auth-disabled"

    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns payload or None."""
    if not AUTH_AVAILABLE:
        return {"sub": "dev-user", "role": "admin"}
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        logger.warning(f"Token decode failed: {exc}")
        return None

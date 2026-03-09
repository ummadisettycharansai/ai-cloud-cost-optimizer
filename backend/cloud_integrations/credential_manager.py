"""
Credential Manager — secure Fernet symmetric encryption for cloud credentials.

Usage:
    mgr = CredentialManager()
    blob = mgr.encrypt({"access_key": "...", "secret_key": "..."})
    data = mgr.decrypt(blob)

The encryption key is read from:
  1. CREDENTIAL_ENCRYPTION_KEY environment variable
  2. backend/config.py → settings.credential_encryption_key
  3. Auto-generated (DEV MODE ONLY) — printed to stdout on first run.

In production, always set CREDENTIAL_ENCRYPTION_KEY to a stable Fernet key.
Generate one with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet, InvalidToken  # pyre-ignore[21]
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logger.warning("cryptography not installed — credential encryption disabled.")


class CloudActionError(Exception):
    """Raised when a real cloud remediation action fails."""


class CredentialManager:
    """
    Encrypts and decrypts credential dicts using Fernet symmetric encryption.
    Falls back to plain Base64 JSON (NOT secure) when cryptography is absent.
    """

    def __init__(self) -> None:
        self._key: bytes | None = None
        self._fernet = None
        self._load_key()

    def _load_key(self) -> None:
        """Load or auto-generate the Fernet encryption key."""
        # 1. Try environment variable
        raw = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")

        # 2. Try config.py
        if not raw:
            try:
                from config import settings  # pyre-ignore[21]
                raw = settings.credential_encryption_key or ""
            except Exception:
                pass

        if raw and CRYPTOGRAPHY_AVAILABLE:
            try:
                self._key = raw.encode() if isinstance(raw, str) else raw
                self._fernet = Fernet(self._key)
                logger.info("CredentialManager: Fernet key loaded from environment.")
                return
            except Exception as exc:
                logger.warning(f"CredentialManager: Invalid key ({exc}). Regenerating.")

        # 3. Auto-generate (DEV ONLY)
        if CRYPTOGRAPHY_AVAILABLE:
            self._key = Fernet.generate_key()
            self._fernet = Fernet(self._key)
            logger.warning(
                "CredentialManager: No CREDENTIAL_ENCRYPTION_KEY set. "
                "Auto-generated key (DEV MODE — credentials won't survive restart):\n"
                f"  CREDENTIAL_ENCRYPTION_KEY={self._key.decode()}\n"
                "  Set this in your .env file to persist credentials across restarts."
            )
        else:
            logger.warning(
                "CredentialManager: cryptography not installed. "
                "Credentials stored as plain JSON (NOT production-safe)."
            )

    def encrypt(self, data: Dict[str, Any]) -> str:
        """Encrypt a credential dict to a string blob."""
        payload = json.dumps(data).encode()
        if self._fernet:
            return self._fernet.encrypt(payload).decode()
        # Fallback: base64 (not secure — development only)
        import base64
        return base64.b64encode(payload).decode()

    def decrypt(self, blob: str) -> Dict[str, Any]:
        """Decrypt a stored credential blob back to a dict."""
        if self._fernet:
            try:
                decrypted = self._fernet.decrypt(blob.encode())
                return json.loads(decrypted)
            except InvalidToken:
                raise ValueError("Cannot decrypt credentials — key mismatch or corrupted data.")
        # Fallback: base64
        import base64
        return json.loads(base64.b64decode(blob.encode()))

    def redact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of the credential dict with sensitive values masked."""
        SENSITIVE = {"secret_key", "client_secret", "service_account_json", "password", "token"}
        return {
            k: ("***REDACTED***" if k.lower() in SENSITIVE else v)
            for k, v in data.items()
        }


# Module-level singleton
_manager: CredentialManager | None = None


def get_credential_manager() -> CredentialManager:
    global _manager
    if _manager is None:
        _manager = CredentialManager()
    return _manager

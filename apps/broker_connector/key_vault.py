"""
API key vault — encryption/decryption for broker credentials.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC).
Keys are encrypted before storage and decrypted only at order execution time.
"""

import logging
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_fernet():
    """Get a Fernet instance using the configured encryption key."""
    key = settings.ENCRYPTION_KEY
    if not key:
        raise ValueError(
            "ENCRYPTION_KEY is not set. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_key(plaintext: str) -> str:
    """
    Encrypt a plaintext API key for storage.

    Args:
        plaintext: The raw API key string.

    Returns:
        Encrypted string safe for database storage.
    """
    if not plaintext:
        return ""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    """
    Decrypt an encrypted API key for use.

    Args:
        ciphertext: The encrypted string from the database.

    Returns:
        Decrypted plaintext API key.

    Raises:
        ValueError: If decryption fails (wrong key or corrupted data).
    """
    if not ciphertext:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt API key — invalid token or wrong encryption key")
        raise ValueError("Failed to decrypt API key. Check ENCRYPTION_KEY.")


def mask_key(key: str) -> str:
    """
    Mask an API key for safe display.

    Args:
        key: The plaintext or encrypted key.

    Returns:
        Masked string showing only last 4 characters.
    """
    if not key or len(key) < 5:
        return "****"
    return "****" + key[-4:]

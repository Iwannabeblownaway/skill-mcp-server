"""
Security utilities for the application.

Provides functions for API key generation, password hashing, and token handling.
"""

import secrets
import hashlib
import hmac
from typing import Optional

from app.config import settings


def generate_api_key(length: Optional[int] = None) -> str:
    """
    Generate a cryptographically secure API key.

    Args:
        length: Length of the API key in bytes (default: API_KEY_LENGTH from settings)

    Returns:
        A URL-safe base64-encoded API key string
    """
    if length is None:
        length = settings.API_KEY_LENGTH
    return secrets.token_urlsafe(length)


def generate_secret(length: int = 32) -> str:
    """
    Generate a cryptographically secure secret.

    Args:
        length: Length of the secret in bytes

    Returns:
        A URL-safe base64-encoded secret string
    """
    return secrets.token_urlsafe(length)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.

    Uses SHA-256 to create a deterministic hash of the API key.
    This allows verification without storing the actual key.

    Args:
        api_key: The API key to hash

    Returns:
        Hex digest of the hashed key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.

    Args:
        api_key: The plain API key to verify
        hashed_key: The stored hash of the API key

    Returns:
        True if the key matches the hash, False otherwise
    """
    return hmac.compare_digest(hash_api_key(api_key), hashed_key)


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash a password using PBKDF2 with SHA-256.

    Args:
        password: The plain text password to hash
        salt: Optional salt (generated if not provided)

    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,  # iterations
    ).hex()

    return hashed, salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: The plain text password to verify
        hashed_password: The stored hashed password
        salt: The salt used during hashing

    Returns:
        True if the password matches, False otherwise
    """
    computed_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, hashed_password)


def generate_token(length: int = 32) -> str:
    """
    Generate a random token for various purposes.

    Args:
        length: Length of the token in bytes

    Returns:
        A URL-safe base64-encoded token string
    """
    return secrets.token_urlsafe(length)

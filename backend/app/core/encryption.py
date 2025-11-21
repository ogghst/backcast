"""Encryption utilities for API key management using Fernet symmetric encryption."""

from cryptography.fernet import Fernet

from app.core.config import settings


def get_fernet_key() -> bytes:
    """
    Get Fernet encryption key from settings.

    The key is loaded from settings.FERNET_KEY which should be a base64-encoded
    Fernet key (32 bytes).

    Returns:
        bytes: Fernet key for encryption/decryption

    Raises:
        ValueError: If FERNET_KEY is not set or invalid
    """
    fernet_key_str = settings.FERNET_KEY

    if not fernet_key_str:
        raise ValueError(
            "FERNET_KEY environment variable must be set. "
            "Generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )

    # Validate that it's a valid Fernet key by trying to create a Fernet instance
    try:
        key_bytes = fernet_key_str.encode()
        # Try to create Fernet instance to validate key format
        Fernet(key_bytes)
        return key_bytes
    except Exception as e:
        raise ValueError(
            f"Invalid FERNET_KEY format: {str(e)}. "
            "Key must be a base64-encoded 32-byte Fernet key."
        ) from e


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key using Fernet symmetric encryption.

    Args:
        api_key: Plain text API key to encrypt

    Returns:
        str: Base64-encoded encrypted API key

    Raises:
        ValueError: If FERNET_KEY environment variable is not set
    """
    fernet_key = get_fernet_key()
    f = Fernet(fernet_key)
    encrypted_bytes = f.encrypt(api_key.encode())
    # Return as base64 string for storage
    return encrypted_bytes.decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an encrypted API key using Fernet symmetric encryption.

    Args:
        encrypted_key: Base64-encoded encrypted API key

    Returns:
        str: Decrypted plain text API key

    Raises:
        ValueError: If decryption fails (invalid key, wrong key, or invalid format)
        ValueError: If FERNET_KEY environment variable is not set
    """
    if not encrypted_key:
        raise ValueError("Encrypted API key cannot be empty")

    fernet_key = get_fernet_key()
    f = Fernet(fernet_key)

    try:
        decrypted_bytes = f.decrypt(encrypted_key.encode())
        return decrypted_bytes.decode()
    except Exception as e:
        raise ValueError(
            f"Invalid encrypted API key: {str(e)}. "
            "The key may be corrupted or was encrypted with a different key."
        ) from e

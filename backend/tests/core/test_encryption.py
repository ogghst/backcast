"""Tests for encryption utilities."""

from unittest.mock import patch

import pytest

from app.core.config import settings
from app.core.encryption import decrypt_api_key, encrypt_api_key, get_fernet_key


def test_get_fernet_key_from_environment() -> None:
    """Test that Fernet key is loaded from settings."""
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key()
    test_key_str = test_key.decode()

    with patch.object(settings, "FERNET_KEY", test_key_str):
        key = get_fernet_key()
        assert key == test_key


def test_get_fernet_key_missing_raises_error() -> None:
    """Test that missing FERNET_KEY raises ValueError."""
    with patch.object(settings, "FERNET_KEY", None):
        with pytest.raises(
            ValueError, match="FERNET_KEY environment variable must be set"
        ):
            get_fernet_key()


def test_encrypt_api_key() -> None:
    """Test encrypting an API key."""
    # Generate a valid Fernet key
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        api_key = "sk-test123456789abcdef"
        encrypted = encrypt_api_key(api_key)

        # Verify encrypted value is different from original
        assert encrypted != api_key
        assert isinstance(encrypted, str)
        # Encrypted value should be base64 encoded (Fernet format)
        assert len(encrypted) > 0


def test_decrypt_api_key() -> None:
    """Test decrypting an API key."""
    # Generate a valid Fernet key
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        api_key = "sk-test123456789abcdef"
        encrypted = encrypt_api_key(api_key)

        # Decrypt and verify
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == api_key


def test_encrypt_decrypt_round_trip() -> None:
    """Test that encrypting and decrypting produces the original value."""
    # Generate a valid Fernet key
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        api_key = "sk-proj-abc123xyz789testkey"
        encrypted = encrypt_api_key(api_key)
        decrypted = decrypt_api_key(encrypted)

        assert decrypted == api_key


def test_decrypt_api_key_invalid_key_raises_error() -> None:
    """Test that decrypting with wrong key raises ValueError."""
    # Generate two different Fernet keys
    from cryptography.fernet import Fernet

    key1 = Fernet.generate_key()
    key2 = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", key1.decode()):
        api_key = "sk-test123456789abcdef"
        encrypted = encrypt_api_key(api_key)

    # Try to decrypt with different key
    with patch.object(settings, "FERNET_KEY", key2.decode()):
        with pytest.raises(ValueError, match="Invalid encrypted API key"):
            decrypt_api_key(encrypted)


def test_decrypt_api_key_invalid_format_raises_error() -> None:
    """Test that decrypting invalid format raises ValueError."""
    # Generate a valid Fernet key
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Try to decrypt invalid data
        with pytest.raises(ValueError, match="Invalid encrypted API key"):
            decrypt_api_key("invalid_encrypted_data")


def test_encrypt_api_key_empty_string() -> None:
    """Test encrypting an empty string."""
    # Generate a valid Fernet key
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        encrypted = encrypt_api_key("")
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == ""


def test_encrypt_api_key_long_string() -> None:
    """Test encrypting a long API key."""
    # Generate a valid Fernet key
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Long API key (OpenAI keys can be up to ~100 characters)
        long_key = "sk-proj-" + "a" * 100
        encrypted = encrypt_api_key(long_key)
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == long_key

"""Provider factory functions for auth and user directory abstractions."""

from app.core.providers.auth import AuthProvider, LocalAuthProvider
from app.core.providers.user import LocalUserProvider, UserProvider

_auth_provider: AuthProvider | None = None
_user_provider: UserProvider | None = None


def get_auth_provider() -> AuthProvider:
    """Get the global auth provider singleton.

    Reads settings.AUTH_PROVIDER to select the implementation.
    Currently only "local" is supported.
    """
    global _auth_provider
    if _auth_provider is None:
        from app.core.config import settings

        if settings.AUTH_PROVIDER != "local":
            raise ValueError(
                f"Unsupported AUTH_PROVIDER: {settings.AUTH_PROVIDER!r}. "
                "Supported: 'local'"
            )
        _auth_provider = LocalAuthProvider()
    return _auth_provider


def get_user_provider() -> UserProvider:
    """Get the global user provider singleton.

    Reads settings.USER_PROVIDER to select the implementation.
    Currently only "local" is supported.
    """
    global _user_provider
    if _user_provider is None:
        from app.core.config import settings

        if settings.USER_PROVIDER != "local":
            raise ValueError(
                f"Unsupported USER_PROVIDER: {settings.USER_PROVIDER!r}. "
                "Supported: 'local'"
            )
        _user_provider = LocalUserProvider()
    return _user_provider


def set_auth_provider(provider: AuthProvider) -> None:
    """Override the global auth provider (for testing)."""
    global _auth_provider
    _auth_provider = provider


def set_user_provider(provider: UserProvider) -> None:
    """Override the global user provider (for testing)."""
    global _user_provider
    _user_provider = provider


__all__ = [
    "AuthProvider",
    "LocalAuthProvider",
    "UserProvider",
    "LocalUserProvider",
    "get_auth_provider",
    "get_user_provider",
    "set_auth_provider",
    "set_user_provider",
]

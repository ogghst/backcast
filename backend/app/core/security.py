from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# Patch passlib's bcrypt handler to handle wrap bug detection with bcrypt 4.x
# bcrypt 4.x has a 72-byte password limit that can cause issues during
# passlib's internal wrap bug detection. The _finalize_backend_mixin method
# calls detect_wrap_bug which tries to hash a 255-byte password, triggering
# bcrypt's 72-byte limit. This patch catches and handles the error gracefully.
try:
    from passlib.handlers import bcrypt as _passlib_bcrypt

    # Patch _finalize_backend_mixin to handle bcrypt 4.x 72-byte limit
    # This is a classmethod on backend classes. We need to patch all of them.
    def create_patched_finalize(
        original_finalize: Callable[..., Any],
    ) -> Callable[..., Any]:
        def _patched_finalize_backend_mixin(
            mixin_cls: Any, backend: Any, dryrun: bool = False
        ) -> Any:
            try:
                return original_finalize(mixin_cls, backend, dryrun)
            except ValueError as e:
                # Ignore "password cannot be longer than 72 bytes" errors
                # during wrap bug detection - this is expected with bcrypt 4.x
                if "password cannot be longer than 72 bytes" in str(e):
                    # Log warning but continue - wrap bug detection is not critical
                    # The handler will still work for normal passwords
                    import logging

                    logging.getLogger(__name__).warning(
                        "bcrypt wrap bug detection skipped due to 72-byte limit in bcrypt 4.x"
                    )
                    # Mark as initialized and return True to indicate successful initialization
                    mixin_cls._workrounds_initialized = True
                    return True
                raise

        # Wrap as classmethod
        return classmethod(_patched_finalize_backend_mixin)  # type: ignore[return-value]

    # Patch all backend classes that have _finalize_backend_mixin
    for cls_name in [
        "_BcryptBackend",
        "_BcryptorBackend",
        "_BuiltinBackend",
        "_OsCryptBackend",
        "_PyBcryptBackend",
    ]:
        cls = getattr(_passlib_bcrypt, cls_name, None)
        if cls and hasattr(cls, "_finalize_backend_mixin"):
            original_finalize = cls._finalize_backend_mixin.__func__
            cls._finalize_backend_mixin = create_patched_finalize(original_finalize)
except (ImportError, AttributeError):
    # If patching fails, continue with normal initialization
    # The error will occur on first password hash, but we'll handle it then
    pass

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

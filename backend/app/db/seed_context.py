"""Seed operation context management.

Provides a thread-safe way to mark operations as seed data imports,
allowing certain validations (like rejecting client-provided entity IDs)
to be bypassed during seeding while maintaining strict validation for
normal API operations.
"""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

# Context variable to track if we're in a seed operation
# ContextVars are thread-safe and async-safe
_seed_operation: ContextVar[bool] = ContextVar("_seed_operation", default=False)


@contextmanager
def seed_operation() -> Generator[None, None, None]:
    """Context manager to mark current operation as seed data import.

    Within this context, validators will allow explicit entity IDs to be
    provided in create requests, which is necessary for deterministic seeding.

    Outside this context (normal API operations), providing entity IDs will
    be rejected to prevent clients from bypassing proper ID generation.

    Example:
        ```python
        async def seed_wbes(self, session: AsyncSession) -> None:
            with seed_operation():  # Allow explicit IDs
                for wbe_data in wbe_json:
                    wbe_in = WBECreate(**wbe_data)  # Can include wbe_id
                    await wbe_service.create_wbe(wbe_in, actor_id)
        ```

        ```python
        # Normal API call - IDs rejected
        wbe_in = WBECreate(
            wbe_id=UUID("..."),  # This will raise ValueError!
            code="WBE-001",
            ...
        )
        ```
    """
    token = _seed_operation.set(True)
    try:
        yield
    finally:
        _seed_operation.reset(token)


def is_seed_operation() -> bool:
    """Check if current execution context is a seed operation.

    Returns:
        True if currently within a seed_operation() context, False otherwise.
    """
    return _seed_operation.get()

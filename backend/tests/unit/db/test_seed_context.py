"""Unit tests for seed_context module."""

import asyncio

import pytest

from app.db.seed_context import is_seed_operation, seed_operation


def test_seed_operation_default_is_false() -> None:
    """Test that is_seed_operation() returns False by default."""
    assert is_seed_operation() is False


def test_seed_operation_context_manager() -> None:
    """Test that seed_operation() context manager works correctly."""
    assert is_seed_operation() is False
    with seed_operation():
        assert is_seed_operation() is True
    assert is_seed_operation() is False


def test_seed_operation_nested() -> None:
    """Test that nested seed_operation() contexts work correctly."""
    assert is_seed_operation() is False
    with seed_operation():
        assert is_seed_operation() is True
        with seed_operation():
            assert is_seed_operation() is True
        assert is_seed_operation() is True
    assert is_seed_operation() is False


@pytest.mark.asyncio
async def test_seed_operation_async_isolation() -> None:
    """Test that is_seed_operation() is isolated between async tasks."""

    async def run_in_context():
        with seed_operation():
            assert is_seed_operation() is True
            await asyncio.sleep(0.1)
            assert is_seed_operation() is True
            return True

    async def run_without_context():
        assert is_seed_operation() is False
        await asyncio.sleep(0.05)
        assert is_seed_operation() is False
        return True

    results = await asyncio.gather(run_in_context(), run_without_context())
    assert all(results)
    assert is_seed_operation() is False

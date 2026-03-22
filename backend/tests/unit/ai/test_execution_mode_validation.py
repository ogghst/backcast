"""Unit tests for execution mode validation in WebSocket schemas.

Tests cover:
- Pydantic validation of execution_mode field
- Default value (standard)
- Valid values (safe, standard, expert)
- Invalid values are rejected
"""

import pytest
from pydantic import ValidationError

from app.models.schemas.ai import WSChatRequest


def test_execution_mode_accepts_valid_values():
    """T-2.4: execution_mode field accepts valid values.

    Arrange & Act:
        - Create WSChatRequest with each valid execution_mode

    Assert:
        - All valid modes are accepted
    """
    # Test all valid modes
    for mode in ["safe", "standard", "expert"]:
        request = WSChatRequest(
            message="test message",
            assistant_config_id="00000000-0000-0000-0000-000000000000",
            execution_mode=mode,  # type: ignore
        )
        assert request.execution_mode == mode


def test_execution_mode_defaults_to_standard():
    """T-2.4: execution_mode field defaults to 'standard'.

    Arrange & Act:
        - Create WSChatRequest without execution_mode

    Assert:
        - execution_mode defaults to 'standard'
    """
    request = WSChatRequest(
        message="test message",
        assistant_config_id="00000000-0000-0000-0000-000000000000",
    )
    assert request.execution_mode == "standard"


def test_execution_mode_rejects_invalid_values():
    """T-2.4: execution_mode field rejects invalid values.

    Arrange & Act:
        - Try to create WSChatRequest with invalid execution_mode

    Assert:
        - Pydantic raises ValidationError
    """
    with pytest.raises(ValidationError) as exc_info:
        WSChatRequest(
            message="test message",
            assistant_config_id="00000000-0000-0000-0000-000000000000",
            execution_mode="invalid",  # type: ignore
        )

    # Verify error mentions execution_mode
    errors = exc_info.value.errors()
    assert any("execution_mode" in str(err.get("loc", [])) for err in errors)


def test_execution_mode_case_sensitive():
    """T-2.4: execution_mode field is case-sensitive.

    Arrange & Act:
        - Try to create WSChatRequest with uppercase mode

    Assert:
        - Pydantic raises ValidationError
    """
    with pytest.raises(ValidationError):
        WSChatRequest(
            message="test message",
            assistant_config_id="00000000-0000-0000-0000-000000000000",
            execution_mode="SAFE",  # type: ignore - should be lowercase
        )

"""Unit tests for AI tool risk categorization.

Tests T-001 to T-003 from the plan:
- T-001: test_tool_metadata_has_risk_level_field
- T-002: test_risk_level_enum_only_accepts_valid_values
- T-003: test_ai_tool_decorator_attaches_risk_level
"""

import pytest

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolMetadata


class TestRiskLevelEnum:
    """Test RiskLevel enum validation (T-002)."""

    def test_risk_level_enum_has_correct_values(self) -> None:
        """Test that RiskLevel enum has LOW, HIGH, CRITICAL values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_risk_level_enum_only_accepts_valid_values(self) -> None:
        """Test that RiskLevel only accepts valid string values.

        This test verifies that RiskLevel validates "low", "high", "critical"
        and rejects invalid values.
        """
        # Valid values should work
        assert RiskLevel("low") == RiskLevel.LOW
        assert RiskLevel("high") == RiskLevel.HIGH
        assert RiskLevel("critical") == RiskLevel.CRITICAL

        # Invalid values should raise ValueError
        with pytest.raises(ValueError, match="is not a valid RiskLevel"):
            RiskLevel("invalid")  # type: ignore[call-arg]

        with pytest.raises(ValueError, match="is not a valid RiskLevel"):
            RiskLevel("medium")  # type: ignore[call-arg]


class TestToolMetadataRiskLevel:
    """Test ToolMetadata risk_level field (T-001)."""

    def test_tool_metadata_has_risk_level_field(self) -> None:
        """Test that ToolMetadata dataclass has risk_level: RiskLevel field.

        This test verifies the FR-1 requirement: All tools tagged with risk_level.
        """
        metadata = ToolMetadata(
            name="test_tool",
            description="Test tool",
            permissions=["read"],
            risk_level=RiskLevel.CRITICAL,
        )

        assert metadata.risk_level == RiskLevel.CRITICAL
        assert isinstance(metadata.risk_level, RiskLevel)

    def test_risk_level_default_is_high(self) -> None:
        """Test that risk_level defaults to RiskLevel.HIGH for backward compatibility.

        This test verifies the backward compatibility requirement from the plan:
        "Existing tools without risk_level default to 'high'"
        """
        # Create metadata without specifying risk_level
        metadata = ToolMetadata(
            name="test_tool",
            description="Test tool",
            permissions=["read"],
        )

        # Should default to HIGH (safe by default)
        assert metadata.risk_level == RiskLevel.HIGH

    def test_tool_metadata_to_dict_includes_risk_level(self) -> None:
        """Test that ToolMetadata.to_dict() includes risk_level.

        This verifies serialization compatibility for API responses.
        """
        metadata = ToolMetadata(
            name="test_tool",
            description="Test tool",
            permissions=["read"],
            risk_level=RiskLevel.LOW,
        )

        result = metadata.to_dict()

        assert "risk_level" in result
        assert result["risk_level"] == "low"  # Serialized as string


class TestAIToolDecoratorRiskLevel:
    """Test @ai_tool decorator risk_level parameter (T-003)."""

    def test_ai_tool_decorator_attaches_risk_level(self) -> None:
        """Test that @ai_tool(risk_level="critical") sets _tool_metadata.risk_level.

        This test verifies that the decorator properly attaches risk_level
        to the tool metadata for risk checking in Phase 2.
        """
        from typing import Annotated

        from langchain_core.tools import InjectedToolArg

        @ai_tool(
            name="test_critical_tool",
            description="A critical test tool",
            permissions=["admin"],
            risk_level=RiskLevel.CRITICAL,
        )
        async def test_tool(
            value: str,
            context: Annotated[object, InjectedToolArg] = None,  # type: ignore[assignment]
        ) -> dict[str, str]:
            """Test tool function.

            Args:
                value: Input value to return
                context: Injected tool execution context

            Returns:
                Dictionary with result
            """
            return {"result": value}

        # Verify the tool has metadata attached
        assert hasattr(test_tool, "_tool_metadata")
        metadata = test_tool._tool_metadata  # type: ignore[attr-defined]

        # Verify risk_level is set correctly
        assert isinstance(metadata, ToolMetadata)
        assert metadata.risk_level == RiskLevel.CRITICAL

    def test_ai_tool_decorator_defaults_to_high(self) -> None:
        """Test that @ai_tool without risk_level defaults to RiskLevel.HIGH.

        This verifies backward compatibility: existing tools without risk_level
        annotation will default to HIGH (safe by default).
        """
        from typing import Annotated

        from langchain_core.tools import InjectedToolArg

        @ai_tool(
            name="test_default_tool",
            description="A test tool with default risk level",
            permissions=["read"],
        )
        async def test_tool(
            context: Annotated[object, InjectedToolArg] = None,  # type: ignore[assignment]
        ) -> dict[str, str]:
            """Test tool function.

            Args:
                context: Injected tool execution context

            Returns:
                Dictionary with result
            """
            return {"result": "ok"}

        # Verify the tool has metadata with default risk_level
        assert hasattr(test_tool, "_tool_metadata")
        metadata = test_tool._tool_metadata  # type: ignore[attr-defined]

        assert metadata.risk_level == RiskLevel.HIGH


class TestExecutionModeEnum:
    """Test ExecutionMode enum for Phase 2."""

    def test_execution_mode_enum_has_correct_values(self) -> None:
        """Test that ExecutionMode enum has SAFE, STANDARD, EXPERT values.

        This enum will be used in Phase 2 for risk checking but is defined
        in Phase 1 for completeness.
        """
        from app.ai.tools.types import ExecutionMode

        assert ExecutionMode.SAFE.value == "safe"
        assert ExecutionMode.STANDARD.value == "standard"
        assert ExecutionMode.EXPERT.value == "expert"

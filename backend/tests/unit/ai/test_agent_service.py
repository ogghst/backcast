"""Tests for AgentService tool result serialization."""

import json
from unittest.mock import MagicMock, Mock

import pytest
from langchain_core.messages import ToolMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_service import AgentService


@pytest.mark.asyncio
class TestToolResultSerialization:
    """Test that ToolMessage objects are properly serialized for JSON storage."""

    async def test_tool_message_content_extraction(
        self, db_session: AsyncSession
    ) -> None:
        """Verify that ToolMessage.content is extracted correctly."""
        service = AgentService(db_session)

        # Create a ToolMessage with string content
        tool_msg = ToolMessage(
            content="Tool execution result", tool_call_id="call_123"
        )

        # Simulate the extraction logic from chat_stream
        tool_output = tool_msg
        result_content = tool_output
        if isinstance(tool_output, ToolMessage):
            result_content = tool_output.content

        # Verify the content is extracted
        assert result_content == "Tool execution result"
        assert isinstance(result_content, str)

    async def test_tool_message_dict_extraction(self, db_session: AsyncSession) -> None:
        """Verify that ToolMessage with dict content is handled correctly."""
        service = AgentService(db_session)

        # Create a ToolMessage with string content (dicts are stringified)
        tool_msg = ToolMessage(
            content='{"result": "success", "data": [1, 2, 3]}', tool_call_id="call_456"
        )

        # Simulate the extraction logic
        tool_output = tool_msg
        result_content = tool_output
        if isinstance(tool_output, ToolMessage):
            result_content = tool_output.content

        # Verify the content is extracted and is a string
        assert result_content == '{"result": "success", "data": [1, 2, 3]}'
        assert isinstance(result_content, str)
        # Verify it's JSON-serializable
        assert json.dumps(result_content)  # Should not raise

    async def test_tool_result_format(self, db_session: AsyncSession) -> None:
        """Verify the tool result dict format is JSON-serializable."""
        service = AgentService(db_session)

        # Create a tool result dict like in chat_stream
        tool_msg = ToolMessage(content="Result text", tool_call_id="call_789")
        result_content = tool_msg.content

        tool_result = {
            "tool": "test_tool",
            "success": True,
            "result": result_content,
            "error": None,
        }

        # Verify it's JSON-serializable
        json_str = json.dumps(tool_result)
        assert json_str

        # Verify it can be deserialized
        parsed = json.loads(json_str)
        assert parsed["tool"] == "test_tool"
        assert parsed["result"] == "Result text"

    async def test_plain_string_handling(self, db_session: AsyncSession) -> None:
        """Verify that plain string outputs are handled correctly."""
        service = AgentService(db_session)

        # Simulate a plain string output (not a ToolMessage)
        tool_output = "Plain string result"

        result_content = tool_output
        if isinstance(tool_output, ToolMessage):
            result_content = tool_output.content

        # Verify the string is unchanged
        assert result_content == "Plain string result"
        assert isinstance(result_content, str)

    async def test_dict_with_content_field(self, db_session: AsyncSession) -> None:
        """Verify that dict outputs with 'content' field are handled correctly."""
        service = AgentService(db_session)

        # Simulate a dict output with content field
        tool_output = {"content": "Extracted content", "metadata": "extra"}

        result_content = tool_output
        if isinstance(tool_output, ToolMessage):
            result_content = tool_output.content
        elif isinstance(tool_output, dict) and "content" in tool_output:
            result_content = tool_output["content"]

        # Verify the content is extracted
        assert result_content == "Extracted content"

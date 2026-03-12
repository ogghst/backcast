import pytest
from app.api.routes.ai_config import list_ai_tools

@pytest.mark.asyncio
async def test_getting_ai_tools_list_returns_valid_schemas() -> None:
    # Act
    tools = await list_ai_tools()
    
    # Assert
    assert isinstance(tools, list)
    assert len(tools) > 0, "No tools returned from registry"
    
    # Verify basic schema shape of first tool
    tool = tools[0]
    # tool is an AIToolPublic schema instance
    assert tool.name
    assert tool.description
    assert isinstance(tool.permissions, list)
    assert hasattr(tool, "category")
    assert tool.version

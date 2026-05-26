"""Test Cost Element Type AI tools.

Tests the Cost Element Type AI tools following TDD methodology:
1. find_cost_element_types
2. create_cost_element_type
3. update_cost_element_type
4. delete_cost_element_type
"""

from collections.abc import Generator
from unittest.mock import patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.registry import get_registry
from app.ai.tools.templates.cost_element_template import (
    create_cost_element_type,
    delete_cost_element_type,
    find_cost_element_types,
    update_cost_element_type,
)
from app.ai.tools.types import RiskLevel, ToolContext
from app.api.dependencies.auth import get_current_user
from app.core.rbac_unified import (
    UnifiedRBACService,
    set_unified_rbac_service,
)
from app.main import app
from app.models.domain.department import Department
from app.models.domain.user import User
from app.models.schemas.cost_element_type import (
    CostElementTypeCreate,
)
from app.models.schemas.department import DepartmentCreate
from app.services.cost_element_type_service import CostElementTypeService
from app.services.department import DepartmentService
from tests.conftest import MockUnifiedRBACService

# Patch target for overriding ToolContext.session to use the test db_session
# instead of creating a task-scoped session from the production engine.
_GET_TOOL_SESSION_PATCH = "app.db.session.get_tool_session"

# Mock admin user for auth
mock_admin_user = User(
    id=uuid4(),
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    full_name="Admin User",
    hashed_password="hash",
    created_by=uuid4(),
)
def mock_get_current_user() -> User:
    return mock_admin_user
@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    """Override authentication and RBAC for all tests."""
    app.dependency_overrides[get_current_user] = mock_get_current_user

    set_unified_rbac_service(MockUnifiedRBACService())

    yield

    set_unified_rbac_service(UnifiedRBACService())
    app.dependency_overrides = {}
@pytest_asyncio.fixture
async def test_department(db_session: AsyncSession) -> Department:
    """Create a test department for cost element type tests."""
    service = DepartmentService(db_session)
    dept_data = DepartmentCreate(
        code="TEST",
        name="Test Department",
        description="Test department for AI tools",
    )
    department = await service.create_department(
        dept_in=dept_data,
        actor_id=mock_admin_user.user_id,
    )
    return department
# =============================================================================
# TOOL DISCOVERY TESTS
# =============================================================================
def test_cost_element_type_tools_are_discovered() -> None:
    """Test that all 5 Cost Element Type tools are discovered and registered."""
    registry = get_registry()

    # Clear registry to start fresh
    registry._tools.clear()

    # Discover cost_element_template module
    registry.discover_and_register("app.ai.tools.templates.cost_element_template")

    tools = registry.get_all_metadata()
    tool_names = [tool.name for tool in tools]

    # Verify Cost Element Type tools are present
    assert "find_cost_element_types" in tool_names, (
        "Missing find_cost_element_types tool"
    )
    assert "create_cost_element_type" in tool_names, (
        "Missing create_cost_element_type tool"
    )
    assert "update_cost_element_type" in tool_names, (
        "Missing update_cost_element_type tool"
    )
    assert "delete_cost_element_type" in tool_names, (
        "Missing delete_cost_element_type tool"
    )
def test_cost_element_type_tools_metadata() -> None:
    """Test that Cost Element Type tools have correct metadata."""
    registry = get_registry()
    registry._tools.clear()
    registry.discover_and_register("app.ai.tools.templates.cost_element_template")

    tools = registry.get_all_metadata()
    tools_dict = {tool.name: tool for tool in tools}

    # Test find_cost_element_types metadata
    find_tool = tools_dict.get("find_cost_element_types")
    assert find_tool is not None
    assert find_tool.category == "cost-element-types"
    assert "cost-element-type-read" in find_tool.permissions

    # Test create_cost_element_type metadata
    create_tool = tools_dict.get("create_cost_element_type")
    assert create_tool is not None
    assert create_tool.category == "cost-element-types"
    assert "cost-element-type-create" in create_tool.permissions

    # Test update_cost_element_type metadata
    update_tool = tools_dict.get("update_cost_element_type")
    assert update_tool is not None
    assert update_tool.category == "cost-element-types"
    assert "cost-element-type-update" in update_tool.permissions

    # Test delete_cost_element_type metadata
    delete_tool = tools_dict.get("delete_cost_element_type")
    assert delete_tool is not None
    assert delete_tool.category == "cost-element-types"
    assert "cost-element-type-delete" in delete_tool.permissions
# =============================================================================
# TOOL FUNCTIONALITY TESTS
# =============================================================================
@pytest.mark.asyncio
async def test_find_cost_element_types_returns_list_with_simple_types(
    db_session: AsyncSession, test_department: Department
) -> None:
    """Test that find_cost_element_types list mode returns AI-friendly format."""
    # Create a test cost element type
    service = CostElementTypeService(db_session)
    type_data = CostElementTypeCreate(
        code="LABOR",
        name="Labor",
        description="Labor costs",
        department_id=test_department.department_id,
    )
    await service.create(type_data, actor_id=mock_admin_user.user_id)

    # Create tool context
    context = ToolContext(
        session=db_session,
        user_id=str(mock_admin_user.user_id),
        user_role="admin",
    )

    # Call the tool via ainvoke (LangChain BaseTool pattern)
    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await find_cost_element_types.ainvoke(
            {
                "context": context,
            }
        )

    # Verify result structure
    assert "cost_element_types" in result
    assert "total" in result
    assert "skip" in result
    assert "limit" in result
    assert isinstance(result["cost_element_types"], list)
    assert result["total"] >= 1

    # Verify AI-friendly format (strings, not UUID objects)
    if result["cost_element_types"]:
        cet = result["cost_element_types"][0]
        assert isinstance(cet["id"], str)
        assert isinstance(cet["code"], str)
        assert isinstance(cet["name"], str)
        assert isinstance(cet["department_id"], str)
@pytest.mark.asyncio
async def test_find_cost_element_types_with_department_filter(
    db_session: AsyncSession, test_department: Department
) -> None:
    """Test that find_cost_element_types filters by department_id."""
    # Create test cost element types
    service = CostElementTypeService(db_session)
    type_data = CostElementTypeCreate(
        code="MAT",
        name="Materials",
        description="Material costs",
        department_id=test_department.department_id,
    )
    await service.create(type_data, actor_id=mock_admin_user.user_id)

    # Create tool context
    context = ToolContext(
        session=db_session,
        user_id=str(mock_admin_user.user_id),
        user_role="admin",
    )

    # Test filtering by department
    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await find_cost_element_types.ainvoke(
            {
                "department_id": str(test_department.department_id),
                "context": context,
            }
        )

    assert "error" not in result
    assert result["total"] >= 1
    for cet in result["cost_element_types"]:
        assert cet["department_id"] == str(test_department.department_id)
@pytest.mark.asyncio
async def test_find_cost_element_types_with_search(
    db_session: AsyncSession, test_department: Department
) -> None:
    """Test that find_cost_element_types supports search functionality."""
    # Create test cost element type
    service = CostElementTypeService(db_session)
    type_data = CostElementTypeCreate(
        code="EQUIP",
        name="Equipment",
        description="Equipment costs",
        department_id=test_department.department_id,
    )
    await service.create(type_data, actor_id=mock_admin_user.user_id)

    # Create tool context
    context = ToolContext(
        session=db_session,
        user_id=str(mock_admin_user.user_id),
        user_role="admin",
    )

    # Test search
    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await find_cost_element_types.ainvoke(
            {
                "search": "Equip",
                "context": context,
            }
        )

    assert "error" not in result
    # Should find the "Equipment" type
    assert any(cet["name"] == "Equipment" for cet in result["cost_element_types"])
@pytest.mark.asyncio
async def test_find_cost_element_type_by_id_returns_dict_with_simple_types(
    db_session: AsyncSession, test_department: Department
) -> None:
    """Test that find_cost_element_types by ID returns AI-friendly format."""
    # Create a test cost element type
    service = CostElementTypeService(db_session)
    type_data = CostElementTypeCreate(
        code="SUB",
        name="Subcontracting",
        description="Subcontracting costs",
        department_id=test_department.department_id,
    )
    created_type = await service.create(type_data, actor_id=mock_admin_user.user_id)

    # Create tool context
    context = ToolContext(
        session=db_session,
        user_id=str(mock_admin_user.user_id),
        user_role="admin",
    )

    # Call the tool via ainvoke
    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await find_cost_element_types.ainvoke(
            {
                "cost_element_type_id": str(created_type.cost_element_type_id),
                "context": context,
            }
        )

    # Verify result structure and AI-friendly format
    assert "error" not in result
    assert isinstance(result["id"], str)
    assert isinstance(result["code"], str)
    assert isinstance(result["name"], str)
    assert isinstance(result["department_id"], str)
    assert result["code"] == "SUB"
    assert result["name"] == "Subcontracting"
@pytest.mark.asyncio
async def test_find_cost_element_type_by_id_not_found_error(db_session: AsyncSession) -> None:
    """Test that find_cost_element_types by ID returns error for non-existent ID."""
    # Create tool context
    context = ToolContext(
        session=db_session,
        user_id=str(mock_admin_user.user_id),
        user_role="admin",
    )

    # Call with non-existent ID
    fake_id = str(uuid4())
    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await find_cost_element_types.ainvoke(
            {
                "cost_element_type_id": fake_id,
                "context": context,
            }
        )

    # Verify error response
    assert "error" in result
    assert "not found" in result["error"].lower()
@pytest.mark.asyncio
async def test_create_cost_element_type_success(
    db_session: AsyncSession, test_department: Department
) -> None:
    """Test that create_cost_element_type creates a new type successfully."""
    # Create tool context
    context = ToolContext(
        session=db_session,
        user_id=str(mock_admin_user.user_id),
        user_role="admin",
    )

    # Call the tool via ainvoke
    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await create_cost_element_type.ainvoke(
            {
                "code": "TEST",
                "name": "Test Type",
                "description": "Test cost element type",
                "department_id": str(test_department.department_id),
                "context": context,
            }
        )

    # Verify result structure and AI-friendly format
    assert "error" not in result
    assert isinstance(result["id"], str)
    assert isinstance(result["code"], str)
    assert isinstance(result["name"], str)
    assert isinstance(result["department_id"], str)
    assert result["code"] == "TEST"
    assert result["name"] == "Test Type"
@pytest.mark.asyncio
async def test_create_cost_element_type_invalid_department_error(
    db_session: AsyncSession,
) -> None:
    """Test that create_cost_element_type returns error for invalid department."""
    # Create tool context
    context = ToolContext(
        session=db_session,
        user_id=str(mock_admin_user.user_id),
        user_role="admin",
    )

    # Call with non-existent department
    fake_dept_id = str(uuid4())
    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await create_cost_element_type.ainvoke(
            {
                "code": "TEST",
                "name": "Test Type",
                "department_id": fake_dept_id,
                "context": context,
            }
        )

    # Verify error response
    assert "error" in result
@pytest.mark.asyncio
async def test_update_cost_element_type_success(
    db_session: AsyncSession, test_department: Department
) -> None:
    """Test that update_cost_element_type updates an existing type."""
    # Create a test cost element type
    service = CostElementTypeService(db_session)
    type_data = CostElementTypeCreate(
        code="ORIG",
        name="Original Name",
        description="Original description",
        department_id=test_department.department_id,
    )
    created_type = await service.create(type_data, actor_id=mock_admin_user.user_id)

    # Create tool context
    context = ToolContext(
        session=db_session,
        user_id=str(mock_admin_user.user_id),
        user_role="admin",
    )

    # Call the tool to update via ainvoke
    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await update_cost_element_type.ainvoke(
            {
                "cost_element_type_id": str(created_type.cost_element_type_id),
                "name": "Updated Name",
                "description": "Updated description",
                "context": context,
            }
        )

    # Verify result structure and AI-friendly format
    assert "error" not in result
    assert isinstance(result["id"], str)
    assert isinstance(result["name"], str)
    assert result["name"] == "Updated Name"
@pytest.mark.asyncio
async def test_update_cost_element_type_not_found_error(
    db_session: AsyncSession,
) -> None:
    """Test that update_cost_element_type returns error for non-existent ID."""
    # Create tool context
    context = ToolContext(
        session=db_session,
        user_id=str(mock_admin_user.user_id),
        user_role="admin",
    )

    # Call with non-existent ID
    fake_id = str(uuid4())
    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await update_cost_element_type.ainvoke(
            {
                "cost_element_type_id": fake_id,
                "name": "Updated Name",
                "context": context,
            }
        )

    # Verify error response
    assert "error" in result
@pytest.mark.asyncio
async def test_delete_cost_element_type_success(
    db_session: AsyncSession, test_department: Department
) -> None:
    """Test that delete_cost_element_type soft deletes a type."""
    # Create a test cost element type
    service = CostElementTypeService(db_session)
    type_data = CostElementTypeCreate(
        code="DEL",
        name="To Delete",
        description="This will be deleted",
        department_id=test_department.department_id,
    )
    created_type = await service.create(type_data, actor_id=mock_admin_user.user_id)

    # Create tool context
    context = ToolContext(
        session=db_session,
        user_id=str(mock_admin_user.user_id),
        user_role="admin",
    )

    # Call the tool to delete via ainvoke
    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await delete_cost_element_type.ainvoke(
            {
                "cost_element_type_id": str(created_type.cost_element_type_id),
                "context": context,
            }
        )

    # Verify deletion response
    assert "error" not in result
    assert "id" in result
    assert "message" in result

    # Verify it was soft deleted (should not be found by get_by_id)
    deleted_type = await service.get_by_id(created_type.cost_element_type_id)
    assert deleted_type is None
@pytest.mark.asyncio
async def test_delete_cost_element_type_not_found_error(
    db_session: AsyncSession,
) -> None:
    """Test that delete_cost_element_type returns error for non-existent ID."""
    # Create tool context
    context = ToolContext(
        session=db_session,
        user_id=str(mock_admin_user.user_id),
        user_role="admin",
    )

    # Call with non-existent ID
    fake_id = str(uuid4())
    with patch(_GET_TOOL_SESSION_PATCH, return_value=db_session):
        result = await delete_cost_element_type.ainvoke(
            {
                "cost_element_type_id": fake_id,
                "context": context,
            }
        )

    # Verify error response
    assert "error" in result
# =============================================================================
# RISK LEVEL TESTS
# =============================================================================
class TestCostElementToolRiskLevels:
    """Test that cost element tools have appropriate risk levels.

    Verifies that all tools in cost_element_template.py are properly annotated
    with risk levels according to the plan guidelines:
    - low: Read-only tools, no side effects
    - high: Tools that modify data but with validation
    - critical: Tools that delete data, bulk operations, or sensitive actions
    """

    @pytest.mark.parametrize(
        "tool_name,expected_risk",
        [
            # Cost Element tools - LOW (read-only)
            ("find_cost_elements", RiskLevel.LOW),
            # Cost Element tools - HIGH (modify with validation)
            ("create_cost_element", RiskLevel.HIGH),
            ("update_cost_element", RiskLevel.HIGH),
            # Cost Element tools - CRITICAL (delete)
            ("delete_cost_element", RiskLevel.CRITICAL),
            # Cost Element Type tools - LOW (read-only)
            ("find_cost_element_types", RiskLevel.LOW),
            # Cost Element Type tools - HIGH (modify with validation)
            ("create_cost_element_type", RiskLevel.HIGH),
            ("update_cost_element_type", RiskLevel.HIGH),
            # Cost Element Type tools - CRITICAL (delete)
            ("delete_cost_element_type", RiskLevel.CRITICAL),
        ],
    )
    def test_tool_has_correct_risk_level(
        self, tool_name: str, expected_risk: RiskLevel
    ) -> None:
        """Test that each tool has the correct risk level annotation.

        Args:
            tool_name: Name of the tool function
            expected_risk: Expected risk level for the tool
        """
        from app.ai.tools import templates

        # Get the tool from the template module
        tool = getattr(templates.cost_element_template, tool_name)

        # Verify the tool has metadata
        assert hasattr(tool, "_tool_metadata"), f"{tool_name} missing _tool_metadata"

        # Get the metadata
        metadata = tool._tool_metadata  # type: ignore[attr-defined]

        # Verify risk level
        assert metadata.risk_level == expected_risk, (
            f"{tool_name} has risk_level={metadata.risk_level}, expected {expected_risk}"
        )

    def test_all_cost_element_type_tools_have_risk_level_metadata(self) -> None:
        """Test that all exported cost element type tools have risk_level metadata.

        This ensures no tools were missed during annotation.
        """
        from app.ai.tools import templates

        # List of all cost element type tool functions that should have risk_level
        tool_names = [
            "find_cost_element_types",
            "create_cost_element_type",
            "update_cost_element_type",
            "delete_cost_element_type",
        ]

        for tool_name in tool_names:
            tool = getattr(templates.cost_element_template, tool_name)
            assert hasattr(tool, "_tool_metadata"), (
                f"{tool_name} missing _tool_metadata"
            )
            metadata = tool._tool_metadata  # type: ignore[attr-defined]
            assert isinstance(metadata.risk_level, RiskLevel), (
                f"{tool_name} has invalid risk_level type"
            )
# =============================================================================
# INTEGRATION TEST
# =============================================================================
@pytest.mark.asyncio
async def test_cost_element_type_tools_endpoint_discovery(client: AsyncClient) -> None:
    """Test that the /tools endpoint includes Cost Element Type tools."""
    # Act
    r = await client.get("/api/v1/ai/config/tools")

    # Assert
    assert r.status_code == 200
    tools = r.json()
    tool_names = [tool.get("name") for tool in tools]

    # Verify Cost Element Type tools are present
    assert "find_cost_element_types" in tool_names
    assert "create_cost_element_type" in tool_names
    assert "update_cost_element_type" in tool_names
    assert "delete_cost_element_type" in tool_names

"""Package Type tool template for wrapping PackageTypeService methods.

This template provides AI tools for package type management. The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Package Types in Backcast:
- Package Types are configurable work package categories (replaces hardcoded enum)
- They are VERSIONABLE but NOT BRANCHABLE (organizational data, not project-specific)
- Admins can configure available types with code, name, color, and description
- Used for consistent work package categorization across projects

Usage:
    1. Import PackageTypeService methods
    2. Use @ai_tool decorator with proper permissions
    3. Use ToolContext for dependency injection
    4. Call service methods with context.session
    5. Return results in AI-friendly format
"""

import logging
from typing import Annotated, Any
from uuid import UUID

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext
from app.models.schemas.package_type import PackageTypeCreate, PackageTypeUpdate

logger = logging.getLogger(__name__)


# =============================================================================
# PACKAGE TYPE CRUD TOOLS
# =============================================================================


@ai_tool(
    name="list_package_types",
    description="List all available work package types. "
    "Returns package types with their code, name, color, and description.",
    permissions=["package-type-read"],
    category="package_types",
    risk_level=RiskLevel.LOW,
)
async def list_package_types(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List package types with optional search and pagination.

    Context: Provides database session and package type service for querying.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        search: Optional search term for code or name
        context: Injected tool execution context

    Returns:
        Dictionary with:
        - package_types: List of package type objects
        - total: Total number of package types matching filters
        - skip: Number of records skipped
        - limit: Maximum records returned

    Raises:
        ValueError: If invalid filter parameters

    Example:
        >>> result = await list_package_types(search="quality", limit=10)
        >>> print(f"Found {result['total']} package types")
        >>> for pt in result['package_types']:
        ...     print(f"- {pt['name']} ({pt['code']})")
    """
    try:
        from app.services.package_type_service import PackageTypeService

        service = PackageTypeService(context.session)

        # Call service method
        package_types, total = await service.get_package_types(
            search=search,
            skip=skip,
            limit=limit,
        )

        # Convert to AI-friendly format
        return {
            "package_types": [
                {
                    "id": str(pt.package_type_id),
                    "code": pt.code,
                    "name": pt.name,
                    "color": pt.color,
                    "description": pt.description,
                }
                for pt in package_types
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Error in list_package_types: {e}")
        return {"error": str(e)}


@ai_tool(
    name="get_package_type",
    description="Get detailed information about a specific package type by ID. "
    "Returns full package type details including code, name, color, and description.",
    permissions=["package-type-read"],
    category="package_types",
    risk_level=RiskLevel.LOW,
)
async def get_package_type(
    package_type_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get a single package type by ID.

    Context: Provides database session and package type service for retrieving data.

    Args:
        package_type_id: UUID of the package type to retrieve
        context: Injected tool execution context

    Returns:
        Dictionary with package type details or error if not found

    Raises:
        ValueError: If package_type_id is not a valid UUID format
        KeyError: If package type is not found

    Example:
        >>> result = await get_package_type("123e4567-e89b-12d3-a456-426614174000")
        >>> if "error" not in result:
        ...     print(f"Package Type: {result['name']}")
        ...     print(f"Code: {result['code']}")
    """
    try:
        from app.services.package_type_service import PackageTypeService

        service = PackageTypeService(context.session)

        # Call service method
        package_type = await service.get_by_id(UUID(package_type_id))

        if not package_type:
            return {"error": f"Package type {package_type_id} not found"}

        # Convert to AI-friendly format
        return {
            "id": str(package_type.package_type_id),
            "code": package_type.code,
            "name": package_type.name,
            "color": package_type.color,
            "description": package_type.description,
        }
    except ValueError:
        return {"error": f"Invalid package type ID: {package_type_id}"}
    except Exception as e:
        logger.error(f"Error in get_package_type: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_package_type",
    description="Create a new package type with code, name, color, is_quality flag, and optional description. "
    "Returns the created package type with all details.",
    permissions=["package-type-create"],
    category="package_types",
    risk_level=RiskLevel.HIGH,
)
async def create_package_type(
    code: str,
    name: str,
    color: str = "blue",
    is_quality: bool = False,
    description: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new package type.

    Context: Provides database session and package type service for creating.

    Args:
        code: Unique type code (e.g., "quality_impact")
        name: Display name (e.g., "Quality Impact")
        color: Ant Design color name (e.g., "red", "blue")
        is_quality: Whether this type contributes to COQ metrics (default: False)
        description: Optional description
        context: Injected tool execution context

    Returns:
        Dictionary with created package type details

    Raises:
        ValueError: If invalid input or duplicate code

    Example:
        >>> result = await create_package_type(
        ...     code="quality_impact",
        ...     name="Quality Impact",
        ...     color="red",
        ...     is_quality=True,
        ...     description="Quality-related work packages"
        ... )
        >>> print(f"Created package type with ID: {result['id']}")
    """
    try:
        from app.services.package_type_service import PackageTypeService

        service = PackageTypeService(context.session)

        # Create Pydantic schema
        type_data = PackageTypeCreate(
            code=code,
            name=name,
            color=color,
            is_quality=is_quality,
            description=description,
        )

        # Call service method
        package_type = await service.create(
            type_in=type_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(package_type.package_type_id),
            "code": package_type.code,
            "name": package_type.name,
            "color": package_type.color,
            "description": package_type.description,
            "message": "Package type created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_package_type: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_package_type",
    description="Update an existing package type with new information, including the is_quality flag. "
    "Only updates fields that are provided.",
    permissions=["package-type-update"],
    category="package_types",
    risk_level=RiskLevel.HIGH,
)
async def update_package_type(
    package_type_id: str,
    code: str | None = None,
    name: str | None = None,
    color: str | None = None,
    is_quality: bool | None = None,
    description: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing package type.

    Context: Provides database session and package type service for updating.

    Args:
        package_type_id: UUID of the package type to update
        code: New code (optional)
        name: New name (optional)
        color: New color (optional)
        is_quality: Whether this type contributes to COQ metrics (optional)
        description: New description (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated package type details

    Raises:
        ValueError: If package_type_id is invalid or no fields provided
        KeyError: If package type not found

    Example:
        >>> result = await update_package_type(
        ...     package_type_id="...",
        ...     name="Updated Quality Impact",
        ...     color="orange",
        ...     is_quality=True
        ... )
        >>> print(f"Updated package type: {result['name']}")
    """
    try:
        from app.services.package_type_service import PackageTypeService

        service = PackageTypeService(context.session)

        # Create update schema with only provided fields
        update_data = PackageTypeUpdate(
            code=code,
            name=name,
            color=color,
            is_quality=is_quality,
            description=description,
        )

        # Call service method
        package_type = await service.update(
            package_type_id=UUID(package_type_id),
            type_in=update_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(package_type.package_type_id),
            "code": package_type.code,
            "name": package_type.name,
            "color": package_type.color,
            "description": package_type.description,
            "message": "Package type updated successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"Package type {package_type_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_package_type: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_package_type",
    description="Soft delete a package type. "
    "The package type is marked as deleted but remains in the system for audit purposes.",
    permissions=["package-type-delete"],
    category="package_types",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_package_type(
    package_type_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a package type.

    Context: Provides database session and package type service for deletion.

    Args:
        package_type_id: UUID of the package type to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If package_type_id is invalid
        KeyError: If package type not found

    Example:
        >>> result = await delete_package_type("...")
        >>> print(f"Deleted package type: {result['id']}")
    """
    try:
        from app.services.package_type_service import PackageTypeService

        service = PackageTypeService(context.session)

        # Call service method
        await service.soft_delete(
            package_type_id=UUID(package_type_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": package_type_id,
            "message": "Package type deleted successfully",
        }
    except ValueError:
        return {"error": f"Invalid package type ID: {package_type_id}"}
    except KeyError:
        return {"error": f"Package type {package_type_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_package_type: {e}")
        return {"error": str(e)}

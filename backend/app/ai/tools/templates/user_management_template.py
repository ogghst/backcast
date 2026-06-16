"""User and Organizational Unit management tool template for wrapping service methods.

This template shows how to create AI tools for user and organizational unit management.
The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Users in Backcast:
- Users are temporal entities with full versioning support
- Password hashing is handled by the service
- Users have roles and permissions managed by RBAC
- User preferences are stored as JSON

Organizational Units in Backcast:
- Organizational Units are temporal entities with full versioning support
- Organizational Units can have optional managers (users)
- Used for organizing users and cost element types

Usage:
    1. Import UserService and OrganizationalUnitService methods
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
from app.ai.tools.templates._pagination import (
    BATCH_SIZE_LIMIT,
    calc_page_count,
    get_page_limit,
)
from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import RiskLevel, ToolContext
from app.api.dependencies.auth import invalidate_user_active_cache
from app.models.schemas.organizational_unit import (
    OrganizationalUnitCreate,
    OrganizationalUnitUpdate,
)
from app.models.schemas.user import UserRegister, UserUpdate

logger = logging.getLogger(__name__)


async def _resolve_user_role(session: Any, user_id: UUID) -> str:
    """Resolve a user's global role from UserRoleAssignment via unified RBAC.

    Args:
        session: Database session
        user_id: The user's root ID (user_id, not PK)

    Returns:
        First global role name, or "viewer" as fallback.
    """
    from app.core.rbac_unified import (
        get_unified_rbac_service,
        set_unified_rbac_session,
    )

    try:
        set_unified_rbac_session(session)
        roles = await get_unified_rbac_service().get_user_roles(user_id, "global", None)
        return roles[0] if roles else "viewer"
    finally:
        set_unified_rbac_session(None)


# =============================================================================
# USER CRUD TOOLS
# =============================================================================


@ai_tool(
    name="find_users",
    description=(
        "Find users by ID or search (matches code or name). "
        "Paginated — check 'total'/'has_more' and page forward with 'page'/'limit', "
        "narrow with 'search' first."
    ),
    permissions=["user-read"],
    category="users",
    risk_level=RiskLevel.LOW,
)
async def find_users(
    user_id: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find users by ID or search.

    Context: Provides database session and user service for querying users.

    Args:
        user_id: UUID of a specific user to retrieve (returns single)
        search: Optional search term
        page: Page number (1-based)
        limit: Maximum records per page (default from config, max 200)
        context: Injected tool execution context

    Returns:
        Single user dict if user_id provided, otherwise list result.

    Raises:
        ValueError: If user_id is not a valid UUID format
    """
    limit = get_page_limit(limit)
    skip = (page - 1) * limit

    try:
        log_temporal_context("find_users", context)

        from app.services.user import UserService

        service = UserService(context.session)

        # Single user lookup
        if user_id:
            user = await service.get_user(UUID(user_id))

            if not user:
                return add_temporal_metadata(
                    {"error": f"User {user_id} not found"}, context
                )

            role = await _resolve_user_role(context.session, user.user_id)
            return add_temporal_metadata(
                {
                    "id": str(user.user_id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "department": user.department,
                    "role": role,
                    "is_active": user.is_active,
                    "preferences": user.preferences if user.preferences else None,
                    "password_changed_at": user.password_changed_at.isoformat()
                    if user.password_changed_at
                    else None,
                },
                context,
            )

        # List users with proper count
        from typing import Any, cast

        from sqlalchemy import func, select

        from app.core.temporal_queries import is_current_version
        from app.models.domain.user import User

        # Count total active users
        count_stmt = (
            select(func.count())
            .select_from(User)
            .where(
                is_current_version(
                    cast(Any, User).valid_time,
                    cast(Any, User).deleted_at,
                )
            )
        )
        count_result = await context.session.execute(count_stmt)
        total = count_result.scalar_one()

        users = await service.get_users(skip=skip, limit=limit)

        user_list = []
        for user in users:
            role = await _resolve_user_role(context.session, user.user_id)
            user_list.append(
                {
                    "id": str(user.user_id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "department": user.department,
                    "role": role,
                    "is_active": user.is_active,
                    "preferences": user.preferences if user.preferences else None,
                }
            )

        return add_temporal_metadata(
            {
                "users": user_list,
                "total": total,
                "page": page,
                "page_count": calc_page_count(total, limit),
                "limit": limit,
                "has_more": page < calc_page_count(total, limit),
            },
            context,
        )
    except ValueError:
        return add_temporal_metadata({"error": f"Invalid user ID: {user_id}"}, context)
    except Exception as e:
        logger.error(f"Error in find_users: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="create_user",
    description="Create a new user.",
    permissions=["user-create"],
    category="users",
    risk_level=RiskLevel.HIGH,
)
async def create_user(
    email: str,
    full_name: str,
    password: str,
    department: str | None = None,
    role: str = "viewer",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new user.

    Context: Provides database session and user service for creating users.

    Args:
        email: User email address (must be unique)
        full_name: User's full name
        password: User password (will be hashed)
        department: Optional department name
        role: User role (default: "viewer")
        context: Injected tool execution context

    Returns:
        Dictionary with created user details (excluding password)

    Raises:
        ValueError: If invalid input or duplicate email

    Example:
        >>> result = await create_user(
        ...     email="john.doe@example.com",
        ...     full_name="John Doe",
        ...     password="securepassword123",
        ...     role="engineer"
        ... )
        >>> print(f"Created user with ID: {result['id']}")
    """
    try:
        from app.services.user import UserService

        service = UserService(context.session)

        # Create Pydantic schema
        user_data = UserRegister(
            email=email,
            full_name=full_name,
            password=password,
            department=department,
            role=role,
        )

        # Call service method (password hashing is handled by service)
        user = await service.create_user(
            user_in=user_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format (exclude password)
        role = await _resolve_user_role(context.session, user.user_id)
        return {
            "id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
            "role": role,
            "is_active": user.is_active,
            "message": "User created successfully (password hashed)",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_user: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_user",
    description="Update user fields.",
    permissions=["user-update"],
    category="users",
    risk_level=RiskLevel.HIGH,
)
async def update_user(
    user_id: str,
    full_name: str | None = None,
    department: str | None = None,
    role: str | None = None,
    password: str | None = None,
    is_active: bool | None = None,
    preferences: dict[str, Any] | None = None,  # noqa: ARG001  # Accept but reject
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing user.

    Context: Provides database session and user service for updating users.

    Args:
        user_id: UUID of the user to update
        full_name: New full name (optional)
        department: New department (optional)
        role: New role (optional)
        password: New password (optional, will be hashed)
        is_active: New active status (optional)
        preferences: User preferences (NOT SUPPORTED - use user preferences endpoint)
        context: Injected tool execution context

    Returns:
        Dictionary with updated user details

    Raises:
        ValueError: If user_id is invalid or no fields provided
        KeyError: If user not found

    Example:
        >>> result = await update_user(
        ...     user_id="...",
        ...     role="manager",
        ...     department="Engineering"
        ... )
        >>> print(f"Updated user role: {result['role']}")
    """
    try:
        # Check if preferences was provided (even if it's the only parameter)
        if preferences is not None:
            return {
                "error": "User preferences cannot be updated via this tool. "
                "Use the user preferences management feature instead."
            }

        from app.services.user import UserService

        service = UserService(context.session)

        # Create update schema with only provided fields
        # Note: preferences is NOT a valid field for UserUpdate
        # Only include password if it's a non-empty string (passlib rejects None/empty)
        update_kwargs = {
            "full_name": full_name,
            "department": department,
            "role": role,
            "is_active": is_active,
        }
        if password:  # Only include password if truthy (non-empty string)
            update_kwargs["password"] = password

        update_data = UserUpdate(**update_kwargs)

        # Call service method (password hashing handled by service)
        user = await service.update_user(
            user_id=UUID(user_id),
            user_in=update_data,
            actor_id=UUID(context.user_id),
        )

        invalidate_user_active_cache(UUID(user_id))

        # Convert to AI-friendly format
        role = await _resolve_user_role(context.session, user.user_id)
        return {
            "id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
            "role": role,
            "is_active": user.is_active,
            "message": "User updated successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"User {user_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_user: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_user",
    description="Delete a user.",
    permissions=["user-delete"],
    category="users",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_user(
    user_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a user.

    Context: Provides database session and user service for deletion.

    Args:
        user_id: UUID of the user to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If user_id is invalid
        KeyError: If user not found

    Example:
        >>> result = await delete_user("...")
        >>> print(f"Deleted user: {result['id']}")
    """
    try:
        from app.services.user import UserService

        service = UserService(context.session)

        # Call service method
        await service.delete_user(
            user_id=UUID(user_id),
            actor_id=UUID(context.user_id),
        )

        invalidate_user_active_cache(UUID(user_id))

        return {
            "id": user_id,
            "message": "User deleted successfully",
        }
    except ValueError:
        return {"error": f"Invalid user ID: {user_id}"}
    except KeyError:
        return {"error": f"User {user_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_user: {e}")
        return {"error": str(e)}


# =============================================================================
# ORGANIZATIONAL UNIT CRUD TOOLS
# =============================================================================


@ai_tool(
    name="find_organizational_units",
    description=(
        "Find organizational units by ID or search (matches code or name). "
        "Paginated — check 'total'/'has_more' and page forward with 'page'/'limit', "
        "narrow with 'search' first."
    ),
    permissions=["organizational-unit-read"],
    category="users",
    risk_level=RiskLevel.LOW,
)
async def find_organizational_units(
    organizational_unit_id: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find organizational units by ID or search.

    Context: Provides database session and organizational unit service for querying.

    Args:
        organizational_unit_id: UUID of a specific organizational unit to retrieve (returns single)
        search: Optional search term for code or name
        page: Page number (1-based)
        limit: Maximum records per page (default from config, max 200)
        context: Injected tool execution context

    Returns:
        Single organizational unit dict if organizational_unit_id provided, otherwise list result.

    Raises:
        ValueError: If organizational_unit_id is not a valid UUID format
    """
    limit = get_page_limit(limit)
    skip = (page - 1) * limit

    try:
        log_temporal_context("find_organizational_units", context)

        from app.services.organizational_unit_service import OrganizationalUnitService

        service = OrganizationalUnitService(context.session)

        # Single organizational unit lookup
        if organizational_unit_id:
            org_unit = await service.get_as_of(UUID(organizational_unit_id))

            if not org_unit:
                return add_temporal_metadata(
                    {
                        "error": f"Organizational unit {organizational_unit_id} not found"
                    },
                    context,
                )

            return add_temporal_metadata(
                {
                    "id": str(org_unit.organizational_unit_id),
                    "code": org_unit.code,
                    "name": org_unit.name,
                    "description": org_unit.description,
                    "parent_unit_id": str(org_unit.parent_unit_id)
                    if org_unit.parent_unit_id
                    else None,
                    "manager_id": str(org_unit.manager_id)
                    if org_unit.manager_id
                    else None,
                    "is_active": org_unit.is_active,
                },
                context,
            )

        # List organizational units
        org_units, total = await service.get_departments(
            search=search,
            skip=skip,
            limit=limit,
        )

        return add_temporal_metadata(
            {
                "organizational_units": [
                    {
                        "id": str(ou.organizational_unit_id),
                        "code": ou.code,
                        "name": ou.name,
                        "description": ou.description,
                        "parent_unit_id": str(ou.parent_unit_id)
                        if ou.parent_unit_id
                        else None,
                        "manager_id": str(ou.manager_id) if ou.manager_id else None,
                        "is_active": ou.is_active,
                    }
                    for ou in org_units
                ],
                "total": total,
                "page": page,
                "page_count": calc_page_count(total, limit),
                "limit": limit,
                "has_more": page < calc_page_count(total, limit),
            },
            context,
        )
    except ValueError:
        return add_temporal_metadata(
            {"error": f"Invalid organizational unit ID: {organizational_unit_id}"},
            context,
        )
    except Exception as e:
        logger.error(f"Error in find_organizational_units: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="create_organizational_unit",
    description="Create a new organizational unit.",
    permissions=["organizational-unit-create"],
    category="users",
    risk_level=RiskLevel.HIGH,
)
async def create_organizational_unit(
    code: str,
    name: str,
    description: str | None = None,
    parent_unit_id: str | None = None,
    manager_id: str | None = None,
    is_active: bool = True,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new organizational unit.

    Context: Provides database session and organizational unit service for creating.

    Args:
        code: Unique organizational unit code (uppercase alphanumeric)
        name: Organizational unit display name
        description: Optional organizational unit description
        parent_unit_id: Optional UUID of the parent organizational unit for hierarchy
        manager_id: Optional UUID of the organizational unit manager
        is_active: Whether the organizational unit is active (default: True)
        context: Injected tool execution context

    Returns:
        Dictionary with created organizational unit details

    Raises:
        ValueError: If invalid input or duplicate code
        KeyError: If manager user not found

    Example:
        >>> result = await create_organizational_unit(
        ...     code="ENG",
        ...     name="Engineering",
        ...     description="Software and Hardware Engineering",
        ...     manager_id="..."
        ... )
        >>> print(f"Created organizational unit with ID: {result['id']}")
    """
    try:
        from app.services.organizational_unit_service import OrganizationalUnitService

        service = OrganizationalUnitService(context.session)

        # Create Pydantic schema
        unit_data = OrganizationalUnitCreate(
            code=code,
            name=name,
            description=description,
            parent_unit_id=UUID(parent_unit_id) if parent_unit_id else None,
            manager_id=UUID(manager_id) if manager_id else None,
            is_active=is_active,
            branch=context.branch_name or "main",
        )

        # Call service method
        org_unit = await service.create_organizational_unit(
            unit_in=unit_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(org_unit.organizational_unit_id),
            "code": org_unit.code,
            "name": org_unit.name,
            "description": org_unit.description,
            "parent_unit_id": str(org_unit.parent_unit_id)
            if org_unit.parent_unit_id
            else None,
            "manager_id": str(org_unit.manager_id) if org_unit.manager_id else None,
            "is_active": org_unit.is_active,
            "message": "Organizational unit created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError as e:
        return {"error": f"Manager not found: {e}"}
    except Exception as e:
        logger.error(f"Error in create_organizational_unit: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_organizational_unit",
    description="Update organizational unit fields.",
    permissions=["organizational-unit-update"],
    category="users",
    risk_level=RiskLevel.HIGH,
)
async def update_organizational_unit(
    organizational_unit_id: str,
    name: str | None = None,
    description: str | None = None,
    manager_id: str | None = None,
    is_active: bool | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing organizational unit.

    Context: Provides database session and organizational unit service for updating.

    Args:
        organizational_unit_id: UUID of the organizational unit to update
        name: New name (optional)
        description: New description (optional)
        manager_id: New manager UUID (optional)
        is_active: New active status (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated organizational unit details

    Raises:
        ValueError: If organizational_unit_id is invalid or no fields provided
        KeyError: If organizational unit not found

    Example:
        >>> result = await update_organizational_unit(
        ...     organizational_unit_id="...",
        ...     name="Updated Engineering",
        ...     is_active=False
        ... )
        >>> print(f"Updated organizational unit: {result['name']}")
    """
    try:
        from app.services.organizational_unit_service import OrganizationalUnitService

        service = OrganizationalUnitService(context.session)

        # Create update schema with only provided fields
        update_data = OrganizationalUnitUpdate(
            name=name,
            description=description,
            manager_id=UUID(manager_id) if manager_id else None,
            is_active=is_active,
            branch=context.branch_name or "main",
        )

        # Call service method
        org_unit = await service.update_organizational_unit(
            organizational_unit_id=UUID(organizational_unit_id),
            unit_in=update_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(org_unit.organizational_unit_id),
            "code": org_unit.code,
            "name": org_unit.name,
            "description": org_unit.description,
            "manager_id": str(org_unit.manager_id) if org_unit.manager_id else None,
            "is_active": org_unit.is_active,
            "message": "Organizational unit updated successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"Organizational unit {organizational_unit_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_organizational_unit: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_organizational_unit",
    description="Delete an organizational unit.",
    permissions=["organizational-unit-delete"],
    category="users",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_organizational_unit(
    organizational_unit_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete an organizational unit.

    Context: Provides database session and organizational unit service for deletion.

    Args:
        organizational_unit_id: UUID of the organizational unit to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If organizational_unit_id is invalid
        KeyError: If organizational unit not found

    Example:
        >>> result = await delete_organizational_unit("...")
        >>> print(f"Deleted organizational unit: {result['id']}")
    """
    try:
        from app.services.organizational_unit_service import OrganizationalUnitService

        service = OrganizationalUnitService(context.session)

        # Call service method
        await service.delete_organizational_unit(
            organizational_unit_id=UUID(organizational_unit_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": organizational_unit_id,
            "message": "Organizational unit deleted successfully",
        }
    except ValueError:
        return {"error": f"Invalid organizational unit ID: {organizational_unit_id}"}
    except KeyError:
        return {"error": f"Organizational unit {organizational_unit_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_organizational_unit: {e}")
        return {"error": str(e)}


# =============================================================================
# BATCH USER TOOLS
# =============================================================================


@ai_tool(
    name="batch_create_users",
    description="Batch create users. Max 50 items.",
    permissions=["user-create"],
    category="users",
    risk_level=RiskLevel.HIGH,
)
async def batch_create_users(
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create users.

    Args:
        items: List of dicts, each with {email, full_name, password, department?, role?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    try:
        from app.services.user import UserService

        if len(items) > BATCH_SIZE_LIMIT:
            return {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"}

        if not items:
            return {"error": "No items provided"}

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("email"):
                return {"error": f"Item at index {i} is missing required field 'email'"}
            if not item.get("full_name"):
                return {
                    "error": f"Item at index {i} is missing required field 'full_name'"
                }
            if not item.get("password"):
                return {
                    "error": f"Item at index {i} is missing required field 'password'"
                }

        service = UserService(context.session)
        actor_id = UUID(context.user_id)
        results: list[dict[str, Any]] = []

        for item in items:
            user_data = UserRegister(
                email=item["email"],
                full_name=item["full_name"],
                password=item["password"],
                department=item.get("department"),
                role=item.get("role", "viewer"),
            )

            user = await service.create_user(
                user_in=user_data,
                actor_id=actor_id,
            )

            role = await _resolve_user_role(context.session, user.user_id)
            results.append(
                {
                    "id": str(user.user_id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": role,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} users",
        }
        return result
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in batch_create_users: {e}")
        return {"error": str(e)}


# =============================================================================
# BATCH ORGANIZATIONAL UNIT TOOLS
# =============================================================================


@ai_tool(
    name="batch_create_organizational_units",
    description="Batch create organizational units. Max 50 items.",
    permissions=["organizational-unit-create"],
    category="users",
    risk_level=RiskLevel.HIGH,
)
async def batch_create_organizational_units(
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create organizational units.

    Args:
        items: List of dicts, each with {code, name, description?, manager_id?, is_active?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    try:
        from app.services.organizational_unit_service import OrganizationalUnitService

        if len(items) > BATCH_SIZE_LIMIT:
            return {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"}

        if not items:
            return {"error": "No items provided"}

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("code"):
                return {"error": f"Item at index {i} is missing required field 'code'"}
            if not item.get("name"):
                return {"error": f"Item at index {i} is missing required field 'name'"}

        service = OrganizationalUnitService(context.session)
        actor_id = UUID(context.user_id)
        branch = context.branch_name or "main"
        results: list[dict[str, Any]] = []

        for item in items:
            unit_data = OrganizationalUnitCreate(
                code=item["code"],
                name=item["name"],
                description=item.get("description"),
                manager_id=UUID(item["manager_id"]) if item.get("manager_id") else None,
                is_active=item.get("is_active", True),
                branch=branch,
            )

            org_unit = await service.create_organizational_unit(
                unit_in=unit_data,
                actor_id=actor_id,
            )
            results.append(
                {
                    "id": str(org_unit.organizational_unit_id),
                    "code": org_unit.code,
                    "name": org_unit.name,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} organizational units",
        }
        return result
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in batch_create_organizational_units: {e}")
        return {"error": str(e)}


# =============================================================================
# TEMPLATE USAGE NOTES
# =============================================================================

"""
USER AND ORGANIZATIONAL UNIT TOOL PATTERNS:

1. USER MANAGEMENT:
   - Users are temporal entities with full versioning
   - Password hashing is handled by the service
   - Users have roles (viewer, engineer, manager, admin)
   - User preferences are stored as JSON

2. ORGANIZATIONAL UNIT MANAGEMENT:
   - Organizational Units are temporal entities with full versioning
   - Organizational Units can have optional managers (users)
   - Used for organizing users and cost element types
   - Organizational Unit codes must be unique

3. RELATIONSHIP BETWEEN USERS AND ORGANIZATIONAL UNITS:
   - Users have a department field (string)
   - Organizational Units have a manager_id (UUID referencing a user)
   - This is a loose relationship for flexibility

4. PERMISSIONS MODEL:
   USERS:
   - user-read: View users
   - user-create: Create users
   - user-update: Update users
   - user-delete: Delete users

   ORGANIZATIONAL UNITS:
   - organizational-unit-read: View organizational units
   - organizational-unit-create: Create organizational units
   - organizational-unit-update: Update organizational units
   - organizational-unit-delete: Delete organizational units

5. RBAC INTEGRATION:
   - User roles determine permissions
   - Permissions are checked via @ai_tool decorator
   - Roles: viewer, engineer, manager, admin

BEST PRACTICES:
   - Always hash passwords before storing (handled by service)
   - Validate email uniqueness in service layer
   - Use soft delete to maintain audit trail
   - Validate manager exists when assigning to organizational unit
   - Keep organizational unit codes uppercase and alphanumeric
"""

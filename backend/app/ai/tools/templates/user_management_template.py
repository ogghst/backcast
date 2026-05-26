"""User and Department management tool template for wrapping service methods.

This template shows how to create AI tools for user and department management.
The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Users in Backcast:
- Users are temporal entities with full versioning support
- Password hashing is handled by the service
- Users have roles and permissions managed by RBAC
- User preferences are stored as JSON

Departments in Backcast:
- Departments are temporal entities with full versioning support
- Departments can have optional managers (users)
- Used for organizing users and cost element types

Usage:
    1. Import UserService and DepartmentService methods
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
from app.models.schemas.department import DepartmentCreate, DepartmentUpdate
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
    description="Find users by ID or search.",
    permissions=["user-read"],
    category="users",
    risk_level=RiskLevel.LOW,
)
async def find_users(
    user_id: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find users by ID or search.

    Context: Provides database session and user service for querying users.

    Args:
        user_id: UUID of a specific user to retrieve (returns single)
        search: Optional search term
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        context: Injected tool execution context

    Returns:
        Single user dict if user_id provided, otherwise list result.

    Raises:
        ValueError: If user_id is not a valid UUID format
    """
    try:
        from app.services.user import UserService

        service = UserService(context.session)

        # Single user lookup
        if user_id:
            user = await service.get_user(UUID(user_id))

            if not user:
                return {"error": f"User {user_id} not found"}

            role = await _resolve_user_role(context.session, user.user_id)
            return {
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
            }

        # List users
        users = await service.get_users(skip=skip, limit=limit)
        total = len(users)

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

        return {
            "users": user_list,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except ValueError:
        return {"error": f"Invalid user ID: {user_id}"}
    except Exception as e:
        logger.error(f"Error in find_users: {e}")
        return {"error": str(e)}


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
# DEPARTMENT CRUD TOOLS
# =============================================================================


@ai_tool(
    name="find_departments",
    description="Find departments by ID or search.",
    permissions=["department-read"],
    category="departments",
    risk_level=RiskLevel.LOW,
)
async def find_departments(
    department_id: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find departments by ID or search.

    Context: Provides database session and department service for querying departments.

    Args:
        department_id: UUID of a specific department to retrieve (returns single)
        search: Optional search term for code or name
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        context: Injected tool execution context

    Returns:
        Single department dict if department_id provided, otherwise list result.

    Raises:
        ValueError: If department_id is not a valid UUID format
    """
    try:
        from app.services.department import DepartmentService

        service = DepartmentService(context.session)

        # Single department lookup
        if department_id:
            department = await service.get_as_of(UUID(department_id))

            if not department:
                return {"error": f"Department {department_id} not found"}

            return {
                "id": str(department.department_id),
                "code": department.code,
                "name": department.name,
                "description": department.description,
                "manager_id": str(department.manager_id)
                if department.manager_id
                else None,
                "is_active": department.is_active,
            }

        # List departments
        departments, total = await service.get_departments(
            search=search,
            skip=skip,
            limit=limit,
        )

        return {
            "departments": [
                {
                    "id": str(dept.department_id),
                    "code": dept.code,
                    "name": dept.name,
                    "description": dept.description,
                    "manager_id": str(dept.manager_id) if dept.manager_id else None,
                    "is_active": dept.is_active,
                }
                for dept in departments
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except ValueError:
        return {"error": f"Invalid department ID: {department_id}"}
    except Exception as e:
        logger.error(f"Error in find_departments: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_department",
    description="Create a new department.",
    permissions=["department-create"],
    category="departments",
    risk_level=RiskLevel.HIGH,
)
async def create_department(
    code: str,
    name: str,
    description: str | None = None,
    manager_id: str | None = None,
    is_active: bool = True,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new department.

    Context: Provides database session and department service for creating departments.

    Args:
        code: Unique department code (uppercase alphanumeric)
        name: Department display name
        description: Optional department description
        manager_id: Optional UUID of the department manager
        is_active: Whether the department is active (default: True)
        context: Injected tool execution context

    Returns:
        Dictionary with created department details

    Raises:
        ValueError: If invalid input or duplicate code
        KeyError: If manager user not found

    Example:
        >>> result = await create_department(
        ...     code="ENG",
        ...     name="Engineering",
        ...     description="Software and Hardware Engineering",
        ...     manager_id="..."
        ... )
        >>> print(f"Created department with ID: {result['id']}")
    """
    try:
        from app.services.department import DepartmentService

        service = DepartmentService(context.session)

        # Create Pydantic schema
        dept_data = DepartmentCreate(
            code=code,
            name=name,
            description=description,
            manager_id=UUID(manager_id) if manager_id else None,
            is_active=is_active,
        )

        # Call service method
        department = await service.create_department(
            dept_in=dept_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(department.department_id),
            "code": department.code,
            "name": department.name,
            "description": department.description,
            "manager_id": str(department.manager_id) if department.manager_id else None,
            "is_active": department.is_active,
            "message": "Department created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError as e:
        return {"error": f"Manager not found: {e}"}
    except Exception as e:
        logger.error(f"Error in create_department: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_department",
    description="Update department fields.",
    permissions=["department-update"],
    category="departments",
    risk_level=RiskLevel.HIGH,
)
async def update_department(
    department_id: str,
    name: str | None = None,
    description: str | None = None,
    manager_id: str | None = None,
    is_active: bool | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing department.

    Context: Provides database session and department service for updating departments.

    Args:
        department_id: UUID of the department to update
        name: New name (optional)
        description: New description (optional)
        manager_id: New manager UUID (optional)
        is_active: New active status (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated department details

    Raises:
        ValueError: If department_id is invalid or no fields provided
        KeyError: If department not found

    Example:
        >>> result = await update_department(
        ...     department_id="...",
        ...     name="Updated Engineering",
        ...     is_active=False
        ... )
        >>> print(f"Updated department: {result['name']}")
    """
    try:
        from app.services.department import DepartmentService

        service = DepartmentService(context.session)

        # Create update schema with only provided fields
        update_data = DepartmentUpdate(
            name=name,
            description=description,
            manager_id=UUID(manager_id) if manager_id else None,
            is_active=is_active,
        )

        # Call service method
        department = await service.update_department(
            department_id=UUID(department_id),
            dept_in=update_data,
            actor_id=UUID(context.user_id),
        )

        # Convert to AI-friendly format
        return {
            "id": str(department.department_id),
            "code": department.code,
            "name": department.name,
            "description": department.description,
            "manager_id": str(department.manager_id) if department.manager_id else None,
            "is_active": department.is_active,
            "message": "Department updated successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"Department {department_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_department: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_department",
    description="Delete a department.",
    permissions=["department-delete"],
    category="departments",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_department(
    department_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a department.

    Context: Provides database session and department service for deletion.

    Args:
        department_id: UUID of the department to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If department_id is invalid
        KeyError: If department not found

    Example:
        >>> result = await delete_department("...")
        >>> print(f"Deleted department: {result['id']}")
    """
    try:
        from app.services.department import DepartmentService

        service = DepartmentService(context.session)

        # Call service method
        await service.delete_department(
            department_id=UUID(department_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": department_id,
            "message": "Department deleted successfully",
        }
    except ValueError:
        return {"error": f"Invalid department ID: {department_id}"}
    except KeyError:
        return {"error": f"Department {department_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_department: {e}")
        return {"error": str(e)}


# =============================================================================
# TEMPLATE USAGE NOTES
# =============================================================================

"""
USER AND DEPARTMENT TOOL PATTERNS:

1. USER MANAGEMENT:
   - Users are temporal entities with full versioning
   - Password hashing is handled by the service
   - Users have roles (viewer, engineer, manager, admin)
   - User preferences are stored as JSON

2. DEPARTMENT MANAGEMENT:
   - Departments are temporal entities with full versioning
   - Departments can have optional managers (users)
   - Used for organizing users and cost element types
   - Department codes must be unique

3. RELATIONSHIP BETWEEN USERS AND DEPARTMENTS:
   - Users have a department field (string)
   - Departments have a manager_id (UUID referencing a user)
   - This is a loose relationship for flexibility

4. PERMISSIONS MODEL:
   USERS:
   - user-read: View users
   - user-create: Create users
   - user-update: Update users
   - user-delete: Delete users

   DEPARTMENTS:
   - department-read: View departments
   - department-create: Create departments
   - department-update: Update departments
   - department-delete: Delete departments

5. RBAC INTEGRATION:
   - User roles determine permissions
   - Permissions are checked via @ai_tool decorator
   - Roles: viewer, engineer, manager, admin

BEST PRACTICES:
   - Always hash passwords before storing (handled by service)
   - Validate email uniqueness in service layer
   - Use soft delete to maintain audit trail
   - Validate manager exists when assigning to department
   - Keep department codes uppercase and alphanumeric
"""

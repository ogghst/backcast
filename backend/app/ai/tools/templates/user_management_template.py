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

# =============================================================================
# USER CRUD TOOLS
# =============================================================================

@ai_tool(
    name="list_users",
    description="List all users with pagination. "
    "Returns users with their roles, departments, and activity status.",
    permissions=["user-read"],
    category="users",
    risk_level=RiskLevel.LOW,
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List users with pagination.

    Context: Provides database session and user service for querying users.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        context: Injected tool execution context

    Returns:
        Dictionary with:
        - users: List of user objects
        - total: Total number of users
        - skip: Number of records skipped
        - limit: Maximum records returned

    Raises:
        ValueError: If invalid pagination parameters

    Example:
        >>> result = await list_users(skip=0, limit=10)
        >>> print(f"Found {result['total']} users")
        >>> for user in result['users']:
        ...     print(f"- {user['full_name']} ({user['email']})")
    """
    try:
        from app.services.user import UserService

        service = UserService(context.session)

        # Call service method
        users = await service.get_users(skip=skip, limit=limit)

        # Get total count (service returns list, so we need to count)
        total = len(users)

        # Convert to AI-friendly format
        return {
            "users": [
                {
                    "id": str(user.user_id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "department": user.department,
                    "role": user.role,
                    "is_active": user.is_active,
                    "preferences": user.preferences if user.preferences else None,
                }
                for user in users
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Error in list_users: {e}")
        return {"error": str(e)}


@ai_tool(
    name="get_user",
    description="Get detailed information about a specific user by ID. "
    "Returns full user details including role and preferences.",
    permissions=["user-read"],
    category="users",
    risk_level=RiskLevel.LOW,
)
async def get_user(
    user_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get a single user by ID.

    Context: Provides database session and user service for retrieving user data.

    Args:
        user_id: UUID of the user to retrieve
        context: Injected tool execution context

    Returns:
        Dictionary with user details or error if not found

    Raises:
        ValueError: If user_id is not a valid UUID format
        KeyError: If user is not found

    Example:
        >>> result = await get_user("123e4567-e89b-12d3-a456-426614174000")
        >>> if "error" not in result:
        ...     print(f"User: {result['full_name']}")
        ...     print(f"Role: {result['role']}")
    """
    try:
        from app.services.user import UserService

        service = UserService(context.session)

        # Call service method
        user = await service.get_user(UUID(user_id))

        if not user:
            return {"error": f"User {user_id} not found"}

        # Convert to AI-friendly format
        return {
            "id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
            "role": user.role,
            "is_active": user.is_active,
            "preferences": user.preferences if user.preferences else None,
            "password_changed_at": user.password_changed_at.isoformat() if user.password_changed_at else None,
        }
    except ValueError:
        return {"error": f"Invalid user ID: {user_id}"}
    except Exception as e:
        logger.error(f"Error in get_user: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_user",
    description="Create a new user with email, password, and role. "
    "Password is automatically hashed. Returns the created user without password.",
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
        return {
            "id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
            "role": user.role,
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
    description="Update an existing user with new information. "
    "Password can be updated and will be automatically hashed. "
    "Note: User preferences cannot be updated via this tool - use the user preferences endpoint instead.",
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
        return {
            "id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
            "role": user.role,
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
    description="Soft delete a user. "
    "The user is marked as deleted but remains in the system for audit purposes.",
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
    name="list_departments",
    description="List all departments with optional search and pagination. "
    "Returns departments with their codes and manager information.",
    permissions=["department-read"],
    category="departments",
    risk_level=RiskLevel.LOW,
)
async def list_departments(
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    sort_field: str | None = None,
    sort_order: str = "asc",
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List departments with optional filtering.

    Context: Provides database session and department service for querying departments.

    Args:
        search: Optional search term for code or name
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        sort_field: Field to sort by (e.g., "name", "code")
        sort_order: Sort order ("asc" or "desc")
        context: Injected tool execution context

    Returns:
        Dictionary with:
        - departments: List of department objects
        - total: Total number of departments matching filters
        - skip: Number of records skipped
        - limit: Maximum records returned

    Raises:
        ValueError: If invalid filter parameters

    Example:
        >>> result = await list_departments(search="Engineering", limit=10)
        >>> print(f"Found {result['total']} departments")
        >>> for dept in result['departments']:
        ...     print(f"- {dept['name']} ({dept['code']})")
    """
    try:
        from app.services.department import DepartmentService

        service = DepartmentService(context.session)

        # Call service method
        departments, total = await service.get_departments(
            search=search,
            skip=skip,
            limit=limit,
            sort_field=sort_field,
            sort_order=sort_order,
        )

        # Convert to AI-friendly format
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
    except Exception as e:
        logger.error(f"Error in list_departments: {e}")
        return {"error": str(e)}


@ai_tool(
    name="get_department",
    description="Get detailed information about a specific department by ID. "
    "Returns full department details including manager and status.",
    permissions=["department-read"],
    category="departments",
    risk_level=RiskLevel.LOW,
)
async def get_department(
    department_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get a single department by ID.

    Context: Provides database session and department service for retrieving department data.

    Args:
        department_id: UUID of the department to retrieve
        context: Injected tool execution context

    Returns:
        Dictionary with department details or error if not found

    Raises:
        ValueError: If department_id is not a valid UUID format
        KeyError: If department is not found

    Example:
        >>> result = await get_department("123e4567-e89b-12d3-a456-426614174000")
        >>> if "error" not in result:
        ...     print(f"Department: {result['name']}")
        ...     print(f"Code: {result['code']}")
    """
    try:
        from app.services.department import DepartmentService

        service = DepartmentService(context.session)

        # Call service method
        department = await service.get_as_of(UUID(department_id))

        if not department:
            return {"error": f"Department {department_id} not found"}

        # Convert to AI-friendly format
        return {
            "id": str(department.department_id),
            "code": department.code,
            "name": department.name,
            "description": department.description,
            "manager_id": str(department.manager_id) if department.manager_id else None,
            "is_active": department.is_active,
        }
    except ValueError:
        return {"error": f"Invalid department ID: {department_id}"}
    except Exception as e:
        logger.error(f"Error in get_department: {e}")
        return {"error": str(e)}


@ai_tool(
    name="create_department",
    description="Create a new department with code, name, and optional manager. "
    "Returns the created department with all details.",
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
    description="Update an existing department with new information. "
    "Only updates fields that are provided.",
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
    description="Soft delete a department. "
    "The department is marked as deleted but remains in the system for audit purposes.",
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

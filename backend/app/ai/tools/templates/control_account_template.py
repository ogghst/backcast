"""Control Account tool template for wrapping ControlAccountService methods.

This template provides AI tools for ANSI-748 Control Account management.
The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Control Accounts in Backcast (ANSI-748):
- Control Accounts are management control points at the intersection of WBS Elements
  and Organizational Units
- They aggregate Work Packages for budget authority delegation
- They are BRANCHABLE (supports change orders) and VERSIONABLE (tracks changes)

Usage:
    1. Import ControlAccountService methods
    2. Use @ai_tool decorator with proper permissions
    3. Use ToolContext for dependency injection
    4. Call service methods with context.session
    5. Return results in AI-friendly format

TEMPORAL CONTEXT PATTERN:
For read tools (those that query versioned entities):
- Import temporal logging helpers: log_temporal_context, add_temporal_metadata
- Call log_temporal_context() at tool start for observability
- Call add_temporal_metadata() on return to include temporal context in results
"""

import logging
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import RiskLevel, ToolContext
from app.models.schemas.control_account import ControlAccountCreate

logger = logging.getLogger(__name__)

BATCH_SIZE_LIMIT = 50

# =============================================================================
# CONTROL ACCOUNT CRUD TOOLS
# =============================================================================


@ai_tool(
    name="find_control_accounts",
    description="Find control accounts by ID or search/filter.",
    permissions=["control-account-read"],
    category="control-accounts",
    risk_level=RiskLevel.LOW,
)
async def find_control_accounts(
    control_account_id: str | None = None,
    wbs_element_id: str | None = None,
    organizational_unit_id: str | None = None,
    skip: int = 0,
    limit: int = 50,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find control accounts by ID or search/filter.

    Context: Provides database session and control account service for querying
    control accounts.

    Args:
        control_account_id: UUID of a specific control account to retrieve
            (returns single)
        wbs_element_id: UUID of the WBS element to filter control accounts for
        organizational_unit_id: UUID of the organizational unit to filter by
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        context: Injected tool execution context

    Returns:
        Single control account dict if control_account_id provided, otherwise
        list result.

    Raises:
        ValueError: If IDs are not valid UUID format
    """
    log_temporal_context("find_control_accounts", context)

    try:
        from app.core.versioning.enums import BranchMode
        from app.services.control_account_service import ControlAccountService

        service = ControlAccountService(context.session)
        branch = context.branch_name or "main"
        branch_mode = (
            BranchMode.MERGED
            if context.branch_mode == "merged"
            else BranchMode.ISOLATED
        )

        # Single control account lookup
        if control_account_id:
            ca = await service.get_as_of(
                entity_id=UUID(control_account_id),
                as_of=context.as_of,
                branch=branch,
                branch_mode=branch_mode,
            )

            if not ca:
                return add_temporal_metadata(
                    {"error": f"Control account {control_account_id} not found"},
                    context,
                )

            ca_result: dict[str, Any] = {
                "control_account_id": str(ca.control_account_id),
                "name": ca.name,
                "code": ca.code,
                "description": ca.description,
                "wbs_element_id": str(ca.wbs_element_id),
                "organizational_unit_id": str(ca.organizational_unit_id),
                "branch": ca.branch,
            }
            return add_temporal_metadata(ca_result, context)

        # List control accounts
        wbs_filter = UUID(wbs_element_id) if wbs_element_id else None
        org_filter = UUID(organizational_unit_id) if organizational_unit_id else None

        control_accounts, total = await service.get_control_accounts(
            wbs_element_id=wbs_filter,
            organizational_unit_id=org_filter,
            skip=skip,
            limit=limit,
            branch=branch,
            branch_mode=branch_mode,
            as_of=context.as_of,
        )

        result: dict[str, Any] = {
            "control_accounts": [
                {
                    "control_account_id": str(ca.control_account_id),
                    "name": ca.name,
                    "code": ca.code,
                    "description": ca.description,
                    "wbs_element_id": str(ca.wbs_element_id),
                    "organizational_unit_id": str(ca.organizational_unit_id),
                    "branch": ca.branch,
                }
                for ca in control_accounts
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in find_control_accounts: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="create_control_account",
    description="Create ANSI-748 control account at a WBS Element x "
    "Organizational Unit intersection.",
    permissions=["control-account-create"],
    category="control-accounts",
    risk_level=RiskLevel.HIGH,
)
async def create_control_account(
    wbs_element_id: str,
    organizational_unit_id: str,
    name: str,
    code: str | None = None,
    description: str | None = None,
    control_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new Control Account at a WBS Element x Organizational Unit
    intersection.

    Context: Provides database session and control account service for creating
    control accounts.

    Args:
        wbs_element_id: UUID of the WBS Element
        organizational_unit_id: UUID of the Organizational Unit
        name: Control account name
        code: Optional control account code (e.g., "CA-001")
        description: Optional description
        control_date: Optional control date for valid_time start (ISO format)
        context: Injected tool execution context

    Returns:
        Dictionary with created control account details

    Raises:
        ValueError: If invalid input or WBS element/org unit not found

    Example:
        >>> result = await create_control_account(
        ...     wbs_element_id="...",
        ...     organizational_unit_id="...",
        ...     name="Mechanical Assembly CA",
        ...     code="CA-001",
        ... )
        >>> print(f"Created control account: {result['control_account_id']}")
    """
    try:
        from app.services.control_account_service import ControlAccountService

        service = ControlAccountService(context.session)

        parsed_control_date = (
            datetime.fromisoformat(control_date) if control_date else None
        )
        branch = context.branch_name or "main"

        ca_data = ControlAccountCreate(
            wbs_element_id=UUID(wbs_element_id),
            organizational_unit_id=UUID(organizational_unit_id),
            name=name,
            code=code,
            description=description,
            branch=branch,
            control_date=parsed_control_date,
        )

        ca = await service.create_root(
            root_id=uuid4(),
            actor_id=UUID(context.user_id),
            control_date=parsed_control_date,
            branch=branch,
            wbs_element_id=ca_data.wbs_element_id,
            organizational_unit_id=ca_data.organizational_unit_id,
            name=ca_data.name,
            code=ca_data.code,
            description=ca_data.description,
        )

        return {
            "control_account_id": str(ca.control_account_id),
            "name": ca.name,
            "code": ca.code,
            "description": ca.description,
            "wbs_element_id": str(ca.wbs_element_id),
            "organizational_unit_id": str(ca.organizational_unit_id),
            "branch": ca.branch,
            "message": "Control account created successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_control_account: {e}")
        return {"error": str(e)}


@ai_tool(
    name="update_control_account",
    description="Update control account fields.",
    permissions=["control-account-update"],
    category="control-accounts",
    risk_level=RiskLevel.HIGH,
)
async def update_control_account(
    control_account_id: str,
    name: str | None = None,
    code: str | None = None,
    description: str | None = None,
    wbs_element_id: str | None = None,
    organizational_unit_id: str | None = None,
    control_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing control account.

    Context: Provides database session and control account service for updating
    control accounts.

    Args:
        control_account_id: UUID of the control account to update
        name: New name (optional)
        code: New code (optional)
        description: New description (optional)
        wbs_element_id: New WBS Element UUID (optional)
        organizational_unit_id: New Organizational Unit UUID (optional)
        control_date: Control date for valid_time start in ISO format (optional)
        context: Injected tool execution context

    Returns:
        Dictionary with updated control account details

    Raises:
        ValueError: If control_account_id is invalid
        KeyError: If control account not found

    Example:
        >>> result = await update_control_account(
        ...     control_account_id="...",
        ...     name="Updated CA Name",
        ...     code="CA-002",
        ... )
        >>> print(f"Updated control account: {result['name']}")
    """
    try:
        from app.services.control_account_service import ControlAccountService

        service = ControlAccountService(context.session)
        branch = context.branch_name or "main"

        parsed_control_date = (
            datetime.fromisoformat(control_date) if control_date else None
        )

        update_kwargs: dict[str, Any] = {}
        if name is not None:
            update_kwargs["name"] = name
        if code is not None:
            update_kwargs["code"] = code
        if description is not None:
            update_kwargs["description"] = description
        if wbs_element_id is not None:
            update_kwargs["wbs_element_id"] = UUID(wbs_element_id)
        if organizational_unit_id is not None:
            update_kwargs["organizational_unit_id"] = UUID(organizational_unit_id)

        ca = await service.update(
            root_id=UUID(control_account_id),
            actor_id=UUID(context.user_id),
            branch=branch,
            control_date=parsed_control_date,
            **update_kwargs,
        )

        return {
            "control_account_id": str(ca.control_account_id),
            "name": ca.name,
            "code": ca.code,
            "description": ca.description,
            "wbs_element_id": str(ca.wbs_element_id),
            "organizational_unit_id": str(ca.organizational_unit_id),
            "branch": ca.branch,
            "message": "Control account updated successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except KeyError:
        return {"error": f"Control account {control_account_id} not found"}
    except Exception as e:
        logger.error(f"Error in update_control_account: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_control_account",
    description="Delete control account.",
    permissions=["control-account-delete"],
    category="control-accounts",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_control_account(
    control_account_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a control account.

    Context: Provides database session and control account service for deletion.

    Args:
        control_account_id: UUID of the control account to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If control_account_id is invalid
        KeyError: If control account not found

    Example:
        >>> result = await delete_control_account("...")
        >>> print(f"Deleted control account: {result['id']}")
    """
    try:
        from app.services.control_account_service import ControlAccountService

        service = ControlAccountService(context.session)

        await service.soft_delete(
            root_id=UUID(control_account_id),
            actor_id=UUID(context.user_id),
            branch=context.branch_name or "main",
        )

        return {
            "id": control_account_id,
            "message": "Control account deleted",
        }
    except ValueError:
        return {"error": f"Invalid control account ID: {control_account_id}"}
    except KeyError:
        return {"error": f"Control account {control_account_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_control_account: {e}")
        return {"error": str(e)}


@ai_tool(
    name="get_control_account_budget",
    description="Get computed budget for a control account.",
    permissions=["control-account-read"],
    category="control-accounts",
    risk_level=RiskLevel.LOW,
)
async def get_control_account_budget(
    control_account_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get computed budget for a Control Account.

    Budget is the sum of all child Work Package budget amounts.

    Args:
        control_account_id: UUID of the control account
        context: Injected tool execution context

    Returns:
        Dictionary with control account budget amount.

    Raises:
        ValueError: If control_account_id is not a valid UUID format
    """
    log_temporal_context("get_control_account_budget", context)

    try:
        from app.services.control_account_service import ControlAccountService

        service = ControlAccountService(context.session)
        branch = context.branch_name or "main"

        budget = await service.compute_budget(
            control_account_id=UUID(control_account_id),
            branch=branch,
        )

        result: dict[str, Any] = {
            "control_account_id": control_account_id,
            "budget": float(budget),
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in get_control_account_budget: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


# =============================================================================
# BATCH CONTROL ACCOUNT TOOLS
# =============================================================================


@ai_tool(
    name="batch_create_control_accounts",
    description="Batch create multiple control accounts under a WBS element. "
    "Each control account represents the intersection of a WBS element and an organizational unit. "
    "Maximum 50 items per batch.",
    permissions=["control-account-create"],
    category="control-accounts",
    risk_level=RiskLevel.HIGH,
)
async def batch_create_control_accounts(
    wbs_element_id: str,
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create control accounts under the same WBS element.

    Each control account represents the intersection of a WBS element and an
    organizational unit. Duplicate organizational_unit_id entries within the
    same batch are rejected because each (wbs_element_id, organizational_unit_id)
    pair must be unique.

    Args:
        wbs_element_id: UUID of the parent WBS Element
        items: List of dicts, each with {organizational_unit_id, name, code?, description?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    log_temporal_context("batch_create_control_accounts", context)

    try:
        from app.services.control_account_service import ControlAccountService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("organizational_unit_id"):
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'organizational_unit_id'"
                    },
                    context,
                )
            if not item.get("name"):
                return add_temporal_metadata(
                    {"error": f"Item at index {i} is missing required field 'name'"},
                    context,
                )

        # Check for duplicate organizational_unit_id within the batch
        seen_org_units: set[str] = set()
        for i, item in enumerate(items):
            org_id = item["organizational_unit_id"]
            if org_id in seen_org_units:
                return add_temporal_metadata(
                    {
                        "error": f"Duplicate organizational_unit_id '{org_id}' found at "
                        f"index {i}. Each control account must have a unique "
                        f"organizational unit within the same WBS element."
                    },
                    context,
                )
            seen_org_units.add(org_id)

        service = ControlAccountService(context.session)
        actor_id = UUID(context.user_id)
        branch = context.branch_name or "main"
        results: list[dict[str, Any]] = []

        for item in items:
            ca_data = ControlAccountCreate(
                wbs_element_id=UUID(wbs_element_id),
                organizational_unit_id=UUID(item["organizational_unit_id"]),
                name=item["name"],
                code=item.get("code"),
                description=item.get("description"),
            )

            ca = await service.create_root(
                root_id=uuid4(),
                actor_id=actor_id,
                control_date=None,
                branch=branch,
                wbs_element_id=ca_data.wbs_element_id,
                organizational_unit_id=ca_data.organizational_unit_id,
                name=ca_data.name,
                code=ca_data.code,
                description=ca_data.description,
            )
            results.append(
                {
                    "id": str(ca.control_account_id),
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} control accounts under WBS Element {wbs_element_id}",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata(
            {"error": f"Parent entity not found: {e}"}, context
        )
    except Exception as e:
        logger.error(f"Error in batch_create_control_accounts: {e}")
        return add_temporal_metadata({"error": str(e)}, context)

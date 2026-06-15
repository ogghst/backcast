"""Change Order tool template for wrapping ChangeOrderService methods.

This template shows how to create AI tools for change order management.
The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Change Orders in Backcast:
- Change Orders document scope changes on projects
- They require approval workflow and impact analysis
- They support branching for isolation during negotiations
- Full audit trail with versioning

Usage:
    1. Import ChangeOrderService methods
    2. Use @ai_tool decorator with proper permissions
    3. Use ToolContext for dependency injection
    4. Call service methods with context.session
    5. Return results in AI-friendly format

TEMPORAL CONTEXT PATTERN:
For temporal tools (those that work with versioned entities):
- Import temporal logging helpers: log_temporal_context, add_temporal_metadata
- Call log_temporal_context() at tool start for observability
- Call add_temporal_metadata() on return to include temporal context in results
- Update tool descriptions to mention temporal context enforcement
"""

import logging
from datetime import UTC, datetime
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
from app.models.schemas.change_order import (
    ChangeOrderCreate,
    ChangeOrderUpdate,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CHANGE ORDER CRUD TOOLS
# =============================================================================


@ai_tool(
    name="find_change_orders",
    description=(
        "Find change orders by ID or search/filter. "
        "IMPORTANT: results are paginated — the returned list may be a SUBSET of all matching results. "
        "Always check 'total' and 'has_more' in the response: if has_more=true or total exceeds the returned count, "
        "more pages exist. Use the 'page' and 'limit' parameters to retrieve additional pages. "
        "Do NOT assume the first page contains all results — if you don't find what you need, page forward. "
        "Use 'search' to narrow results before paging."
    ),
    permissions=["change-order-read"],
    category="change-orders",
    risk_level=RiskLevel.LOW,
)
async def find_change_orders(
    change_order_id: str | None = None,
    project_id: str | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find change orders by ID or search/filter.

    Context: Provides database session and change order service for querying change orders.

    Args:
        change_order_id: UUID of a specific change order to retrieve (returns single)
        project_id: Optional project ID to filter change orders
        status: Optional status filter (e.g., "Draft", "Pending", "Approved", "Rejected")
        page: Page number (1-based)
        limit: Maximum records per page (default from config, max 200)
        context: Injected tool execution context

    Returns:
        Single change order dict if change_order_id provided, otherwise list result.

    Raises:
        ValueError: If IDs are not valid UUID format
    """
    # Log temporal context for observability
    log_temporal_context("find_change_orders", context)
    limit = get_page_limit(limit)
    skip = (page - 1) * limit

    try:
        from app.services.change_order_service import ChangeOrderService

        service = ChangeOrderService(context.session)

        # Single change order lookup
        if change_order_id:
            change_order = await service.get_as_of(
                UUID(change_order_id),
                branch=context.branch_name or "main",
                as_of=context.as_of,
            )

            if not change_order:
                return add_temporal_metadata(
                    {"error": f"Change order {change_order_id} not found"}, context
                )

            result = {
                "id": str(change_order.change_order_id),
                "project_id": str(change_order.project_id),
                "title": change_order.title,
                "description": change_order.description,
                "status": change_order.status,
                "approval_status": change_order.approval_status
                if hasattr(change_order, "approval_status")
                else None,
                "budget_impact": float(change_order.budget_impact)
                if hasattr(change_order, "budget_impact") and change_order.budget_impact
                else 0.0,
                "schedule_impact_days": change_order.schedule_impact_days
                if hasattr(change_order, "schedule_impact_days")
                else None,
                "reason": change_order.reason
                if hasattr(change_order, "reason")
                else None,
                "created_at": change_order.created_at.isoformat()
                if hasattr(change_order, "created_at") and change_order.created_at
                else None,
                "updated_at": change_order.updated_at.isoformat()
                if hasattr(change_order, "updated_at") and change_order.updated_at
                else None,
            }
            return add_temporal_metadata(result, context)

        # List change orders
        project_uuid = UUID(project_id) if project_id else None
        filters = f"status:{status}" if status else None

        change_orders, total = await service.get_change_orders(
            project_id=project_uuid,  # type: ignore[arg-type]
            skip=skip,
            limit=limit,
            branch=context.branch_name or "main",
            filters=filters,
            as_of=context.as_of,
        )

        result = {
            "change_orders": [
                {
                    "id": str(co.change_order_id),
                    "project_id": str(co.project_id),
                    "title": co.title,
                    "description": co.description,
                    "status": co.status,
                    "approval_status": co.approval_status
                    if hasattr(co, "approval_status")
                    else None,
                    "budget_impact": float(co.budget_impact)
                    if hasattr(co, "budget_impact") and co.budget_impact
                    else 0.0,
                    "schedule_impact_days": co.schedule_impact_days
                    if hasattr(co, "schedule_impact_days")
                    else None,
                    "created_at": co.created_at.isoformat()
                    if hasattr(co, "created_at") and co.created_at
                    else None,
                }
                for co in change_orders
            ],
            "total": total,
            "page": page,
            "page_count": calc_page_count(total, limit),
            "limit": limit,
            "has_more": page < calc_page_count(total, limit),
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        error_result = {"error": f"Invalid input: {e}"}
        return add_temporal_metadata(error_result, context)
    except Exception as e:
        logger.error(f"Error in find_change_orders: {e}")
        error_result = {"error": str(e)}
        return add_temporal_metadata(error_result, context)


@ai_tool(
    name="create_change_order",
    description="Create a new change order.",
    permissions=["change-order-create"],
    category="change-orders",
    risk_level=RiskLevel.HIGH,
)
async def create_change_order(
    project_id: str,
    title: str,
    description: str,
    reason: str,
    impact_level: str | None = None,
    effective_date: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new change order.

    Context: Provides database session and change order service for creating change orders.

    Extract all parameters from the user's natural language request before calling.
    Infer impact_level from what the user describes.

    Args:
        project_id: UUID of the project this change order applies to
        title: Short title for the change order
        description: Detailed description of the change
        reason: Business justification for the change
        impact_level: Risk/impact level — one of LOW, MEDIUM, HIGH
        effective_date: When the change takes effect (ISO 8601 date string, optional)
        context: Injected tool execution context

    Returns:
        Dictionary with created change order details

    Raises:
        ValueError: If invalid input parameters or UUID format

    Example:
        >>> result = await create_change_order(
        ...     project_id="...",
        ...     title="Upgrade Controller System",
        ...     description="Replace legacy controllers with modern PLC system",
        ...     reason="Legacy system no longer supported",
        ...     impact_level="HIGH"
        ... )
        >>> print(f"Created change order: {result['id']}")
    """
    try:
        from app.services.change_order_service import ChangeOrderService

        service = ChangeOrderService(context.session)
        project_uuid = UUID(project_id)

        # Generate code before constructing schema
        code = await service.get_next_code(project_uuid)

        # Parse effective_date if provided
        parsed_effective_date = None
        if effective_date:
            parsed_effective_date = datetime.fromisoformat(effective_date).replace(
                tzinfo=UTC
            )

        # Create Pydantic schema
        co_data = ChangeOrderCreate(
            code=code,
            project_id=project_uuid,
            title=title,
            description=description,
            justification=reason,
            impact_level=impact_level,
            effective_date=parsed_effective_date,
        )

        # Call service method
        change_order = await service.create_change_order(
            change_order_in=co_data,
            actor_id=UUID(context.user_id),
            control_date=context.as_of,
        )

        # Convert to AI-friendly format
        return {
            "id": str(change_order.change_order_id),
            "code": change_order.code,
            "project_id": str(change_order.project_id),
            "title": change_order.title,
            "description": change_order.description,
            "status": change_order.status,
            "impact_level": change_order.impact_level,
            "branch_name": change_order.branch_name,
            "message": f"Change order {change_order.code} created with branch {change_order.branch_name}",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_change_order: {e}")
        return {"error": str(e)}


@ai_tool(
    name="submit_change_order_for_approval",
    description="Submit draft CO for approval.",
    permissions=["change-order-update"],
    category="change-orders",
    risk_level=RiskLevel.HIGH,
)
async def submit_change_order_for_approval(
    change_order_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Submit a change order for approval.

    Context: Provides database session and change order service for workflow management.

    Args:
        change_order_id: UUID of the draft change order
        context: Injected tool execution context

    Returns:
        Dictionary with updated change order status

    Raises:
        ValueError: If change_order_id is not a valid UUID format

    Example:
        >>> result = await submit_change_order_for_approval("...")
        >>> print(f"Change order submitted: {result['status']}")
    """
    try:
        from app.services.change_order_service import ChangeOrderService

        service = ChangeOrderService(context.session)

        # Update status to "Pending Approval"
        update_data = ChangeOrderUpdate(status="Pending Approval")
        # Call service method
        change_order = await service.update_change_order(
            change_order_id=UUID(change_order_id),
            change_order_in=update_data,
            actor_id=UUID(context.user_id),
            branch=context.branch_name or "main",
        )

        # Convert to AI-friendly format
        return {
            "id": str(change_order.change_order_id),
            "status": change_order.status,
            "approval_status": change_order.approval_status
            if hasattr(change_order, "approval_status")
            else None,
            "message": "Change order submitted for approval",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in submit_change_order_for_approval: {e}")
        return {"error": str(e)}


@ai_tool(
    name="approve_change_order",
    description="Approve a pending change order.",
    permissions=["change-order-approve"],
    category="change-orders",
    risk_level=RiskLevel.HIGH,
)
async def approve_change_order(
    change_order_id: str,
    comments: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Approve a change order.

    Context: Provides database session and change order service for approval workflow.

    Args:
        change_order_id: UUID of the change order to approve
        comments: Optional approval comments
        context: Injected tool execution context

    Returns:
        Dictionary with approved change order details

    Raises:
        ValueError: If change_order_id is not a valid UUID format

    Example:
        >>> result = await approve_change_order(
        ...     change_order_id="...",
        ...     comments="Approved within budget and timeline"
        ... )
        >>> print(f"Change order approved: {result['status']}")
    """
    try:
        from app.services.change_order_service import ChangeOrderService

        service = ChangeOrderService(context.session)

        # Update status to "Approved"
        update_data = ChangeOrderUpdate(
            status="Approved",
            approval_status="Approved",
        )
        # Call service method
        change_order = await service.update_change_order(
            change_order_id=UUID(change_order_id),
            change_order_in=update_data,
            actor_id=UUID(context.user_id),
            branch=context.branch_name or "main",
        )

        # Convert to AI-friendly format
        return {
            "id": str(change_order.change_order_id),
            "status": change_order.status,
            "approval_status": change_order.approval_status
            if hasattr(change_order, "approval_status")
            else None,
            "message": "Change order approved",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in approve_change_order: {e}")
        return {"error": str(e)}


@ai_tool(
    name="reject_change_order",
    description="Reject a pending change order.",
    permissions=["change-order-approve"],
    category="change-orders",
    risk_level=RiskLevel.HIGH,
)
async def reject_change_order(
    change_order_id: str,
    rejection_reason: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Reject a change order.

    Context: Provides database session and change order service for rejection workflow.

    Args:
        change_order_id: UUID of the change order to reject
        rejection_reason: Reason for rejection
        context: Injected tool execution context

    Returns:
        Dictionary with rejected change order details

    Raises:
        ValueError: If change_order_id is not a valid UUID format

    Example:
        >>> result = await reject_change_order(
        ...     change_order_id="...",
        ...     rejection_reason="Exceeds budget allocation"
        ... )
        >>> print(f"Change order rejected: {result['status']}")
    """
    try:
        from app.services.change_order_service import ChangeOrderService

        service = ChangeOrderService(context.session)

        # Update status to "Rejected"
        update_data = ChangeOrderUpdate(
            status="Rejected",
            approval_status="Rejected",
            rejection_reason=rejection_reason,
        )
        # Call service method
        change_order = await service.update_change_order(
            change_order_id=UUID(change_order_id),
            change_order_in=update_data,
            actor_id=UUID(context.user_id),
            branch=context.branch_name or "main",
        )

        # Convert to AI-friendly format
        return {
            "id": str(change_order.change_order_id),
            "status": change_order.status,
            "approval_status": change_order.approval_status
            if hasattr(change_order, "approval_status")
            else None,
            "message": "Change order rejected",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in reject_change_order: {e}")
        return {"error": str(e)}


# =============================================================================
# CHANGE ORDER ANALYSIS TOOLS
# =============================================================================


@ai_tool(
    name="analyze_change_order_impact",
    description="Analyze CO impact on budget and schedule.",
    permissions=["change-order-read"],
    category="change-orders",
    risk_level=RiskLevel.LOW,
)
async def analyze_change_order_impact(
    change_order_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Analyze change order impact.

    Context: Provides database session and change order service for impact analysis.

    Args:
        change_order_id: UUID of the change order to analyze
        context: Injected tool execution context

    Returns:
        Dictionary with detailed impact analysis including:
        - budget_impact: Financial impact
        - schedule_impact_days: Schedule delay in days
        - risk_level: "Low", "Medium", or "High"
        - recommendation: Approval recommendation

    Raises:
        ValueError: If change_order_id is not a valid UUID format

    Example:
        >>> result = await analyze_change_order_impact("...")
        >>> print(f"Budget Impact: ${result['budget_impact']}")
        >>> print(f"Schedule Impact: {result['schedule_impact_days']} days")
        >>> print(f"Risk Level: {result['risk_level']}")
    """
    try:
        from app.services.change_order_service import ChangeOrderService

        service = ChangeOrderService(context.session)

        # Get change order
        change_order = await service.get_as_of(
            UUID(change_order_id),
            branch=context.branch_name or "main",
            as_of=context.as_of,
        )

        if not change_order:
            return {"error": f"Change order {change_order_id} not found"}

        # Perform impact analysis (simplified example)
        # In production, this would involve complex calculations
        budget_impact = (
            float(change_order.budget_impact)
            if hasattr(change_order, "budget_impact") and change_order.budget_impact
            else 0.0
        )
        schedule_impact = (
            change_order.schedule_impact_days
            if hasattr(change_order, "schedule_impact_days")
            and change_order.schedule_impact_days
            else 0
        )

        # Determine risk level based on impact
        if budget_impact > 100000 or schedule_impact > 30:
            risk_level = "High"
        elif budget_impact > 50000 or schedule_impact > 15:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        return {
            "change_order_id": str(change_order.change_order_id),
            "budget_impact": budget_impact,
            "schedule_impact_days": schedule_impact,
            "risk_level": risk_level,
            "recommendation": "Approve" if risk_level == "Low" else "Review required",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in analyze_change_order_impact: {e}")
        return {"error": str(e)}


@ai_tool(
    name="delete_change_order",
    description="Delete a change order (Draft or Rejected only).",
    permissions=["change-order-delete"],
    category="change-orders",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_change_order(
    change_order_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Soft delete a change order (Draft or Rejected only).

    Context: Provides database session and change order service for deletion.

    Args:
        change_order_id: UUID of the change order to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deletion confirmation

    Raises:
        ValueError: If change_order_id is invalid or CO is not in a deletable status
        KeyError: If change order not found

    Example:
        >>> result = await delete_change_order("...")
        >>> print(f"Deleted change order: {result['id']}")
    """
    try:
        from uuid import UUID

        from app.services.change_order_service import ChangeOrderService

        service = ChangeOrderService(context.session)

        await service.delete_change_order(
            change_order_id=UUID(change_order_id),
            actor_id=UUID(context.user_id),
        )

        return {
            "id": change_order_id,
            "message": "Change order deleted",
        }
    except ValueError:
        return {"error": f"Invalid change order ID: {change_order_id}"}
    except KeyError:
        return {"error": f"Change order {change_order_id} not found"}
    except Exception as e:
        logger.error(f"Error in delete_change_order: {e}")
        return {"error": str(e)}


# =============================================================================
# BATCH CHANGE ORDER TOOLS
# =============================================================================


@ai_tool(
    name="batch_create_change_orders",
    description="Batch create change orders under a project. Max 50 items.",
    permissions=["change-order-create"],
    category="change-orders",
    risk_level=RiskLevel.HIGH,
)
async def batch_create_change_orders(
    project_id: str,
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create change orders under the same project.

    Args:
        project_id: UUID of the parent project
        items: List of dicts, each with {title, description, reason,
               budget_impact?, schedule_impact_days?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    try:
        from app.services.change_order_service import ChangeOrderService

        if len(items) > BATCH_SIZE_LIMIT:
            return {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"}

        if not items:
            return {"error": "No items provided"}

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("title"):
                return {"error": f"Item at index {i} is missing required field 'title'"}
            if not item.get("description"):
                return {
                    "error": f"Item at index {i} is missing required field 'description'"
                }
            if not item.get("reason"):
                return {
                    "error": f"Item at index {i} is missing required field 'reason'"
                }

        service = ChangeOrderService(context.session)
        actor_id = UUID(context.user_id)
        results: list[dict[str, Any]] = []

        for item in items:
            co_data = ChangeOrderCreate(  # type: ignore[call-arg]
                project_id=UUID(project_id),
                title=item["title"],
                description=item["description"],
                reason=item["reason"],
                budget_impact=item.get("budget_impact"),
                schedule_impact_days=item.get("schedule_impact_days"),
            )

            change_order = await service.create_change_order(
                change_order_in=co_data,
                actor_id=actor_id,
                control_date=context.as_of,
            )
            results.append(
                {
                    "id": str(change_order.change_order_id),
                    "title": change_order.title,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} change orders under project {project_id}",
        }
        return result
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in batch_create_change_orders: {e}")
        return {"error": str(e)}


# =============================================================================
# TEMPLATE USAGE NOTES
# =============================================================================

"""
CHANGE ORDER TOOL PATTERNS:

1. LIFECYCLE MANAGEMENT:
   - Create draft change order
   - Generate impact analysis
   - Submit for approval
   - Approve or reject
   - Implement approved changes

2. PERMISSIONS MODEL:
   - change-order-read: View change orders
   - change-order-create: Create draft change orders
   - change-order-update: Update change orders
   - change-order-approve: Approve/reject change orders (managers only)

3. WORKFLOW INTEGRATION:
   - Use create_change_order for new change orders (extract impact data from user request)
   - Use submit_change_order_for_approval to start workflow
   - Use approve/reject tools for decision making

4. BRANCHING SUPPORT:
   - Change orders support branch isolation
   - Negotiate changes in separate branch
   - Merge to main when approved

5. AUDIT TRAIL:
   - All changes are versioned
   - Complete audit history
   - Approval tracking

BEST PRACTICES:
   - Always generate impact analysis before approval
   - Document clear business reasons
   - Get stakeholder input for significant changes
   - Use branching to isolate negotiation phase
"""

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
from typing import Annotated, Any
from uuid import UUID

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import RiskLevel, ToolContext
from app.models.schemas.change_order import (
    ChangeOrderCreate,
    ChangeOrderUpdate,
)

logger = logging.getLogger(__name__)

MAX_LIST_LIMIT = 200


def _clamp_limit(limit: int) -> int:
    """Clamp limit to the maximum allowed value."""
    return min(limit, MAX_LIST_LIMIT)


# =============================================================================
# CHANGE ORDER CRUD TOOLS
# =============================================================================


@ai_tool(
    name="find_change_orders",
    description="Find change orders by ID or search/filter. Results are paginated; response includes total count and has_more.",
    permissions=["change-order-read"],
    category="change-orders",
    risk_level=RiskLevel.LOW,
)
async def find_change_orders(
    change_order_id: str | None = None,
    project_id: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Find change orders by ID or search/filter.

    Context: Provides database session and change order service for querying change orders.

    Args:
        change_order_id: UUID of a specific change order to retrieve (returns single)
        project_id: Optional project ID to filter change orders
        status: Optional status filter (e.g., "Draft", "Pending", "Approved", "Rejected")
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return (max 200)
        context: Injected tool execution context

    Returns:
        Single change order dict if change_order_id provided, otherwise list result.

    Raises:
        ValueError: If IDs are not valid UUID format
    """
    # Log temporal context for observability
    log_temporal_context("find_change_orders", context)
    limit = _clamp_limit(limit)

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
            "skip": skip,
            "limit": limit,
            "has_more": total > skip + len(change_orders),
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
    budget_impact: float | None = None,
    schedule_impact_days: int | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new change order.

    Context: Provides database session and change order service for creating change orders.

    Args:
        project_id: UUID of the project this change order applies to
        title: Short title for the change order
        description: Detailed description of the change
        reason: Business reason for the change
        budget_impact: Estimated budget impact (positive = increase)
        schedule_impact_days: Estimated schedule impact in days
        context: Injected tool execution context

    Returns:
        Dictionary with created change order details

    Raises:
        ValueError: If invalid input parameters or UUID format

    Example:
        >>> result = await create_change_order(
        ...     project_id="...",
        ...     title="Add Safety Sensors",
        ...     description="Install additional safety sensors on assembly line",
        ...     reason="Updated safety regulations require additional sensors",
        ...     budget_impact=25000.00,
        ...     schedule_impact_days=5
        ... )
        >>> print(f"Created change order: {result['id']}")
    """
    try:
        from app.services.change_order_service import ChangeOrderService

        service = ChangeOrderService(context.session)

        # Create Pydantic schema
        co_data = ChangeOrderCreate(  # type: ignore[call-arg]
            project_id=UUID(project_id),
            title=title,
            description=description,
            reason=reason,
            budget_impact=budget_impact,
            schedule_impact_days=schedule_impact_days,
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
            "project_id": str(change_order.project_id),
            "title": change_order.title,
            "description": change_order.description,
            "status": change_order.status,
            "budget_impact": float(change_order.budget_impact)
            if hasattr(change_order, "budget_impact") and change_order.budget_impact
            else 0.0,
            "schedule_impact_days": change_order.schedule_impact_days
            if hasattr(change_order, "schedule_impact_days")
            else None,
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in create_change_order: {e}")
        return {"error": str(e)}


@ai_tool(
    name="generate_change_order_draft",
    description="Generate draft CO from impact analysis.",
    permissions=["change-order-create"],
    category="change-orders",
    risk_level=RiskLevel.HIGH,
)
async def generate_change_order_draft(
    project_id: str,
    title: str,
    description: str,
    reason: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Generate a draft change order with impact analysis.

    Context: Provides database session and change order service for generating draft change orders.

    This tool analyzes the proposed change and generates a comprehensive
    change order draft including:
    - Budget impact analysis
    - Schedule impact assessment
    - Risk evaluation
    - Recommendation

    Args:
        project_id: UUID of the project
        title: Change order title
        description: Description of the change
        reason: Business reason for the change
        context: Injected tool execution context

    Returns:
        Dictionary with generated draft change order

    Raises:
        ValueError: If invalid input parameters or UUID format

    Example:
        >>> result = await generate_change_order_draft(
        ...     project_id="...",
        ...     title="Upgrade Controller System",
        ...     description="Replace legacy controllers with modern PLC system",
        ...     reason="Legacy system no longer supported, need modern features"
        ... )
        >>> print(f"Draft generated: {result['title']}")
        >>> print(f"Estimated impact: ${result['budget_impact']}")
    """
    try:
        from app.services.change_order_service import ChangeOrderService

        service = ChangeOrderService(context.session)

        # Call service method to generate draft
        # This analyzes impact and creates a comprehensive draft
        draft = await service.generate_draft(
            project_id=UUID(project_id),
            title=title,
            description=description,
            reason=reason,
            actor_id=UUID(context.user_id),
            branch=context.branch_name or "main",
        )

        # Extract AI analysis results from impact_analysis_results
        ai_analysis: dict[str, Any] = {}
        if hasattr(draft, "impact_analysis_results") and draft.impact_analysis_results:
            ai_data = draft.impact_analysis_results
            if isinstance(ai_data, dict) and "ai_analysis" in ai_data:
                ai_analysis = ai_data["ai_analysis"]

        # Convert to AI-friendly format
        return {
            "id": str(draft.change_order_id),
            "project_id": str(draft.project_id),
            "code": draft.code,
            "title": draft.title,
            "description": draft.description,
            "status": draft.status,
            "impact_level": draft.impact_level,
            "branch": draft.branch,
            "estimated_budget_impact": ai_analysis.get("estimated_budget_impact", 0.0),
            "estimated_schedule_impact_days": ai_analysis.get(
                "estimated_schedule_impact_days", 0
            ),
            "risk_assessment": ai_analysis.get("risk_assessment", "Medium"),
            "recommendation": ai_analysis.get("recommendation", "Review required"),
            "confidence_score": ai_analysis.get("confidence_score", 0.0),
            "affected_entities": ai_analysis.get("affected_entities", []),
            "message": f"Draft change order {draft.code} generated successfully",
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in generate_change_order_draft: {e}")
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
   - Use generate_change_order_draft for automated analysis
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

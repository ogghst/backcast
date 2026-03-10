"""Change Order tool template for wrapping ChangeOrderService methods.

This template shows how to create AI tools for change order management.
The key principle is:

    @ai_tool decorator MUST wrap existing service methods, NOT duplicate business logic

Change Orders in Backcast EVS:
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
"""

from typing import Any
from uuid import UUID

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext
from app.models.schemas.change_order import (
    ChangeOrderCreate,
    ChangeOrderUpdate,
)

# =============================================================================
# CHANGE ORDER CRUD TOOLS
# =============================================================================

@ai_tool(
    name="list_change_orders",
    description="List all change orders with optional filtering by project, status, "
    "or other criteria. Returns change orders with their approval status and impact.",
    permissions=["change-order-read"],
    category="change-orders",
)
async def list_change_orders(
    project_id: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    context: ToolContext = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """List change orders with optional filtering.

    Args:
        project_id: Optional project ID to filter change orders
        status: Optional status filter (e.g., "Draft", "Pending", "Approved", "Rejected")
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        context: Tool context with database session and user info

    Returns:
        Dictionary with:
        - change_orders: List of change order objects
        - total: Total number of change orders matching filters
        - skip: Number of records skipped
        - limit: Maximum records returned

    Example:
        >>> result = await list_change_orders(project_id="...", status="Pending")
        >>> print(f"Found {result['total']} pending change orders")
        >>> for co in result['change_orders']:
        ...     print(f"- {co['title']}: {co['status']}")
    """
    from app.services.change_order_service import ChangeOrderService

    service = ChangeOrderService(context.session)

    # Convert project_id to UUID if provided
    project_uuid = UUID(project_id) if project_id else None

    # Call service method
    change_orders, total = await service.get_change_orders(
        project_id=project_uuid,
        status=status,
        skip=skip,
        limit=limit,
    )

    # Convert to AI-friendly format
    return {
        "change_orders": [
            {
                "id": str(co.change_order_id),
                "project_id": str(co.project_id),
                "title": co.title,
                "description": co.description,
                "status": co.status,
                "approval_status": co.approval_status,
                "budget_impact": float(co.budget_impact) if co.budget_impact else 0.0,
                "schedule_impact_days": co.schedule_impact_days,
                "created_at": co.created_at.isoformat() if co.created_at else None,
            }
            for co in change_orders
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@ai_tool(
    name="get_change_order",
    description="Get detailed information about a specific change order, including "
    "impact analysis, approval history, and audit trail.",
    permissions=["change-order-read"],
    category="change-orders",
)
async def get_change_order(
    change_order_id: str,
    context: ToolContext = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get a single change order by ID.

    Args:
        change_order_id: UUID of the change order to retrieve
        context: Tool context with database session and user info

    Returns:
        Dictionary with change order details including impact analysis

    Example:
        >>> result = await get_change_order("123e4567-e89b-12d3-a456-426614174000")
        >>> print(f"Change Order: {result['title']}")
        >>> print(f"Budget Impact: ${result['budget_impact']}")
        >>> print(f"Approval Status: {result['approval_status']}")
    """
    from app.services.change_order_service import ChangeOrderService

    service = ChangeOrderService(context.session)

    # Call service method
    change_order = await service.get_by_id(UUID(change_order_id))

    # Convert to AI-friendly format
    return {
        "id": str(change_order.change_order_id),
        "project_id": str(change_order.project_id),
        "title": change_order.title,
        "description": change_order.description,
        "status": change_order.status,
        "approval_status": change_order.approval_status,
        "budget_impact": float(change_order.budget_impact) if change_order.budget_impact else 0.0,
        "schedule_impact_days": change_order.schedule_impact_days,
        "reason": change_order.reason,
        "created_at": change_order.created_at.isoformat() if change_order.created_at else None,
        "updated_at": change_order.updated_at.isoformat() if change_order.updated_at else None,
    }


@ai_tool(
    name="create_change_order",
    description="Create a new change order with impact analysis. "
    "The change order will be created in 'Draft' status and require approval workflow.",
    permissions=["change-order-create"],
    category="change-orders",
)
async def create_change_order(
    project_id: str,
    title: str,
    description: str,
    reason: str,
    budget_impact: float | None = None,
    schedule_impact_days: int | None = None,
    context: ToolContext = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Create a new change order.

    Args:
        project_id: UUID of the project this change order applies to
        title: Short title for the change order
        description: Detailed description of the change
        reason: Business reason for the change
        budget_impact: Estimated budget impact (positive = increase)
        schedule_impact_days: Estimated schedule impact in days
        context: Tool context with database session and user info

    Returns:
        Dictionary with created change order details

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
    from app.services.change_order_service import ChangeOrderService

    service = ChangeOrderService(context.session)

    # Create Pydantic schema
    co_data = ChangeOrderCreate(
        project_id=UUID(project_id),
        title=title,
        description=description,
        reason=reason,
        budget_impact=budget_impact,
        schedule_impact_days=schedule_impact_days,
    )

    # Call service method
    change_order = await service.create(co_data)

    # Convert to AI-friendly format
    return {
        "id": str(change_order.change_order_id),
        "project_id": str(change_order.project_id),
        "title": change_order.title,
        "description": change_order.description,
        "status": change_order.status,
        "budget_impact": float(change_order.budget_impact) if change_order.budget_impact else 0.0,
        "schedule_impact_days": change_order.schedule_impact_days,
    }


@ai_tool(
    name="generate_change_order_draft",
    description="Generate a draft change order based on impact analysis. "
    "Analyzes the impact and creates a comprehensive change order document.",
    permissions=["change-order-create"],
    category="change-orders",
)
async def generate_change_order_draft(
    project_id: str,
    title: str,
    description: str,
    reason: str,
    context: ToolContext = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Generate a draft change order with impact analysis.

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
        context: Tool context with database session and user info

    Returns:
        Dictionary with generated draft change order

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
    from app.services.change_order_service import ChangeOrderService

    service = ChangeOrderService(context.session)

    # Call service method to generate draft
    # This analyzes impact and creates a comprehensive draft
    draft = await service.generate_draft(
        project_id=UUID(project_id),
        title=title,
        description=description,
        reason=reason,
    )

    # Convert to AI-friendly format
    return {
        "id": str(draft.change_order_id),
        "project_id": str(draft.project_id),
        "title": draft.title,
        "description": draft.description,
        "status": draft.status,
        "budget_impact": float(draft.budget_impact) if draft.budget_impact else 0.0,
        "schedule_impact_days": draft.schedule_impact_days,
        "risk_assessment": draft.risk_assessment if hasattr(draft, 'risk_assessment') else None,
        "recommendation": draft.recommendation if hasattr(draft, 'recommendation') else None,
    }


@ai_tool(
    name="submit_change_order_for_approval",
    description="Submit a draft change order for approval. "
    "Initiates the approval workflow and notifies stakeholders.",
    permissions=["change-order-update"],
    category="change-orders",
)
async def submit_change_order_for_approval(
    change_order_id: str,
    context: ToolContext = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Submit a change order for approval.

    Args:
        change_order_id: UUID of the draft change order
        context: Tool context with database session and user info

    Returns:
        Dictionary with updated change order status

    Example:
        >>> result = await submit_change_order_for_approval("...")
        >>> print(f"Change order submitted: {result['status']}")
    """
    from app.services.change_order_service import ChangeOrderService

    service = ChangeOrderService(context.session)

    # Update status to "Pending Approval"
    update_data = ChangeOrderUpdate(status="Pending Approval")
    change_order = await service.update(UUID(change_order_id), update_data, branch="main")

    # Convert to AI-friendly format
    return {
        "id": str(change_order.change_order_id),
        "status": change_order.status,
        "approval_status": change_order.approval_status,
        "message": "Change order submitted for approval",
    }


@ai_tool(
    name="approve_change_order",
    description="Approve a change order. Requires manager or higher permissions. "
    "Changes the status to 'Approved' and allows implementation to begin.",
    permissions=["change-order-approve"],
    category="change-orders",
)
async def approve_change_order(
    change_order_id: str,
    comments: str | None = None,
    context: ToolContext = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Approve a change order.

    Args:
        change_order_id: UUID of the change order to approve
        comments: Optional approval comments
        context: Tool context with database session and user info

    Returns:
        Dictionary with approved change order details

    Example:
        >>> result = await approve_change_order(
        ...     change_order_id="...",
        ...     comments="Approved within budget and timeline"
        ... )
        >>> print(f"Change order approved: {result['status']}")
    """
    from app.services.change_order_service import ChangeOrderService

    service = ChangeOrderService(context.session)

    # Update status to "Approved"
    update_data = ChangeOrderUpdate(
        status="Approved",
        approval_status="Approved",
    )
    change_order = await service.update(UUID(change_order_id), update_data, branch="main")

    # Convert to AI-friendly format
    return {
        "id": str(change_order.change_order_id),
        "status": change_order.status,
        "approval_status": change_order.approval_status,
        "message": "Change order approved",
    }


@ai_tool(
    name="reject_change_order",
    description="Reject a change order. Requires manager or higher permissions. "
    "Changes the status to 'Rejected' and documents the reason.",
    permissions=["change-order-approve"],
    category="change-orders",
)
async def reject_change_order(
    change_order_id: str,
    rejection_reason: str,
    context: ToolContext = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Reject a change order.

    Args:
        change_order_id: UUID of the change order to reject
        rejection_reason: Reason for rejection
        context: Tool context with database session and user info

    Returns:
        Dictionary with rejected change order details

    Example:
        >>> result = await reject_change_order(
        ...     change_order_id="...",
        ...     rejection_reason="Exceeds budget allocation"
        ... )
        >>> print(f"Change order rejected: {result['status']}")
    """
    from app.services.change_order_service import ChangeOrderService

    service = ChangeOrderService(context.session)

    # Update status to "Rejected"
    update_data = ChangeOrderUpdate(
        status="Rejected",
        approval_status="Rejected",
        rejection_reason=rejection_reason,
    )
    change_order = await service.update(UUID(change_order_id), update_data, branch="main")

    # Convert to AI-friendly format
    return {
        "id": str(change_order.change_order_id),
        "status": change_order.status,
        "approval_status": change_order.approval_status,
        "message": "Change order rejected",
    }


# =============================================================================
# CHANGE ORDER ANALYSIS TOOLS
# =============================================================================

@ai_tool(
    name="analyze_change_order_impact",
    description="Analyze the impact of a proposed change order on project budget, "
    "schedule, and risk. Provides detailed impact assessment for decision making.",
    permissions=["change-order-read"],
    category="change-orders",
)
async def analyze_change_order_impact(
    change_order_id: str,
    context: ToolContext = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Analyze change order impact.

    Args:
        change_order_id: UUID of the change order to analyze
        context: Tool context with database session and user info

    Returns:
        Dictionary with detailed impact analysis

    Example:
        >>> result = await analyze_change_order_impact("...")
        >>> print(f"Budget Impact: ${result['budget_impact']}")
        >>> print(f"Schedule Impact: {result['schedule_impact_days']} days")
        >>> print(f"Risk Level: {result['risk_level']}")
    """
    from app.services.change_order_service import ChangeOrderService

    service = ChangeOrderService(context.session)

    # Get change order
    change_order = await service.get_by_id(UUID(change_order_id))

    # Perform impact analysis (simplified example)
    # In production, this would involve complex calculations
    budget_impact = float(change_order.budget_impact) if change_order.budget_impact else 0.0
    schedule_impact = change_order.schedule_impact_days or 0

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
# type: ignore[misc]

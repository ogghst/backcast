"""Batch tool template for bulk CRUD operations.

Provides batch variants of single-entity AI tools. These allow the LLM to
create, update, or delete multiple entities in a single tool call, reducing
round-trips and improving efficiency for bulk operations.

Key principles:
- Pre-validate ALL items before ANY database writes (fail-fast)
- Batch size limit of 50 items per call
- Single shared transaction -- all-or-nothing semantics
- Service-level errors propagate to the decorator for rollback

TEMPORAL CONTEXT PATTERN:
For temporal tools (those that work with versioned entities):
- Import temporal logging helpers: log_temporal_context, add_temporal_metadata
- Call log_temporal_context() at tool start for observability
- Call add_temporal_metadata() on return to include temporal context in results
"""

import logging
from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.temporal_logging import add_temporal_metadata, log_temporal_context
from app.ai.tools.types import RiskLevel, ToolContext

logger = logging.getLogger(__name__)

BATCH_SIZE_LIMIT = 50


# =============================================================================
# BATCH COST ELEMENT TOOLS
# =============================================================================


@ai_tool(
    name="create_cost_elements",
    description="Batch create multiple cost elements under the same WBE. "
    "All items share the parent wbe_id and optional schedule dates/progression type. "
    "Each item provides its own code, name, budget_amount, cost_element_type_id, and "
    "optional description. Pre-validates all codes for duplicates before creating any. "
    "Maximum 50 items per batch.",
    permissions=["cost-element-create"],
    category="cost-elements",
    risk_level=RiskLevel.HIGH,
)
async def create_cost_elements(
    wbe_id: str,
    items: list[dict[str, Any]],
    start_date: str | None = None,
    end_date: str | None = None,
    progression_type: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create cost elements under the same WBE.

    Args:
        wbe_id: UUID of the parent WBE
        items: List of dicts, each with {code, name, budget_amount, cost_element_type_id, description?}
        start_date: Optional shared schedule start date (ISO format)
        end_date: Optional shared schedule end date (ISO format)
        progression_type: Optional shared progression type (LINEAR, GAUSSIAN, LOGARITHMIC)
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    log_temporal_context("create_cost_elements", context)

    try:
        from datetime import datetime
        from typing import cast
        from uuid import UUID

        from sqlalchemy import func, select

        from app.models.domain.cost_element import CostElement as CostElementModel
        from app.models.schemas.cost_element import CostElementCreate
        from app.services.cost_element_service import CostElementService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("code"):
                return add_temporal_metadata(
                    {"error": f"Item at index {i} is missing required field 'code'"},
                    context,
                )
            if not item.get("name"):
                return add_temporal_metadata(
                    {"error": f"Item at index {i} is missing required field 'name'"},
                    context,
                )
            if item.get("budget_amount") is None:
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'budget_amount'"
                    },
                    context,
                )
            if not item.get("cost_element_type_id"):
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'cost_element_type_id'"
                    },
                    context,
                )

        # Check for duplicate codes within the batch
        codes = [it["code"] for it in items]
        if len(codes) != len(set(codes)):
            dupes = {c for c in codes if codes.count(c) > 1}
            return add_temporal_metadata(
                {"error": f"Duplicate codes in batch: {dupes}"}, context
            )

        # Check for duplicates in the database (single query)
        branch = context.branch_name or "main"
        dedup_stmt = select(
            CostElementModel.cost_element_id, CostElementModel.code
        ).where(
            CostElementModel.code.in_(codes),
            CostElementModel.wbe_id == UUID(wbe_id),
            CostElementModel.branch == branch,
            func.upper(cast(Any, CostElementModel).valid_time).is_(None),
            cast(Any, CostElementModel).deleted_at.is_(None),
        )
        dedup_result = await context.session.execute(dedup_stmt)
        existing_rows = dedup_result.all()
        if existing_rows:
            existing_codes = {row.code for row in existing_rows}
            return add_temporal_metadata(
                {
                    "error": f"Cost elements with codes already exist under this WBE: {existing_codes}. "
                    "Use a different code or update the existing cost elements.",
                    "existing_codes": list(existing_codes),
                },
                context,
            )

        # Parse shared schedule dates
        schedule_start = datetime.fromisoformat(start_date) if start_date else None
        schedule_end = datetime.fromisoformat(end_date) if end_date else None

        service = CostElementService(context.session)
        actor_id = UUID(context.user_id)
        results: list[dict[str, Any]] = []

        for item in items:
            ce_data = CostElementCreate(
                wbe_id=UUID(wbe_id),
                cost_element_type_id=UUID(item["cost_element_type_id"]),
                code=item["code"],
                name=item["name"],
                budget_amount=item["budget_amount"],
                description=item.get("description"),
                branch=branch,
                schedule_start_date=schedule_start,
                schedule_end_date=schedule_end,
                schedule_progression_type=progression_type,
            )
            cost_element = await service.create_cost_element(
                element_in=ce_data,
                actor_id=actor_id,
            )
            results.append(
                {
                    "id": str(cost_element.cost_element_id),
                    "code": cost_element.code,
                    "name": cost_element.name,
                    "budget_amount": float(cost_element.budget_amount)
                    if cost_element.budget_amount
                    else None,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} cost elements under WBE {wbe_id}",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata(
            {"error": f"Parent entity not found: {e}"}, context
        )
    except Exception as e:
        logger.error(f"Error in create_cost_elements: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="update_cost_elements",
    description="Batch update multiple cost elements. Each item must include cost_element_id "
    "and any fields to update (code, name, budget_amount, description, cost_element_type_id). "
    "Maximum 50 items per batch.",
    permissions=["cost-element-update"],
    category="cost-elements",
    risk_level=RiskLevel.HIGH,
)
async def update_cost_elements(
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch update cost elements.

    Args:
        items: List of dicts, each with {cost_element_id, code?, name?, budget_amount?, description?, cost_element_type_id?}
        context: Injected tool execution context

    Returns:
        Dictionary with updated items list, total count, and message
    """
    log_temporal_context("update_cost_elements", context)

    try:
        from uuid import UUID

        from app.models.schemas.cost_element import CostElementUpdate
        from app.services.cost_element_service import CostElementService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate cost_element_id on each item
        for i, item in enumerate(items):
            if not item.get("cost_element_id"):
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'cost_element_id'"
                    },
                    context,
                )

        service = CostElementService(context.session)
        actor_id = UUID(context.user_id)
        branch = context.branch_name or "main"
        results: list[dict[str, Any]] = []

        for item in items:
            update_kwargs: dict[str, Any] = {"branch": branch}
            if "code" in item and item["code"] is not None:
                update_kwargs["code"] = item["code"]
            if "name" in item and item["name"] is not None:
                update_kwargs["name"] = item["name"]
            if "budget_amount" in item and item["budget_amount"] is not None:
                update_kwargs["budget_amount"] = item["budget_amount"]
            if "description" in item and item["description"] is not None:
                update_kwargs["description"] = item["description"]
            if (
                "cost_element_type_id" in item
                and item["cost_element_type_id"] is not None
            ):
                update_kwargs["cost_element_type_id"] = UUID(
                    item["cost_element_type_id"]
                )

            update_data = CostElementUpdate(**update_kwargs)

            cost_element = await service.update(
                cost_element_id=UUID(item["cost_element_id"]),
                element_in=update_data,
                actor_id=actor_id,
            )
            results.append(
                {
                    "id": str(cost_element.cost_element_id),
                    "code": cost_element.code,
                    "name": cost_element.name,
                    "budget_amount": float(cost_element.budget_amount)
                    if cost_element.budget_amount
                    else None,
                }
            )

        result = {
            "updated": results,
            "total": len(results),
            "message": f"Updated {len(results)} cost elements",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in update_cost_elements: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="delete_cost_elements",
    description="Batch soft delete multiple cost elements. "
    "Cascades the delete to associated schedule baselines and forecasts. "
    "This is a destructive operation requiring expert execution mode. "
    "Maximum 50 items per batch.",
    permissions=["cost-element-delete"],
    category="cost-elements",
    risk_level=RiskLevel.CRITICAL,
)
async def delete_cost_elements(
    cost_element_ids: list[str],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch soft delete cost elements.

    Args:
        cost_element_ids: List of cost element UUIDs to delete
        context: Injected tool execution context

    Returns:
        Dictionary with deleted IDs list, total count, and message
    """
    log_temporal_context("delete_cost_elements", context)

    try:
        from uuid import UUID

        from app.services.cost_element_service import CostElementService

        if len(cost_element_ids) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not cost_element_ids:
            return add_temporal_metadata(
                {"error": "No cost element IDs provided"}, context
            )

        service = CostElementService(context.session)
        actor_id = UUID(context.user_id)
        branch = context.branch_name or "main"
        deleted_ids: list[str] = []

        for ce_id in cost_element_ids:
            await service.soft_delete(
                cost_element_id=UUID(ce_id),
                actor_id=actor_id,
                branch=branch,
            )
            deleted_ids.append(ce_id)

        result = {
            "deleted": deleted_ids,
            "total": len(deleted_ids),
            "message": f"Soft deleted {len(deleted_ids)} cost elements "
            "(schedule baselines and forecasts also deleted)",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in delete_cost_elements: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="get_budget_status_batch",
    description="Get budget status for multiple cost elements in a single call. "
    "Returns budget, used, remaining, and percentage for each cost element. "
    "Maximum 50 items per batch.",
    permissions=["cost-element-read"],
    category="cost-registration",
    risk_level=RiskLevel.LOW,
)
async def get_budget_status_batch(
    cost_element_ids: list[str],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch get budget status for cost elements.

    Args:
        cost_element_ids: List of cost element UUIDs
        context: Injected tool execution context

    Returns:
        Dictionary with budget statuses list and total count
    """
    log_temporal_context("get_budget_status_batch", context)

    try:
        from uuid import UUID

        from app.services.cost_registration_service import CostRegistrationService

        if len(cost_element_ids) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not cost_element_ids:
            return add_temporal_metadata(
                {"error": "No cost element IDs provided"}, context
            )

        service = CostRegistrationService(context.session)
        branch = context.branch_name or "main"
        statuses: list[dict[str, Any]] = []

        for ce_id in cost_element_ids:
            status = await service.get_budget_status(
                cost_element_id=UUID(ce_id),
                as_of=context.as_of,
                branch=branch,
            )
            statuses.append(
                {
                    "cost_element_id": str(status.cost_element_id),
                    "budget": float(status.budget),
                    "used": float(status.used),
                    "remaining": float(status.remaining),
                    "percentage": float(status.percentage),
                }
            )

        result = {
            "statuses": statuses,
            "total": len(statuses),
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in get_budget_status_batch: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="get_cost_element_summaries",
    description="Get comprehensive summaries for multiple cost elements in a single call. "
    "Each summary includes forecast data, budget status, and latest progress. "
    "Aggregates data from ForecastService, CostRegistrationService, and ProgressEntryService. "
    "Maximum 50 items per batch.",
    permissions=["forecast-read", "cost-registration-read", "progress-entry-read"],
    category="summary",
    risk_level=RiskLevel.LOW,
)
async def get_cost_element_summaries(
    cost_element_ids: list[str],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch get comprehensive summaries for cost elements.

    Args:
        cost_element_ids: List of cost element UUIDs
        context: Injected tool execution context

    Returns:
        Dictionary with summaries list and total count
    """
    log_temporal_context("get_cost_element_summaries", context)

    try:
        from uuid import UUID

        from app.services.cost_registration_service import CostRegistrationService
        from app.services.forecast_service import ForecastService
        from app.services.progress_entry_service import ProgressEntryService

        if len(cost_element_ids) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not cost_element_ids:
            return add_temporal_metadata(
                {"error": "No cost element IDs provided"}, context
            )

        forecast_service = ForecastService(context.session)
        cost_service = CostRegistrationService(context.session)
        progress_service = ProgressEntryService(context.session)
        branch = context.branch_name or "main"

        summaries: list[dict[str, Any]] = []

        for ce_id in cost_element_ids:
            try:
                ce_uuid = UUID(ce_id)
            except ValueError:
                summaries.append({"cost_element_id": ce_id, "error": "Invalid UUID"})
                continue

            summary: dict[str, Any] = {"cost_element_id": ce_id}

            # Get forecast data
            try:
                forecast = await forecast_service.get_for_cost_element(
                    cost_element_id=ce_uuid,
                    branch=branch,
                )
                if forecast:
                    summary["forecast"] = {
                        "id": str(forecast.forecast_id),
                        "eac_amount": float(forecast.eac_amount)
                        if forecast.eac_amount
                        else None,
                        "basis_of_estimate": forecast.basis_of_estimate,
                        "branch": forecast.branch,
                    }
                else:
                    summary["forecast"] = None
            except Exception:
                summary["forecast"] = None

            # Get budget status
            try:
                budget_status = await cost_service.get_budget_status(
                    cost_element_id=ce_uuid,
                    as_of=context.as_of,
                    branch=branch,
                )
                summary["budget_status"] = {
                    "budget": float(budget_status.budget),
                    "used": float(budget_status.used),
                    "remaining": float(budget_status.remaining),
                    "percentage": float(budget_status.percentage),
                }
            except Exception:
                summary["budget_status"] = None

            # Get latest progress
            try:
                progress = await progress_service.get_latest_progress(
                    cost_element_id=ce_uuid,
                    as_of=context.as_of,
                )
                if progress:
                    summary["progress"] = {
                        "progress_entry_id": str(progress.progress_entry_id),
                        "progress_percentage": float(progress.progress_percentage)
                        if progress.progress_percentage
                        else None,
                        "notes": progress.notes,
                    }
                else:
                    summary["progress"] = None
            except Exception:
                summary["progress"] = None

            summaries.append(summary)

        result = {
            "summaries": summaries,
            "total": len(summaries),
            "message": f"Retrieved summaries for {len(summaries)} cost elements",
        }
        return add_temporal_metadata(result, context)
    except Exception as e:
        logger.error(f"Error in get_cost_element_summaries: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


# =============================================================================
# BATCH WBE TOOLS
# =============================================================================


@ai_tool(
    name="create_wbes",
    description="Batch create multiple WBEs under the same project. "
    "All items share the parent project_id. Each item provides its own name, code, "
    "and optional description and parent_wbe_id. Pre-validates all codes for duplicates "
    "before creating any. Maximum 50 items per batch.",
    permissions=["wbe-create"],
    category="wbe",
    risk_level=RiskLevel.HIGH,
)
async def create_wbes(
    project_id: str,
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create WBEs under the same project.

    Args:
        project_id: UUID of the parent project
        items: List of dicts, each with {name, code, description?, parent_wbe_id?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    log_temporal_context("create_wbes", context)

    try:
        from uuid import UUID

        from app.models.schemas.wbe import WBECreate
        from app.services.wbe import WBEService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("code"):
                return add_temporal_metadata(
                    {"error": f"Item at index {i} is missing required field 'code'"},
                    context,
                )
            if not item.get("name"):
                return add_temporal_metadata(
                    {"error": f"Item at index {i} is missing required field 'name'"},
                    context,
                )

        # Check for duplicate codes within the batch
        codes = [it["code"] for it in items]
        if len(codes) != len(set(codes)):
            dupes = {c for c in codes if codes.count(c) > 1}
            return add_temporal_metadata(
                {"error": f"Duplicate codes in batch: {dupes}"}, context
            )

        service = WBEService(context.session)
        project_uuid = UUID(project_id)

        # Pre-validate: check all codes against the database
        for code in codes:
            existing = await service.get_by_code(code, project_uuid)
            if existing:
                return add_temporal_metadata(
                    {
                        "error": f"A WBE with code '{code}' already exists in this project "
                        f"(ID: {existing.wbe_id}, name: '{existing.name}'). "
                        "Use a different code or update the existing WBE.",
                        "existing_id": str(existing.wbe_id),
                        "existing_code": code,
                    },
                    context,
                )

        actor_id = UUID(context.user_id)
        branch = context.branch_name or "main"
        results: list[dict[str, Any]] = []

        for item in items:
            wbe_data = WBECreate(
                project_id=project_uuid,
                name=item["name"],
                code=item["code"],
                description=item.get("description"),
                parent_wbe_id=UUID(item["parent_wbe_id"])
                if item.get("parent_wbe_id")
                else None,
                branch=branch,
            )
            wbe = await service.create_wbe(wbe_data, actor_id=actor_id)
            results.append(
                {
                    "id": str(wbe.wbe_id),
                    "name": wbe.name,
                    "code": wbe.code,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} WBEs under project {project_id}",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in create_wbes: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


@ai_tool(
    name="update_wbes",
    description="Batch update multiple WBEs. Each item must include wbe_id and any "
    "fields to update (name, description, revenue_allocation). "
    "Maximum 50 items per batch.",
    permissions=["wbe-update"],
    category="wbe",
    risk_level=RiskLevel.HIGH,
)
async def update_wbes(
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch update WBEs.

    Args:
        items: List of dicts, each with {wbe_id, name?, description?, revenue_allocation?}
        context: Injected tool execution context

    Returns:
        Dictionary with updated items list, total count, and message
    """
    log_temporal_context("update_wbes", context)

    try:
        from decimal import Decimal
        from uuid import UUID

        from app.models.schemas.wbe import WBEUpdate
        from app.services.wbe import WBEService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate wbe_id on each item
        for i, item in enumerate(items):
            if not item.get("wbe_id"):
                return add_temporal_metadata(
                    {"error": f"Item at index {i} is missing required field 'wbe_id'"},
                    context,
                )

        service = WBEService(context.session)
        actor_id = UUID(context.user_id)
        branch = context.branch_name or "main"
        results: list[dict[str, Any]] = []

        for item in items:
            update_kwargs: dict[str, Any] = {"branch": branch}
            if "name" in item and item["name"] is not None:
                update_kwargs["name"] = item["name"]
            if "description" in item and item["description"] is not None:
                update_kwargs["description"] = item["description"]
            if "revenue_allocation" in item and item["revenue_allocation"] is not None:
                update_kwargs["revenue_allocation"] = Decimal(
                    str(item["revenue_allocation"])
                )

            if len(update_kwargs) == 1:  # Only branch, no actual fields
                return add_temporal_metadata(
                    {
                        "error": f"Item with wbe_id '{item['wbe_id']}' has no fields to update"
                    },
                    context,
                )

            update_data = WBEUpdate(**update_kwargs)

            wbe = await service.update_wbe(
                wbe_id=UUID(item["wbe_id"]),
                wbe_in=update_data,
                actor_id=actor_id,
            )
            results.append(
                {
                    "id": str(wbe.wbe_id),
                    "name": wbe.name,
                    "code": wbe.code,
                }
            )

        result = {
            "updated": results,
            "total": len(results),
            "message": f"Updated {len(results)} WBEs",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"WBE not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in update_wbes: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


# =============================================================================
# BATCH COST REGISTRATION TOOLS
# =============================================================================


@ai_tool(
    name="create_cost_registrations",
    description="Batch register actual costs against multiple cost elements. "
    "Each item carries its own cost_element_id, amount, and optional description, "
    "invoice_number, vendor_reference, registration_date. "
    "Maximum 50 items per batch.",
    permissions=["cost-registration-create"],
    category="cost-registration",
    risk_level=RiskLevel.HIGH,
)
async def create_cost_registrations(
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create cost registrations.

    Args:
        items: List of dicts, each with {cost_element_id, amount, description?, invoice_number?, vendor_reference?, registration_date?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    log_temporal_context("create_cost_registrations", context)

    try:
        from datetime import datetime
        from decimal import Decimal
        from uuid import UUID

        from app.models.schemas.cost_registration import CostRegistrationCreate
        from app.services.cost_registration_service import CostRegistrationService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("cost_element_id"):
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'cost_element_id'"
                    },
                    context,
                )
            if item.get("amount") is None:
                return add_temporal_metadata(
                    {"error": f"Item at index {i} is missing required field 'amount'"},
                    context,
                )

        service = CostRegistrationService(context.session)
        actor_id = UUID(context.user_id)
        branch = context.branch_name or "main"
        results: list[dict[str, Any]] = []

        for item in items:
            reg_date = None
            if item.get("registration_date"):
                reg_date = datetime.fromisoformat(item["registration_date"])

            registration_in = CostRegistrationCreate(
                cost_element_id=UUID(item["cost_element_id"]),
                amount=Decimal(str(item["amount"])),
                description=item.get("description"),
                invoice_number=item.get("invoice_number"),
                vendor_reference=item.get("vendor_reference"),
                registration_date=reg_date,
            )

            registration = await service.create_cost_registration(
                registration_in=registration_in,
                actor_id=actor_id,
                branch=branch,
            )
            results.append(
                {
                    "id": str(registration.cost_registration_id),
                    "cost_element_id": str(registration.cost_element_id),
                    "amount": float(registration.amount)
                    if registration.amount
                    else None,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} cost registrations",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in create_cost_registrations: {e}")
        return add_temporal_metadata({"error": str(e)}, context)


# =============================================================================
# BATCH PROGRESS ENTRY TOOLS
# =============================================================================


@ai_tool(
    name="create_progress_entries",
    description="Batch create progress entries for multiple cost elements. "
    "Each item carries its own cost_element_id, progress_percentage, and optional notes. "
    "Maximum 50 items per batch.",
    permissions=["progress-entry-create"],
    category="progress-entry",
    risk_level=RiskLevel.HIGH,
)
async def create_progress_entries(
    items: list[dict[str, Any]],
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Batch create progress entries.

    Args:
        items: List of dicts, each with {cost_element_id, progress_percentage, notes?}
        context: Injected tool execution context

    Returns:
        Dictionary with created items list, total count, and message
    """
    log_temporal_context("create_progress_entries", context)

    try:
        from decimal import Decimal
        from uuid import UUID

        from app.models.schemas.progress_entry import ProgressEntryCreate
        from app.services.progress_entry_service import ProgressEntryService

        if len(items) > BATCH_SIZE_LIMIT:
            return add_temporal_metadata(
                {"error": f"Batch size exceeds maximum of {BATCH_SIZE_LIMIT} items"},
                context,
            )

        if not items:
            return add_temporal_metadata({"error": "No items provided"}, context)

        # Validate required fields on each item
        for i, item in enumerate(items):
            if not item.get("cost_element_id"):
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'cost_element_id'"
                    },
                    context,
                )
            if item.get("progress_percentage") is None:
                return add_temporal_metadata(
                    {
                        "error": f"Item at index {i} is missing required field 'progress_percentage'"
                    },
                    context,
                )

        service = ProgressEntryService(context.session)
        actor_id = UUID(context.user_id)
        results: list[dict[str, Any]] = []

        for item in items:
            progress_in = ProgressEntryCreate(
                cost_element_id=UUID(item["cost_element_id"]),
                progress_percentage=Decimal(str(item["progress_percentage"])),
                notes=item.get("notes"),
            )

            progress = await service.create(
                actor_id=actor_id,
                progress_in=progress_in,
                control_date=context.as_of,
            )
            results.append(
                {
                    "progress_entry_id": str(progress.progress_entry_id),
                    "cost_element_id": str(progress.cost_element_id),
                    "progress_percentage": float(progress.progress_percentage)
                    if progress.progress_percentage
                    else None,
                }
            )

        result = {
            "created": results,
            "total": len(results),
            "message": f"Created {len(results)} progress entries",
        }
        return add_temporal_metadata(result, context)
    except ValueError as e:
        return add_temporal_metadata({"error": f"Invalid input: {e}"}, context)
    except KeyError as e:
        return add_temporal_metadata({"error": f"Cost element not found: {e}"}, context)
    except Exception as e:
        logger.error(f"Error in create_progress_entries: {e}")
        return add_temporal_metadata({"error": str(e)}, context)

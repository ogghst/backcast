"""Project context tools for AI agent.

Provides read-only access to project context information for the LLM.
Tools in this module do NOT modify project state - they only provide
visibility into the current project context.
"""

from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext


@ai_tool(
    name="get_project_context",
    description="Returns the current project context for the session. "
    "This provides READ-ONLY information about the project: "
    "project_id, project_name, project_code, user's role in the project. "
    "NOTE: This is informational only. Project context is enforced at the system level. "
    "The project scope is immutable for the session duration - to change projects, "
    "the user must navigate to a different project chat URL.",
    permissions=[],  # No special permissions required
    category="context",
)
async def get_project_context(
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Returns the current project context for the session.

    This tool provides the LLM with visibility into project context
    WITHOUT giving it control. Project context remains immutable
    and can only be changed by navigating to a different project URL.

    Context: Read-only tool for LLM awareness of project state.
    The LLM can query this tool to understand what project context
    it's operating in, but cannot modify it.

    Args:
        context: Injected tool execution context (contains project_id)

    Returns:
        Dictionary containing:
            - project_id: Project UUID or None (global scope)
            - project_name: Project name or None
            - project_code: Project code or None
            - user_role: User's role in the project (admin/editor/viewer) or None
            - scope: "project" if project_id is set, "global" otherwise

    Example:
        >>> await get_project_context(context)
        {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_name": "Automation Line 1",
            "project_code": "AL1",
            "user_role": "editor",
            "scope": "project"
        }

        >>> await get_project_context(context)  # No project context
        {
            "project_id": None,
            "project_name": None,
            "project_code": None,
            "user_role": None,
            "scope": "global"
        }

    Security:
        This tool is READ-ONLY. It only reads from ToolContext and never
        modifies project state. Project context can only be changed
        by navigating to a different project URL, providing maximum security
        against prompt injection attacks.
    """
    # If no project_id is set, return global scope
    if not context.project_id:
        return {
            "project_id": None,
            "project_name": None,
            "project_code": None,
            "user_role": None,
            "scope": "global",
        }

    # Project context is set - fetch project details and user role
    try:
        from uuid import UUID

        from app.core.rbac import get_rbac_service

        # Validate project_id format
        project_uuid = UUID(context.project_id)

        # Inject session for project-level access checks
        rbac_service = get_rbac_service()
        if hasattr(rbac_service, "session") and rbac_service.session is None:
            rbac_service.session = context.session

        # Get project details
        from app.core.versioning.enums import BranchMode

        branch = context.branch_name or "main"
        branch_mode = BranchMode.MERGE if context.branch_mode == "merged" else BranchMode.STRICT

        project = await context.project_service.get_as_of(
            entity_id=project_uuid,
            as_of=context.as_of,
            branch=branch,
            branch_mode=branch_mode,
        )

        if not project:
            # Project not found (may have been deleted)
            return {
                "project_id": context.project_id,
                "project_name": None,
                "project_code": None,
                "user_role": None,
                "scope": "project",
                "error": "Project not found or access denied",
            }

        # Get user's role in the project
        user_uuid = UUID(context.user_id)
        user_role = await rbac_service.get_project_role(
            user_id=user_uuid,
            project_id=project_uuid,
        )

        return {
            "project_id": context.project_id,
            "project_name": project.name,
            "project_code": project.code,
            "user_role": user_role,  # Will be None if not a member
            "scope": "project",
        }

    except (ValueError, TypeError):
        # Invalid UUID format
        return {
            "project_id": context.project_id,
            "project_name": None,
            "project_code": None,
            "user_role": None,
            "scope": "project",
            "error": "Invalid project ID format",
        }
    except Exception as e:
        # Error fetching project details
        return {
            "project_id": context.project_id,
            "project_name": None,
            "project_code": None,
            "user_role": None,
            "scope": "project",
            "error": f"Error fetching project details: {str(e)}",
        }

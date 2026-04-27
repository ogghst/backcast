"""Shared subagent/specialist compilation logic.

Extracts the common tool-filtering and agent-compilation pattern used by both
DeepAgentOrchestrator and SupervisorOrchestrator so they don't duplicate the
same ~80-line method.
"""

import logging
from typing import Any

from langchain.agents import create_agent as langchain_create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.ai.middleware.backcast_security import BackcastSecurityMiddleware
from app.ai.middleware.temporal_context import TemporalContextMiddleware
from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant for the Backcast project budget management system.

You can help with:
- Listing and viewing projects
- Getting detailed project information
- Earned value management calculations

When providing information:
- Be accurate and rely on the project data
- Use three-letter codes for project status (e.g., "ACT" for active, "PLN" for planned)
- Present data in clear, structured formats
- Only use tools you have been explicitly enabled for the assistant

When using tools:
- Always use the exact field names expected by the tools
- For status filters, use three-letter codes like 'ACT', 'PLN', 'CLS'
- Use search to find projects by code or name
"""


def compile_subagents(
    model: str | BaseChatModel,
    context: ToolContext,
    subagent_configs: list[dict[str, Any]],
    available_tools: list[BaseTool],
    allowed_tools: list[str] | None = None,
    *,
    label: str = "subagent",
) -> list[dict[str, Any]]:
    """Compile subagent configs into runnable LangChain agent graphs.

    Applies per-config tool filtering, creates the Backcast middleware stack
    (TemporalContextMiddleware + BackcastSecurityMiddleware), and compiles each
    via ``langchain_create_agent()``.

    Args:
        model: LLM model string or instance.
        context: ToolContext with user permissions and temporal parameters.
        subagent_configs: List of subagent configuration dicts (name, description,
            system_prompt, allowed_tools, structured_output_schema).
        available_tools: All tools after execution-mode and RBAC filtering.
        allowed_tools: Optional tool-name whitelist from the assistant config.
        label: Log label ("subagent" or "specialist").

    Returns:
        List of dicts with keys: name, description, runnable,
        structured_output_schema, tools.
    """
    middleware = [
        TemporalContextMiddleware(context),
        BackcastSecurityMiddleware(
            context,
            tools=available_tools,
            interrupt_node=None,
        ),
    ]

    results: list[dict[str, Any]] = []

    for cfg in subagent_configs:
        name = cfg.get("name", "")
        description = cfg.get("description", "")
        system_prompt = cfg.get("system_prompt", "")
        allowed_tool_names = cfg.get("allowed_tools")
        schema = cfg.get("structured_output_schema")

        # Resolve the tool-name list for this subagent
        if allowed_tool_names is None:
            filtered_tool_names = (
                list(allowed_tools)
                if allowed_tools is not None
                else [t.name for t in available_tools]
            )
        else:
            if allowed_tools is not None:
                filtered_tool_names = [
                    n for n in allowed_tool_names if n in allowed_tools
                ]
            else:
                filtered_tool_names = allowed_tool_names

        subagent_tools = [t for t in available_tools if t.name in filtered_tool_names]

        if not subagent_tools:
            logger.warning(
                "%s '%s' has no tools after filtering — skipping", label, name
            )
            continue

        runnable = langchain_create_agent(
            model=model,
            tools=subagent_tools,
            system_prompt=system_prompt,
            middleware=middleware,
            response_format=schema,
            name=name,
        )

        results.append(
            {
                "name": name,
                "description": description,
                "runnable": runnable,
                "structured_output_schema": schema,
                "tools": subagent_tools,
            }
        )
        logger.info("Compiled %s '%s' with %d tools", label, name, len(subagent_tools))

    return results

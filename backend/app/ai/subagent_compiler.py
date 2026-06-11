"""Shared subagent/specialist compilation logic.

Extracts the common tool-filtering and agent-compilation pattern used by
SupervisorOrchestrator so it doesn't inline the same ~80-line method.
"""

import logging
import types
from typing import Any

from langchain.agents import create_agent as langchain_create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.ai.config import AI_SEQUENTIAL_TOOL_CALLS, AgentConfig
from app.ai.middleware.backcast_security import BackcastSecurityMiddleware
from app.ai.middleware.sequential_tool_calls import SequentialToolCallsMiddleware
from app.ai.middleware.temporal_context import TemporalContextMiddleware
from app.ai.schemas import SpecialistOutput
from app.ai.tools import (
    create_project_tools,
    filter_tools_by_execution_mode,
    filter_tools_by_role,
)
from app.ai.tools.sequential_tool_node import SequentialToolNode
from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)


DEFAULT_SYSTEM_PROMPT = """You are a Backcast project management assistant.
Before calling tools, review your briefing context to avoid redundant queries.

When using tools:
- Use exact field names expected by the tools
- For status filters, use three-letter codes like 'ACT', 'PLN', 'CLS'
- Use search to find projects by code or name
"""


async def filter_tools_for_context(
    context: ToolContext,
    config: AgentConfig,
) -> list[BaseTool]:
    """Create project tools and apply execution-mode + RBAC filtering.

    Centralizes the identical tool-filtering pipeline shared by both
    orchestrators.

    Args:
        context: ToolContext with user permissions and temporal parameters.
        config: AgentConfig with optional role and allowed_tools filters.

    Returns:
        Filtered list of tools available for the current request.
    """
    all_tools = create_project_tools(context)

    if config.allowed_tools is not None:
        all_tools = [t for t in all_tools if t.name in config.allowed_tools]

    all_tools = filter_tools_by_execution_mode(all_tools, context.execution_mode)

    if config.assistant_role is not None:
        all_tools = await filter_tools_by_role(all_tools, config.assistant_role)

    if config.user_role is not None:
        all_tools = await filter_tools_by_role(all_tools, config.user_role)

    return all_tools


def build_backcast_middleware(
    context: ToolContext,
    tools: list[BaseTool],
) -> list[Any]:
    """Build the standard Backcast middleware stack.

    Returns:
        List with TemporalContextMiddleware and BackcastSecurityMiddleware.
    """
    middleware: list[Any] = []
    if AI_SEQUENTIAL_TOOL_CALLS:
        middleware.append(SequentialToolCallsMiddleware())
    middleware.extend(
        [
            TemporalContextMiddleware(context),
            BackcastSecurityMiddleware(
                context,
                tools=tools,
                interrupt_node=None,
            ),
        ]
    )
    return middleware


def compile_subagents(
    model: str | BaseChatModel,
    context: ToolContext,
    subagent_configs: list[dict[str, Any]],
    available_tools: list[BaseTool],
    allowed_tools: list[str] | None = None,
    *,
    specialist_models: dict[str, BaseChatModel] | None = None,
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
    results: list[dict[str, Any]] = []

    for cfg in subagent_configs:
        name = cfg.get("name", "")
        specialist_model = (specialist_models or {}).get(name, model)
        description = cfg.get("description", "")
        presentation_prompt = cfg.get("presentation_prompt", description)
        system_prompt = cfg.get("system_prompt", "")
        allowed_tool_names = cfg.get("allowed_tools")
        schema = cfg.get("structured_output_schema") or SpecialistOutput

        # Resolve the tool-name list for this subagent.
        # Convention:
        #   allowed_tools = None      → no tools ( specialist has no regular tool access)
        #   allowed_tools = ["*"]     → all available tools (catch-all / fallback agents)
        #   allowed_tools = ["t1",…]  → only the listed tools
        if allowed_tool_names is None:
            # No tools configured — specialist gets nothing from the regular pool.
            subagent_tools = []
        elif "*" in allowed_tool_names:
            # Wildcard: all tools (used by general_purpose / fallback agents).
            filtered_tool_names = (
                list(allowed_tools)
                if allowed_tools is not None
                else [t.name for t in available_tools]
            )
            subagent_tools = [
                t for t in available_tools if t.name in filtered_tool_names
            ]
        else:
            if allowed_tools is not None:
                filtered_tool_names = [
                    n for n in allowed_tool_names if n in allowed_tools
                ]
            else:
                filtered_tool_names = allowed_tool_names

            subagent_tools = [
                t for t in available_tools if t.name in filtered_tool_names
            ]

        if not subagent_tools:
            logger.warning(
                "%s '%s' has no tools after filtering — skipping", label, name
            )
            continue

        # Fresh middleware per subagent to avoid mutable state leakage
        middleware = build_backcast_middleware(context, subagent_tools)

        runnable = langchain_create_agent(
            model=specialist_model,
            tools=subagent_tools,
            system_prompt=system_prompt,
            middleware=middleware,
            response_format=schema,
            name=name,
        )

        # Belt-and-suspenders: replace the tools node's afunc at the instance
        # level so the sequential version is used even if the class-level
        # monkey-patch is bypassed by LangGraph's internal dispatch.
        if AI_SEQUENTIAL_TOOL_CALLS:
            tools_spec = runnable.builder.nodes.get("tools")
            if tools_spec is not None and hasattr(tools_spec, "runnable"):
                tool_node_instance = tools_spec.runnable
                if hasattr(tool_node_instance, "afunc"):
                    tool_node_instance.afunc = types.MethodType(
                        SequentialToolNode._afunc, tool_node_instance
                    )
                    logger.info(
                        "Replaced tools node afunc for specialist '%s': %s → sequential",
                        name,
                        type(tool_node_instance).__name__,
                    )
                else:
                    logger.warning(
                        "Tools node for specialist '%s' has no afunc attribute (type=%s)",
                        name,
                        type(tool_node_instance).__name__,
                    )
            else:
                logger.warning(
                    "No 'tools' node found in specialist '%s' graph (nodes=%s)",
                    name,
                    list(runnable.builder.nodes.keys()),
                )

        results.append(
            {
                "name": name,
                "description": description,
                "presentation_prompt": presentation_prompt,
                "runnable": runnable,
                "structured_output_schema": schema,
                "tools": subagent_tools,
            }
        )
        logger.info("Compiled %s '%s' with %d tools", label, name, len(subagent_tools))

    return results

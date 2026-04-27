"""Supervisor orchestrator for the handoff-based agent delegation pattern.

Builds a parent StateGraph where the supervisor routes requests to specialist
agents via handoff tools. Each specialist is a compiled ``create_agent()`` graph
embedded as a subgraph node. Specialists share full message history through
the parent graph's shared state.

The supervisor also retains the ``task`` tool for parallel batch operations
where context isolation is acceptable.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents import create_agent as langchain_create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph

from app.ai.config import AgentConfig
from app.ai.handoff_tools import create_all_handoff_tools
from app.ai.middleware.backcast_security import BackcastSecurityMiddleware
from app.ai.middleware.temporal_context import TemporalContextMiddleware
from app.ai.subagent_compiler import compile_subagents
from app.ai.subagents import get_all_subagents
from app.ai.supervisor_state import BackcastSupervisorState
from app.ai.tools import (
    create_project_tools,
    filter_tools_by_execution_mode,
    filter_tools_by_role,
)
from app.ai.tools.subagent_task import build_task_tool
from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)

SUPERVISOR_SYSTEM_PROMPT = """You are a helpful AI assistant for the Backcast project budget management system.

You act as a supervisor that routes user requests to the appropriate specialist agent. You have two mechanisms for delegation:

## 1. Handoff Tools (Preferred)
Use handoff tools to transfer control to a specialist. The specialist will see the full conversation history and can respond directly to the user. Use handoff for:
- Any request that requires domain-specific tools
- Multi-turn conversations where context preservation matters
- Follow-up questions to previous specialist interactions

## 2. Task Tool (Secondary)
Use the task tool when you need to launch parallel batch operations with isolated context. Use task for:
- Explicitly parallel cross-domain queries
- Batch operations where context isolation is acceptable

## Routing Guidelines
- Project CRUD, WBEs, cost elements, cost tracking → project_manager
- EVM calculations, performance analysis → evm_analyst
- Change orders, impact analysis → change_order_manager
- User/department management → user_admin
- Diagrams, visualizations → visualization_specialist
- Forecasts, schedule baselines → forecast_manager
- Unclear or cross-cutting → general_purpose

After receiving a response from a specialist, provide a brief, helpful synthesis.
"""

# Suffix appended when handoff specialists are available
_HANDOFF_SUFFIX = """
IMPORTANT: You do NOT have direct access to Backcast tools.
ALL Backcast operations must be delegated to specialists via handoff tools or the task tool.

Prefer handoff tools over the task tool for most requests — handoff preserves full conversation context.
"""


class SupervisorOrchestrator:
    """Orchestrator that builds a supervisor + handoff agent graph.

    Creates a parent StateGraph where the supervisor routes to specialist
    agents via ``Command(goto=...)`` handoff tools. Each specialist is a
    compiled ``create_agent()`` graph with its own filtered tools and
    middleware.

    Attributes:
        model: LangChain chat model instance.
        context: ToolContext with user permissions and temporal parameters.
        system_prompt: Optional custom system prompt for the supervisor.
        enable_subagents: Whether to compile specialist agents.
        interrupt_node: Optional InterruptNode for approval workflow.
    """

    def __init__(
        self,
        model: str | BaseChatModel,
        context: ToolContext,
        system_prompt: str | None = None,
        enable_subagents: bool = True,
        interrupt_node: Any = None,
    ) -> None:
        self.model = model
        self.context = context
        self.system_prompt = system_prompt
        self.enable_subagents = enable_subagents
        self.interrupt_node = interrupt_node

    def create_supervisor_graph(self, config: AgentConfig | None = None) -> Any:
        """Create the supervisor + handoff parent graph.

        Args:
            config: Optional AgentConfig with tool filtering parameters.

        Returns:
            Compiled StateGraph (parent graph with all specialists as nodes).
        """
        if config is None:
            config = AgentConfig()

        logger.info(
            "[SUPERVISOR_CREATION_START] create_supervisor_graph | "
            f"model={self.model} | "
            f"enable_subagents={self.enable_subagents} | "
            f"execution_mode={self.context.execution_mode.value}"
        )

        # Get all available tools and apply RBAC filtering
        all_tools = create_project_tools(self.context)
        if config.allowed_tools is not None:
            all_tools = [t for t in all_tools if t.name in config.allowed_tools]

        all_tools = filter_tools_by_execution_mode(
            all_tools, self.context.execution_mode
        )

        if config.assistant_role is not None:
            all_tools = filter_tools_by_role(all_tools, config.assistant_role)

        if config.user_role is not None:
            all_tools = filter_tools_by_role(all_tools, config.user_role)

        # Build specialist agents
        subagent_configs = (
            config.subagents if config.subagents is not None else get_all_subagents()
        )
        specialist_names: list[str] = []
        specialist_graphs = compile_subagents(
            self.model,
            self.context,
            subagent_configs,
            all_tools,
            allowed_tools=config.allowed_tools,
            label="specialist",
        )

        for sg in specialist_graphs:
            specialist_names.append(sg["name"])

        if not specialist_graphs:
            logger.warning(
                "No valid specialists compiled — falling back to direct tools"
            )
            return self._build_fallback_graph(all_tools, config)

        # Build handoff tools for all specialists
        handoff_tools = create_all_handoff_tools(subagent_configs)

        # Build task tool (secondary mechanism, reuses existing subagent defs)
        task_tool = build_task_tool(specialist_graphs)

        # Build supervisor agent
        supervisor_tools: list[BaseTool] = list(handoff_tools) + [task_tool]
        temporal_context_tool = next(
            (t for t in all_tools if t.name == "get_temporal_context"), None
        )
        if temporal_context_tool:
            supervisor_tools.append(temporal_context_tool)

        base_prompt = self.system_prompt or SUPERVISOR_SYSTEM_PROMPT
        supervisor_prompt = base_prompt + _HANDOFF_SUFFIX

        supervisor_middleware = [
            TodoListMiddleware(),
            TemporalContextMiddleware(self.context),
            BackcastSecurityMiddleware(
                self.context,
                tools=all_tools,
                interrupt_node=None,
            ),
        ]

        supervisor_agent = langchain_create_agent(
            model=self.model,
            tools=supervisor_tools,
            system_prompt=supervisor_prompt,
            middleware=supervisor_middleware,  # type: ignore[arg-type]
            checkpointer=config.checkpointer,
            context_schema=config.context_schema,
            name="supervisor",
        )

        # Build parent graph
        parent = StateGraph(BackcastSupervisorState)

        # Add supervisor as a subgraph node
        parent.add_node("supervisor", supervisor_agent)

        # Add each specialist as a subgraph node
        for sg in specialist_graphs:
            parent.add_node(sg["name"], sg["runnable"])
            logger.info(f"Added specialist node: {sg['name']}")

        # Wire edges
        parent.add_edge(START, "supervisor")

        # Supervisor routing: after supervisor finishes, check for handoff
        parent.add_conditional_edges(
            "supervisor",
            self._make_supervisor_router(specialist_names),
            specialist_names + [END],
        )

        # Each specialist: after finishing, return to supervisor
        for sg in specialist_graphs:
            parent.add_conditional_edges(
                sg["name"],
                self._make_specialist_router(specialist_names),
                specialist_names + ["supervisor"],
            )

        compiled = parent.compile(
            checkpointer=config.checkpointer,
            name="backcast_supervisor",
        )

        logger.info(
            f"[SUPERVISOR_CREATED] Graph compiled with "
            f"{len(specialist_graphs)} specialists"
        )

        return compiled

    @staticmethod
    def _make_supervisor_router(
        specialist_names: list[str],
    ) -> Any:
        """Create a routing function for the supervisor node.

        After the supervisor produces output, route based on whether
        it called a handoff tool (→ target specialist) or finished
        (→ END).
        """

        def router(state: BackcastSupervisorState) -> str:
            messages = state.get("messages", [])
            if not messages:
                return END

            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                for tc in last_msg.tool_calls:
                    tool_name = tc.get("name", "")
                    # Check if it's a handoff tool
                    for spec_name in specialist_names:
                        if tool_name == f"handoff_to_{spec_name}":
                            return spec_name

            # No handoff — supervisor is done
            return END

        return router

    @staticmethod
    def _make_specialist_router(
        specialist_names: list[str],
    ) -> Any:
        """Create a routing function for specialist nodes.

        After a specialist finishes, check if it handed off to another
        specialist (peer handoff) or should return control to the supervisor.
        """

        def router(state: BackcastSupervisorState) -> str:
            messages = state.get("messages", [])
            if not messages:
                return "supervisor"

            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                for tc in last_msg.tool_calls:
                    tool_name = tc.get("name", "")
                    for spec_name in specialist_names:
                        if tool_name == f"handoff_to_{spec_name}":
                            return spec_name

            # No peer handoff — return to supervisor
            return "supervisor"

        return router

    def _build_fallback_graph(
        self,
        all_tools: list[BaseTool],
        config: AgentConfig,
    ) -> Any:
        """Build a simple agent with direct tool access (no specialists).

        Used when no specialists compile successfully.
        """
        logger.info("Building fallback graph with direct tool access")

        base_prompt = self.system_prompt or SUPERVISOR_SYSTEM_PROMPT
        middleware = [
            TodoListMiddleware(),
            TemporalContextMiddleware(self.context),
            BackcastSecurityMiddleware(
                self.context,
                tools=all_tools,
                interrupt_node=None,
            ),
        ]

        return langchain_create_agent(
            model=self.model,
            tools=all_tools,
            system_prompt=base_prompt,
            middleware=middleware,  # type: ignore[arg-type]
            checkpointer=config.checkpointer,
            context_schema=config.context_schema,
        )


__all__ = ["SupervisorOrchestrator"]

"""Supervisor orchestrator for the briefing-based agent delegation pattern.

Builds a parent StateGraph where the supervisor routes requests to specialist
agents via handoff tools. Specialists do NOT share message history -- instead,
each receives the compiled briefing document as context and contributes findings
back to the accumulating document.

The supervisor reads the briefing via ``get_briefing`` and delegates work via
handoff tools. Each specialist runs in isolation with only the briefing as
context, returning structured findings that get compiled back into the document.

Specialists are stateless -- they receive the briefing as their only context and
return findings via Command objects.

Graph: START -> initialize_briefing -> supervisor <-> specialist_nodes -> END
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any

from langchain.agents import create_agent as langchain_create_agent
from langchain.agents.middleware.types import AgentState
from langchain.tools import tool as lc_tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt.tool_node import InjectedState
from langgraph.types import Command

from app.ai.briefing import BriefingDocument
from app.ai.briefing_compiler import (
    compile_specialist_output,
    initialize_briefing,
    parse_and_clean,
)
from app.ai.config import AgentConfig
from app.ai.handoff_tools import create_all_handoff_tools
from app.ai.message_utils import extract_final_ai_response, is_transient_stream_error
from app.ai.subagent_compiler import (
    build_backcast_middleware,
    compile_subagents,
    filter_tools_for_context,
)
from app.ai.subagents import get_all_subagents
from app.ai.subagents.db_loader import load_specialists_from_db
from app.ai.supervisor_state import BackcastSupervisorState
from app.ai.tools.types import ToolContext
from app.core.config import settings

logger = logging.getLogger(__name__)

BRIEFING_ROOM_SUPERVISOR_PROMPT = """You are a supervisor for the Backcast project budget management system.

You coordinate specialist agents who report back through a compiled briefing document.
The user reads the briefing directly — do NOT summarize or repeat findings in your response.

## How It Works
The current briefing is injected into your context as a system message before every turn.
1. Read the briefing to see what has been analyzed
2. If not addressed, hand off to the most relevant specialist
3. After a specialist contributes, the briefing is updated automatically

## Available Specialists
- project_manager -> Project CRUD, WBEs, cost elements, cost tracking, progress entries
- evm_analyst -> EVM calculations, performance analysis
- change_order_manager -> Change orders, impact analysis
- user_admin -> User and department management
- visualization_specialist -> Diagrams, visualizations
- forecast_manager -> Forecasts, schedule baselines
- mcp_specialist -> External tools via MCP servers (web search, database, etc.)
- general_purpose -> Unclear or cross-cutting requests

## Rules
- Do NOT write a response summarizing the briefing — the user reads the briefing directly
- Only respond if you need to ask the user a clarification question
- Do NOT hand off to the same specialist more than once for the same task
- Maximum 2 specialist cycles for simple requests
- Always check the briefing before deciding to hand off
"""

_BRIEFING_HANDOFF_SUFFIX = (
    "You do NOT have direct access to Backcast tools. "
    "Delegate all operations to specialists via handoff tools."
)

_BRIEFING_CONTEXT_PREFIX = "## Current Briefing\n\n"

_BRIEFING_SUMMARY_PROMPT = """<role>
Context Extraction Assistant
</role>

<primary_objective>
Extract the most relevant context from the conversation history below.
</primary_objective>

<instructions>
You are nearing the input token limit. Extract the most important information from the conversation history so it can replace the full history.

Focus on:
- The user's overall goal and current request
- Key findings, decisions, and conclusions reached so far
- Any artifacts created, files modified, or resources accessed (with paths)
- Remaining tasks and next steps

Format your response as plain paragraphs. Do NOT use markdown headers (##) or
bullet-point outlines. Write natural prose that captures the essential context
concisely.

<messages>
{messages}
</messages>
"""


def _briefing_update(doc: BriefingDocument) -> dict[str, Any]:
    """Build the standard state update after briefing initialization."""
    briefing_md = doc.to_markdown() if doc.sections else "No findings yet."
    return {
        "briefing_data": doc.model_dump(),
        "supervisor_iterations": 0,
        "max_supervisor_iterations": 3,
        "completed_specialists": set(),
        "messages": [SystemMessage(content=f"{_BRIEFING_CONTEXT_PREFIX}{briefing_md}")],
    }


class _BriefingSupervisorState(AgentState[Any]):
    """State extension for the briefing supervisor subgraph.

    Adds ``briefing_data`` so LangGraph shares it from the parent
    ``BackcastSupervisorState`` via automatic key-matching state sharing.
    Without this, ``InjectedState`` inside ``get_briefing`` only sees
    ``AgentState`` (messages, jump_to) and the briefing data field is
    never passed into the subgraph.
    """

    briefing_data: dict[str, Any]


def _create_get_briefing_tool() -> BaseTool:
    """Create a tool that reads the current briefing from graph state."""

    @lc_tool(
        "get_briefing",
        description=(
            "Get the current compiled briefing document with findings from all "
            "specialists. Call this to review what has been learned before "
            "deciding next steps."
        ),
    )
    def get_briefing(
        state: Annotated[dict[str, Any], InjectedState()],
    ) -> str:
        briefing_data = state.get("briefing_data", {})
        if not briefing_data:
            return "No briefing available yet."
        doc = BriefingDocument.from_state(briefing_data)
        return doc.to_markdown()

    return get_briefing


class SupervisorOrchestrator:
    """Orchestrator that builds a briefing-room supervisor graph.

    Creates a parent StateGraph where the supervisor routes to specialist
    agents via handoff tools. Each specialist receives a compiled briefing
    document instead of shared message history, contributing structured
    findings back to the accumulating document.

    Attributes:
        model: LangChain chat model instance.
        context: ToolContext with user permissions and temporal parameters.
        system_prompt: Optional custom system prompt for the supervisor.
    """

    def __init__(
        self,
        model: str | BaseChatModel,
        context: ToolContext,
        system_prompt: str | None = None,
        main_assistant_config: Any | None = None,
    ) -> None:
        self.model = model
        self.context = context
        self.system_prompt = system_prompt
        self.main_assistant_config = main_assistant_config

    async def create_supervisor_graph(self, config: AgentConfig | None = None) -> Any:
        """Create the briefing-based supervisor + specialist parent graph.

        Args:
            config: Optional AgentConfig with tool filtering parameters.

        Returns:
            Compiled StateGraph (parent graph with all specialists as nodes).
        """
        if config is None:
            config = AgentConfig()

        logger.info(
            "[SUPERVISOR_CREATION_START] create_supervisor_graph | "
            "model=%s | execution_mode=%s",
            self.model,
            self.context.execution_mode.value,
        )

        # --- 1. Tool filtering ---
        all_tools = await filter_tools_for_context(self.context, config)

        # --- 2. Compile specialists ---
        # Try DB-loaded specialists first, fall back to hardcoded
        if config.subagents is not None:
            subagent_configs = config.subagents
        else:
            try:
                subagent_configs = await load_specialists_from_db()
                if not subagent_configs:
                    logger.info("[SUPERVISOR] No DB specialists found, using hardcoded")
                    subagent_configs = get_all_subagents()
            except Exception as exc:
                logger.warning(
                    "[SUPERVISOR] DB specialist loading failed, using hardcoded: %s",
                    exc,
                )
                subagent_configs = get_all_subagents()

        # Filter specialists by delegation config
        if self.main_assistant_config and self.main_assistant_config.delegation_config:
            allowed = self.main_assistant_config.delegation_config.get(
                "allowed_specialists"
            )
            if allowed is not None:
                subagent_configs = [
                    s for s in subagent_configs if s.get("name") in allowed
                ]
        specialist_graphs = compile_subagents(
            self.model,
            self.context,
            subagent_configs,
            all_tools,
            allowed_tools=config.allowed_tools,
            label="specialist",
        )

        specialist_names = [sg["name"] for sg in specialist_graphs]

        if not specialist_graphs:
            logger.warning(
                "No valid specialists compiled -- falling back to direct tools"
            )
            return self._build_fallback_graph(all_tools, config)

        # --- 3. Build supervisor tools ---
        get_briefing_tool = _create_get_briefing_tool()
        handoff_tools = create_all_handoff_tools(subagent_configs)

        supervisor_tools: list[BaseTool] = [get_briefing_tool] + list(handoff_tools)

        # Inject direct tools from the main agent's delegation config
        direct_tool_names: list[str] = []
        if self.main_assistant_config and self.main_assistant_config.delegation_config:
            direct_tool_names = (
                self.main_assistant_config.delegation_config.get("direct_tools", [])
                or []
            )

        direct_tools: list[BaseTool] = []
        if direct_tool_names:
            tool_map = {t.name: t for t in all_tools}
            for name in direct_tool_names:
                if name in tool_map:
                    direct_tools.append(tool_map[name])
            supervisor_tools.extend(direct_tools)

        # --- 4. Build supervisor agent ---
        base_prompt = self.system_prompt or BRIEFING_ROOM_SUPERVISOR_PROMPT

        # Conditional prompt based on direct tool availability
        if direct_tools:
            tool_names = ", ".join(t.name for t in direct_tools)
            direct_tools_suffix = (
                f"\n\nYou have DIRECT access to these Backcast tools: [{tool_names}]. "
                "Use them directly for their operations. "
                "ALL other Backcast operations must be delegated to specialists "
                "via handoff tools."
            )
            supervisor_prompt = base_prompt + direct_tools_suffix
        else:
            supervisor_prompt = base_prompt + _BRIEFING_HANDOFF_SUFFIX

        supervisor_agent = langchain_create_agent(
            model=self.model,
            tools=supervisor_tools,
            system_prompt=supervisor_prompt,
            middleware=self._build_middleware(all_tools),
            state_schema=_BriefingSupervisorState,
            checkpointer=config.checkpointer,
            context_schema=config.context_schema,
            name="supervisor",
        )

        logger.debug(
            "[SUPERVISOR] State bridge: _BriefingSupervisorState includes "
            "briefing_data for subgraph sharing",
        )

        # --- 5. Create specialist wrapper nodes ---
        # Wrappers isolate specialists: they receive only the briefing as context
        # and return findings via Command.
        specialist_wrappers: dict[str, Any] = {}
        for sg in specialist_graphs:
            specialist_wrappers[sg["name"]] = self._create_specialist_wrapper(
                specialist_name=sg["name"],
                specialist_graph=sg["runnable"],
            )

        # --- 6. Build the initialize_briefing node ---
        # Restores existing briefing on follow-up messages so specialist findings
        # survive across turns.
        async def initialize_briefing_node(
            state: BackcastSupervisorState,
        ) -> dict[str, Any]:
            messages = state.get("messages", [])
            user_request = ""
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    user_request = (
                        msg.content
                        if isinstance(msg.content, str)
                        else str(msg.content)
                    )
                    break

            # Check for existing briefing in state (from checkpoint on follow-ups)
            existing_briefing = state.get("briefing_data")

            if existing_briefing:
                doc = BriefingDocument.from_state(existing_briefing)
                if doc.original_request != "(recovered)":
                    doc.original_request = user_request
                    logger.info(
                        "[SUPERVISOR] Reusing existing briefing with %d sections",
                        len(doc.sections),
                    )
                    return _briefing_update(doc)

            # Create new briefing (first message or recovery)
            doc = initialize_briefing(user_request)
            return _briefing_update(doc)

        # --- 7. Build parent graph ---
        parent = StateGraph(BackcastSupervisorState)
        parent.add_node("initialize_briefing", initialize_briefing_node)
        parent.add_node("supervisor", supervisor_agent)
        for name, wrapper_fn in specialist_wrappers.items():
            parent.add_node(name, wrapper_fn)

        # --- 8. Wire edges ---
        parent.add_edge(START, "initialize_briefing")
        parent.add_edge("initialize_briefing", "supervisor")

        # Supervisor routing: handoff or END
        parent.add_conditional_edges(
            "supervisor",
            self._make_supervisor_router(specialist_names),
            specialist_names + [END],
        )

        # Each specialist always returns to supervisor
        for name in specialist_names:
            parent.add_edge(name, "supervisor")

        # --- 9. Compile and return ---
        compiled = parent.compile(
            checkpointer=config.checkpointer,
            name="backcast_supervisor",
        )

        logger.info(
            "[SUPERVISOR_CREATED] Graph compiled with %d specialists",
            len(specialist_graphs),
        )

        return compiled

    @staticmethod
    def _make_supervisor_router(
        specialist_names: list[str],
    ) -> Any:
        """Create a routing function for the supervisor node.

        After the supervisor produces output, route based on whether
        it called a handoff tool (-> target specialist) or finished
        (-> END). Enforces iteration cap and prevents redispatch
        to already-completed specialists.
        """
        from app.ai.handoff_tools import _slugify

        slug_map: dict[str, str] = {}
        for name in specialist_names:
            slug = _slugify(name)
            if slug in slug_map:
                logger.warning(
                    "[SUPERVISOR] Slug collision: '%s' and '%s' both map to '%s'",
                    slug_map[slug],
                    name,
                    slug,
                )
            slug_map[slug] = name

        def router(state: BackcastSupervisorState) -> str:
            iterations = state.get("supervisor_iterations", 0)
            max_iterations = state.get("max_supervisor_iterations", 3)
            if iterations >= max_iterations:
                logger.warning(
                    "[SUPERVISOR] Max supervisor iterations (%d) reached, forcing END",
                    max_iterations,
                )
                return END

            messages = state.get("messages", [])
            if not messages:
                return END

            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                completed = state.get("completed_specialists", set())
                specialist_set = set(specialist_names)
                for tc in last_msg.tool_calls:
                    tool_name = tc.get("name", "")
                    if tool_name.startswith("handoff_to_"):
                        slug = tool_name.removeprefix("handoff_to_")
                        # Map slug back to the actual specialist name
                        spec_name = slug_map.get(slug, slug)
                        if spec_name in completed:
                            logger.warning(
                                "[SUPERVISOR] Preventing redispatch to "
                                "already-completed specialist: %s",
                                spec_name,
                            )
                            return END
                        if spec_name in specialist_set:
                            return spec_name

            # No handoff -- supervisor is done
            return END

        return router

    def _create_specialist_wrapper(
        self,
        specialist_name: str,
        specialist_graph: Any,
    ) -> Any:
        """Create a briefing-specialist wrapper node for a compiled agent.

        The returned async function isolates the specialist from the parent
        graph: it constructs fresh messages containing only the briefing,
        invokes the specialist graph, then compiles findings back into the
        briefing document.

        Failed specialists are NOT added to ``completed_specialists`` -- this
        allows the supervisor to retry them on a subsequent turn.

        The specialist's system prompt is baked into its compiled graph by
        ``compile_subagents`` — the wrapper only provides runtime context.

        Args:
            specialist_name: Human-readable name for logging and briefing sections.
            specialist_graph: Compiled LangGraph (output of compile_subagents()).

        Returns:
            Async function suitable as a LangGraph node.
        """

        async def specialist_node(
            state: BackcastSupervisorState,
        ) -> dict[str, Any] | Command:  # type: ignore[type-arg]
            completed = state.get("completed_specialists", set())
            if specialist_name in completed:
                logger.info(
                    "[SUPERVISOR] Specialist %s already completed, early exiting",
                    specialist_name,
                )
                return Command(
                    update={
                        "active_agent": "supervisor",
                        "supervisor_iterations": state.get("supervisor_iterations", 0)
                        + 1,
                    },
                    goto=END,
                )

            task_desc = "Execute specialist task from briefing"
            rationale: str | None = None
            briefing_data_raw = state.get("briefing_data", {})
            if briefing_data_raw:
                doc = BriefingDocument.from_state(briefing_data_raw)
                if doc.task_history:
                    latest = doc.task_history[-1]
                    task_desc = latest.description
                    rationale = latest.rationale

            assignment_block = f"## Your Assignment\n\n{task_desc}"
            if rationale:
                assignment_block += f"\n\n**Supervisor's rationale:** {rationale}"

            briefing_markdown = doc.to_markdown() if briefing_data_raw else ""

            isolated_messages = [
                HumanMessage(
                    content=f"{assignment_block}\n\n## Briefing\n\n{briefing_markdown}"
                ),
            ]

            max_iterations = state.get("max_tool_iterations", 25)
            max_retries = settings.AI_SPECIALIST_MAX_RETRIES
            result = None

            for _retry_attempt in range(max_retries + 1):
                try:
                    result = await specialist_graph.ainvoke(
                        {
                            "messages": isolated_messages,
                            "tool_call_count": 0,
                            "max_tool_iterations": max_iterations,
                            "next": "agent",
                        },
                        config={"recursion_limit": max_iterations},
                    )
                    break  # success
                except Exception as exc:
                    if is_transient_stream_error(exc) and _retry_attempt < max_retries:
                        logger.warning(
                            "[SPECIALIST_RETRY] Specialist %s transient error "
                            "(attempt %d/%d), retrying in 2s: %s",
                            specialist_name,
                            _retry_attempt + 1,
                            max_retries + 1,
                            exc,
                        )
                        await asyncio.sleep(2.0)
                        continue
                    # Non-transient or retries exhausted — report to supervisor.
                    logger.error(
                        "[SPECIALIST_ERROR] Specialist %s failed: %s",
                        specialist_name,
                        exc,
                        exc_info=True,
                    )
                    error_msg = (
                        f"Specialist {specialist_name} encountered an error: {exc}"
                    )
                    updated_data = compile_specialist_output(
                        briefing_data=state.get("briefing_data", {}),
                        specialist_name=specialist_name,
                        task_description=f"Failed: {exc}",
                        specialist_output=error_msg,
                    )
                    return Command(
                        update={
                            "briefing_data": updated_data,
                            "active_agent": "supervisor",
                            "supervisor_iterations": state.get(
                                "supervisor_iterations", 0
                            )
                            + 1,
                            "tool_call_count": 0,
                        },
                        goto="supervisor",
                    )

            assert result is not None  # guaranteed: break on success, return on failure
            messages = result.get("messages", [])
            findings = extract_final_ai_response(messages)

            cleaned_findings, parsed = parse_and_clean(findings)

            updated_data = compile_specialist_output(
                briefing_data=state.get("briefing_data", {}),
                specialist_name=specialist_name,
                task_description=task_desc,
                specialist_output=cleaned_findings,
                supervisor_rationale=rationale,
                parsed_findings=parsed,
            )

            logger.info(
                "[SUPERVISOR] Specialist %s completed, briefing sections=%d",
                specialist_name,
                len(updated_data.get("sections", [])),
            )

            return Command(
                update={
                    "briefing_data": updated_data,
                    "active_agent": "supervisor",
                    "tool_call_count": result.get("tool_call_count", 0),
                    "supervisor_iterations": state.get("supervisor_iterations", 0) + 1,
                    "completed_specialists": state.get("completed_specialists", set())
                    | {specialist_name},
                },
                goto="supervisor",
            )

        return specialist_node

    def _build_middleware(self, tools: list[BaseTool]) -> list[Any]:
        """Build the middleware stack for the supervisor agent.

        Includes SummarizationMiddleware to compact message history during
        long multi-specialist conversations. Safe because the briefing is
        re-injected as a fresh SystemMessage each turn via _briefing_update.
        """
        from langchain.agents.middleware.summarization import SummarizationMiddleware

        base = build_backcast_middleware(self.context, tools)
        summ = SummarizationMiddleware(
            model=self.model,
            trigger=[("tokens", 8000), ("messages", 40)],
            summary_prompt=_BRIEFING_SUMMARY_PROMPT,
            keep=("messages", 20),
        )
        return [summ, *base]

    def _build_fallback_graph(
        self,
        all_tools: list[BaseTool],
        config: AgentConfig,
    ) -> Any:
        """Build a simple agent with direct tool access (no specialists).

        Used when specialist compilation fails entirely -- gives the agent
        direct tool access as a safety net.
        """
        logger.info("Building fallback graph with direct tool access")

        base_prompt = self.system_prompt or BRIEFING_ROOM_SUPERVISOR_PROMPT

        return langchain_create_agent(
            model=self.model,
            tools=all_tools,
            system_prompt=base_prompt,
            middleware=self._build_middleware(all_tools),
            checkpointer=config.checkpointer,
            context_schema=config.context_schema,
        )


__all__ = ["SupervisorOrchestrator"]

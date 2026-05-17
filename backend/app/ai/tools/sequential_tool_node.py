"""SequentialToolNode — defense-in-depth against parallel tool execution.

LangGraph's default ToolNode executes multiple tool calls via asyncio.gather,
which can cause DB pool exhaustion and race conditions when tools share a
database session. This module provides a drop-in replacement that executes
tools sequentially.

Two mechanisms:
1. SequentialToolNode class — inherit from this instead of ToolNode
2. patch_tool_node_for_sequential_execution() — monkey-patches ToolNode._afunc
   globally, covering specialist subgraphs created by langchain_create_agent()
   which instantiate plain ToolNode internally.
"""

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.runnables.config import RunnableConfig, get_config_list
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt.tool_node import ToolRuntime

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)

_patched: bool = False


class SequentialToolNode(ToolNode):
    """ToolNode subclass that executes tools sequentially.

    Identical to LangGraph's ToolNode except that _afunc runs tool calls
    one at a time instead of via asyncio.gather. This prevents DB pool
    exhaustion and race conditions when multiple tools share an async
    database session.

    Usage:
        Simply replace ``ToolNode(tools)`` with ``SequentialToolNode(tools)``.
    """

    async def _afunc(  # type: ignore[override]
        self,
        input: list[Any] | dict[str, Any],
        config: RunnableConfig,
        runtime: "Runtime",
    ) -> Any:
        """Execute tool calls sequentially instead of in parallel.

        This is a copy of ToolNode._afunc with the asyncio.gather replaced
        by a sequential for-loop. All other logic is identical.
        """
        tool_calls, input_type = self._parse_input(input)
        config_list = get_config_list(config, len(tool_calls))

        # Log a warning when multiple tool calls are batched
        if len(tool_calls) > 1:
            tool_names = [tc.get("name", "<unknown>") for tc in tool_calls]
            logger.warning(
                "SequentialToolNode: executing %d tool calls sequentially "
                "(would have been parallel): %s",
                len(tool_calls),
                tool_names,
            )

        # Construct ToolRuntime instances at the top level for each tool call
        tool_runtimes: list[Any] = []
        for call, cfg in zip(tool_calls, config_list, strict=False):
            state = self._extract_state(input)
            tool_runtime = ToolRuntime(
                state=state,
                tool_call_id=call["id"],
                config=cfg,
                context=runtime.context,
                store=runtime.store,
                stream_writer=runtime.stream_writer,
                execution_info=runtime.execution_info,
                server_info=runtime.server_info,
            )
            tool_runtimes.append(tool_runtime)

        # Pass original tool calls without injection
        # SEQUENTIAL EXECUTION — replaced asyncio.gather with for-loop
        outputs = []
        for call, tool_runtime in zip(tool_calls, tool_runtimes, strict=False):
            result = await self._arun_one(call, input_type, tool_runtime)
            outputs.append(result)

        return self._combine_tool_outputs(outputs, input_type)


def patch_tool_node_for_sequential_execution() -> None:
    """Monkey-patch ToolNode._afunc globally for sequential execution.

    This ensures that specialist subgraphs created via langchain_create_agent()
    — which instantiate plain ToolNode internally — also execute sequentially.

    Idempotent: calling multiple times has no additional effect.
    """
    global _patched
    if _patched:
        logger.debug("ToolNode._afunc already patched for sequential execution")
        return

    ToolNode._afunc = SequentialToolNode._afunc  # type: ignore[method-assign,assignment]
    _patched = True
    logger.info("ToolNode._afunc monkey-patched for sequential tool execution")

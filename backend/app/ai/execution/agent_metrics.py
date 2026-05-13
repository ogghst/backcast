"""Dataclass for aggregated agent execution metrics.

Returned by ``_run_agent_graph`` so that ``start_execution`` can persist
token counts and tool call counts to the ``ai_agent_executions`` row.
"""

from dataclasses import dataclass


@dataclass
class AgentExecutionMetrics:
    """Aggregated metrics from a single agent graph execution.

    Attributes:
        total_tokens: Sum of prompt + completion tokens from all LLM API calls.
        tool_calls_count: Number of tool invocations during the execution.
    """

    total_tokens: int = 0
    tool_calls_count: int = 0

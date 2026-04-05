"""Token usage estimation and monitoring for LangGraph agent.

Provides pre-flight context window estimation and post-flight actual token
capture from API responses for observability and debugging.

Context: Used by agent_service.py before and after graph invocation to log
token usage metrics. Pre-flight uses chars/4 heuristic; post-flight captures
real API data from on_chat_model_end events.
"""

import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)

CONTEXT_WINDOW_SIZES: dict[str, int] = {
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4.5-preview": 128_000,
    "gpt-4.1": 1_047_576,
    "gpt-4.1-mini": 1_047_576,
    "gpt-4.1-nano": 1_047_576,
    "o3": 200_000,
    "o4-mini": 200_000,
}
"""Static mapping of model names to context window sizes in tokens."""


def estimate_input_tokens(messages: list[BaseMessage]) -> int:
    """Estimate input token count from message history using chars/4 heuristic.

    Args:
        messages: List of LangChain messages to estimate tokens for.

    Returns:
        Estimated token count (total characters / 4).

    Examples:
        >>> estimate_input_tokens([HumanMessage(content="hello world")])
        2
    """
    total_chars = 0
    for msg in messages:
        content = msg.content
        if isinstance(content, str):
            total_chars += len(content)
        else:
            total_chars += len(str(content))
    return total_chars // 4


def get_context_window_size(model_name: str) -> int | None:
    """Look up context window size for a model.

    Args:
        model_name: Model identifier (e.g., "gpt-4o").

    Returns:
        Context window size in tokens, or None for unknown models.
    """
    return CONTEXT_WINDOW_SIZES.get(model_name)


def log_context_usage_estimate(
    messages: list[BaseMessage],
    model_name: str,
    session_id: str,
    execution_id: str,
) -> int:
    """Log estimated context window usage before graph invocation.

    Args:
        messages: Message history to estimate tokens for.
        model_name: Model identifier for context window lookup.
        session_id: Current session ID.
        execution_id: Current execution ID.

    Returns:
        Estimated input token count.
    """
    estimated_tokens = estimate_input_tokens(messages)
    window_size = get_context_window_size(model_name)

    if window_size is not None:
        usage_pct = (estimated_tokens / window_size) * 100
        logger.info(
            f"[CONTEXT_USAGE_ESTIMATE] session_id={session_id} | "
            f"execution_id={execution_id} | model={model_name} | "
            f"estimated_input_tokens={estimated_tokens} | "
            f"context_window_size={window_size} | "
            f"usage_percentage={usage_pct:.1f}%"
        )
    else:
        logger.info(
            f"[CONTEXT_USAGE_ESTIMATE] session_id={session_id} | "
            f"execution_id={execution_id} | model={model_name} | "
            f"estimated_input_tokens={estimated_tokens} | "
            f"context_window_size=unknown | "
            f"usage_percentage=N/A"
        )

    return estimated_tokens


@dataclass
class TokenUsageAccumulator:
    """Accumulates actual token usage from on_chat_model_end events.

    Handles both LangChain format (usage_metadata.input_tokens/output_tokens)
    and OpenAI format (response_metadata.token_usage.prompt_tokens/completion_tokens).

    Attributes:
        prompt_tokens: Accumulated input/prompt tokens from API.
        completion_tokens: Accumulated output/completion tokens from API.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0

    def accumulate_from_event(self, event_data: dict[str, Any]) -> None:
        """Extract and accumulate token usage from an on_chat_model_end event.

        Checks LangChain usage_metadata first, then falls back to OpenAI
        response_metadata format. Gracefully no-ops if neither is present.

        Args:
            event_data: Event dict from astream_events with 'output' field
                containing an AIMessage with usage metadata.
        """
        output = event_data.get("output")
        if output is None:
            return

        # Try LangChain standard format first (usage_metadata)
        usage_metadata = getattr(output, "usage_metadata", None)
        if isinstance(usage_metadata, dict):
            input_tokens = usage_metadata.get("input_tokens")
            output_tokens = usage_metadata.get("output_tokens")
            if isinstance(input_tokens, int) and isinstance(output_tokens, int):
                self.prompt_tokens += input_tokens
                self.completion_tokens += output_tokens
                return

        # Fallback to OpenAI format (response_metadata.token_usage)
        response_metadata = getattr(output, "response_metadata", None)
        if isinstance(response_metadata, dict):
            token_usage = response_metadata.get("token_usage")
            if isinstance(token_usage, dict):
                prompt = token_usage.get("prompt_tokens")
                completion = token_usage.get("completion_tokens")
                if isinstance(prompt, int) and isinstance(completion, int):
                    self.prompt_tokens += prompt
                    self.completion_tokens += completion

    def to_dict(self) -> dict[str, int]:
        """Return token usage as a dictionary.

        Returns:
            Dict with prompt_tokens, completion_tokens, and total_tokens.
        """
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
        }


def log_actual_usage(
    accumulator: TokenUsageAccumulator,
    model_name: str,
    session_id: str,
    execution_id: str,
) -> None:
    """Log actual token usage after graph invocation completes.

    Args:
        accumulator: TokenUsageAccumulator with accumulated API token data.
        model_name: Model identifier.
        session_id: Current session ID.
        execution_id: Current execution ID.
    """
    usage = accumulator.to_dict()
    logger.info(
        f"[CONTEXT_USAGE_ACTUAL] session_id={session_id} | "
        f"execution_id={execution_id} | model={model_name} | "
        f"prompt_tokens={usage['prompt_tokens']} | "
        f"completion_tokens={usage['completion_tokens']} | "
        f"total_tokens={usage['total_tokens']}"
    )

"""Token buffer manager for WebSocket streaming optimization.

Buffers tokens per agent and flushes at configurable intervals.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TokenBuffer:
    """Buffer for tokens from a single agent."""

    content: list[str] = field(default_factory=list)
    session_id: str | None = None
    source: str = "main"
    subagent_name: str | None = None
    invocation_id: str | None = None
    last_flush_time: float = 0.0

    def add(self, token: str) -> None:
        """Add a token to the buffer."""
        self.content.append(token)

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self.content) == 0

    def get_content(self) -> str:
        """Get concatenated buffer content."""
        return "".join(self.content)

    def clear(self) -> None:
        """Clear the buffer."""
        self.content.clear()


class TokenBufferManager:
    """Manages token buffers for multiple agents with periodic flushing.

    Each agent (main + subagents) has an independent buffer identified by:
    - Buffer key: f"{source}:{invocation_id or subagent_name or 'main'}"
    """

    def __init__(
        self,
        flush_interval_ms: int = 1000,
        max_buffer_size: int = 10000,
        enabled: bool = True,
    ):
        self.flush_interval_ms = flush_interval_ms
        self.max_buffer_size = max_buffer_size
        self.enabled = enabled
        self.buffers: dict[str, TokenBuffer] = defaultdict(self._create_buffer)
        self.flush_task: asyncio.Task[None] | None = None
        self.flush_callback: (
            Callable[[str, TokenBuffer], None | Awaitable[None]] | None
        ) = None
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()

    def _create_buffer(self) -> TokenBuffer:
        """Factory function for defaultdict."""
        return TokenBuffer()

    def _get_buffer_key(
        self, source: str, subagent_name: str | None, invocation_id: str | None = None
    ) -> str:
        """Generate buffer key from agent identifier."""
        if source == "subagent" and invocation_id:
            # Use invocation_id for unique subagent identification
            return f"{source}:{invocation_id}"
        if source == "main" and invocation_id:
            # Use invocation_id for main agent (separates content before/after subagents)
            return f"{source}:{invocation_id}"
        return f"{source}:{subagent_name or 'main'}"

    def set_flush_callback(self, callback: Callable[[str, TokenBuffer], None]) -> None:
        """Set callback for flushing buffers.

        Args:
            callback: Function called with (buffer_key, buffer) when flushing
        """
        self.flush_callback = callback

    def add_token(
        self,
        token: str,
        session_id: str,
        source: str = "main",
        subagent_name: str | None = None,
        invocation_id: str | None = None,
    ) -> None:
        """Add a token to the appropriate buffer.

        Args:
            token: Token content to add
            session_id: Session identifier
            source: "main" or "subagent"
            subagent_name: Subagent name when source="subagent"
            invocation_id: Unique invocation ID for subagent instance
        """
        if not self.enabled:
            # Buffering disabled - callback should handle immediately
            if self.flush_callback:
                buffer = TokenBuffer(
                    content=[token],
                    session_id=session_id,
                    source=source,
                    subagent_name=subagent_name,
                    invocation_id=invocation_id,
                )
                self.flush_callback("_immediate", buffer)
            return

        key = self._get_buffer_key(source, subagent_name, invocation_id)
        buffer = self.buffers[key]
        buffer.session_id = session_id
        buffer.source = source
        buffer.subagent_name = subagent_name
        buffer.invocation_id = invocation_id
        buffer.add(token)

        # Flush immediately if buffer exceeds max size
        if len(buffer.content) >= self.max_buffer_size:
            asyncio.create_task(self._flush_buffer(key))

    async def _flush_buffer(self, key: str) -> None:
        """Flush a specific buffer via callback.

        Args:
            key: Buffer key to flush
        """
        async with self._lock:
            if key not in self.buffers:
                return

            buffer = self.buffers[key]
            if buffer.is_empty():
                return

            if self.flush_callback:
                try:
                    # Callback must handle async if needed
                    # For websocket.send_json which is async
                    if asyncio.iscoroutinefunction(self.flush_callback):
                        await self.flush_callback(key, buffer)
                    else:
                        self.flush_callback(key, buffer)
                except Exception as e:
                    logger.error(f"Error flushing buffer {key}: {e}")

            buffer.clear()

    async def _flush_loop(self) -> None:
        """Background task that periodically flushes all buffers."""
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self.flush_interval_ms / 1000)

                if self._stop_event.is_set():
                    break

                async with self._lock:
                    keys_to_flush = list(self.buffers.keys())

                for key in keys_to_flush:
                    await self._flush_buffer(key)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")

    async def start(self) -> None:
        """Start the background flush loop."""
        if not self.enabled or self.flush_task is not None:
            return

        self.flush_task = asyncio.create_task(self._flush_loop())
        logger.info(
            f"Token buffer manager started (interval={self.flush_interval_ms}ms)"
        )

    async def stop(self) -> None:
        """Stop the buffer manager and flush all pending buffers.

        Important: Call this before closing the WebSocket to ensure
        all buffered tokens are sent.
        """
        self._stop_event.set()

        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
            self.flush_task = None

        # Flush all remaining buffers
        async with self._lock:
            keys = list(self.buffers.keys())

        for key in keys:
            await self._flush_buffer(key)

        self.buffers.clear()
        logger.info("Token buffer manager stopped")

    async def flush_agent(
        self,
        source: str = "main",
        subagent_name: str | None = None,
        invocation_id: str | None = None,
    ) -> None:
        """Manually flush a specific agent's buffer.

        Useful when:
        - Subagent switches (flush main agent before starting subagent)
        - Stream completion
        - Error conditions

        Args:
            source: "main" or "subagent"
            subagent_name: Subagent name when source="subagent"
            invocation_id: Unique invocation ID for subagent instance
        """
        key = self._get_buffer_key(source, subagent_name, invocation_id)
        await self._flush_buffer(key)

    async def flush_all(self) -> None:
        """Flush all buffers immediately."""
        async with self._lock:
            keys = list(self.buffers.keys())

        for key in keys:
            await self._flush_buffer(key)

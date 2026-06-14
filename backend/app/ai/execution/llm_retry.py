"""Shared resilience primitives for AI graph execution.

Provides three reusable helpers that bound provider stalls and retry
transient errors, while PAUSING their active-work clock while an
``ask_user`` request is awaiting a human response (so a slow human does
not get the surrounding call killed mid-clarification):

- :func:`await_with_pausable_deadline` -- for a single coroutine
  (used by the planner's ``llm.ainvoke`` and the specialist invocation).
- :func:`iter_with_pausable_deadline` -- for an async generator
  (used by the top-level ``ctx.graph.astream_events`` loop).
- :func:`invoke_with_retry` -- wraps a zero-arg async factory in
  ``await_with_pausable_deadline`` and retries on transient/timeout errors
  with exponential backoff plus jitter.

These were extracted from ``app/ai/supervisor_orchestrator.py`` where they
originated as module-private, specialist-only helpers.  They are now
generalised so the planner and the top-level graph loop can share the same
retry + pausable-deadline discipline.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import AsyncIterator, Awaitable, Callable

from app.ai.message_utils import is_transient_stream_error

logger = logging.getLogger(__name__)

# Exponential backoff parameters for ``invoke_with_retry`` retries.
# Tunable later if real-world throttling data warrants different values.
RETRY_BASE_S = 1.0
RETRY_CAP_S = 20.0
RETRY_JITTER_S = 0.5


def _awaiting_human(execution_id: str | None) -> bool:
    """True if THIS execution is awaiting a human, or (fallback) any ask.

    The per-execution predicate :func:`is_awaiting_user` is preferred when
    *execution_id* is known; when it is ``None`` the global
    :func:`is_ask_user_pending` predicate is used so any in-flight ask
    pauses the clock (conservative for the single-conversation-per-process
    server).
    """
    from app.ai.tools.ask_user import is_ask_user_pending, is_awaiting_user

    if execution_id is not None and is_awaiting_user(execution_id):
        return True
    return is_ask_user_pending()


async def await_with_pausable_deadline[T](
    coro: Awaitable[T],
    *,
    timeout: float,
    execution_id: str | None = None,
    tick: float = 0.5,
) -> T:
    """Await *coro*, enforcing a wall-clock *timeout* that PAUSES while an
    ask_user request is awaiting a human response.

    Provider stalls still trip the timeout; legitimate user-waits
    (ask_user) do not, because ask_user carries its own response timeout.

    The deadline is sliced into ``tick``-second windows.  A tick-timeout
    (``TimeoutError`` from ``wait_for(asyncio.shield(task), tick)``) only
    accrues toward *timeout* when the call is NOT awaiting a human.  When
    elapsed active time reaches *timeout*, the underlying task is cancelled
    and a retryable ``TimeoutError`` is raised.

    Args:
        coro: The coroutine to await.
        timeout: Active (non-paused) seconds budget for the call.
        execution_id: Optional execution ID for per-execution
            awaiting-user tracking. Falls back to the global ask predicate
            when None.
        tick: Window size for the deadline slicer (default 0.5s).

    Returns:
        The awaited result.

    Raises:
        TimeoutError: When active elapsed time reaches *timeout* (real stall).
    """
    # Clamp the tick to ``timeout`` so a single slicer window can never be
    # larger than the entire active budget -- otherwise a real stall whose
    # inner hang is shorter than ``tick`` would slip through unnoticed.
    effective_tick = min(tick, timeout)

    task = asyncio.ensure_future(coro)
    elapsed = 0.0
    try:
        while True:
            try:
                # shield so a tick-timeout does NOT cancel the underlying task
                return await asyncio.wait_for(
                    asyncio.shield(task), timeout=effective_tick
                )
            except TimeoutError:
                # Only accrue time when NOT waiting on a human.
                if not _awaiting_human(execution_id):
                    elapsed += effective_tick
                    if elapsed >= timeout:
                        # Real stall: cancel the task and surface a retryable timeout.
                        task.cancel()
                        raise TimeoutError(
                            f"invocation exceeded {timeout:.0f}s of active time"
                        ) from None
                # else: an ask_user is pending -> pause the deadline (do not accrue).
    except BaseException:
        # Ensure the task is cancelled if we bail for any reason while
        # it's still running.
        if not task.done():
            task.cancel()
        raise


async def iter_with_pausable_deadline[T](
    agen: AsyncIterator[T],
    *,
    timeout: float,
    execution_id: str | None = None,
    tick: float = 0.5,
) -> AsyncIterator[T]:
    """Yield items from *agen* under an active-time deadline that PAUSES
    while an ask_user request is awaiting a human response.

    Sibling of :func:`await_with_pausable_deadline` for the async-generator
    shape of ``ctx.graph.astream_events``.  For each item, a single
    ``__anext__`` task is scheduled once (via ``ensure_future``) and then
    re-awaited across ``tick``-second windows using
    ``asyncio.wait_for(asyncio.shield(task), tick)`` so a tick-timeout
    does NOT cancel the in-flight step (it keeps running; we just stop
    waiting for it this tick).  Elapsed time accrues ONLY when no human is
    being asked.  When active elapsed time reaches *timeout*, the generator
    is closed (``await agen.aclose()`` in the ``finally``) and a retryable
    ``TimeoutError`` is raised.

    Args:
        agen: The async iterator (e.g. ``graph.astream_events(...)``).
        timeout: Active (non-paused) seconds budget for the whole
            iteration.
        execution_id: Optional execution ID for per-execution
            awaiting-user tracking. Falls back to the global ask predicate
            when None.
        tick: Window size for the deadline slicer (default 0.5s).

    Yields:
        Items from *agen*.

    Raises:
        TimeoutError: When active elapsed time reaches *timeout* (real stall).
    """
    # Clamp the tick to ``timeout`` so a single slicer window can never be
    # larger than the entire active budget.
    effective_tick = min(tick, timeout)
    elapsed = 0.0
    # Tracks the in-flight __anext__ task so we can cancel it on timeout
    # (mirrors ``await_with_pausable_deadline``'s ``task.cancel()``).  Kept
    # out here so the ``finally`` can cancel it even if the timeout path
    # raises before reassigning.
    step: asyncio.Future[_StepResult[T]] | None = None

    try:
        while True:
            # Schedule ONE __anext__ task per item, wrapped so the task
            # resolves with the _DONE sentinel instead of raising
            # StopAsyncIteration (which must not propagate through an async
            # generator body).  On tick-timeout we do NOT cancel the task
            # (shield); we re-await the SAME task next loop so the
            # generator is not double-advanced.
            # ``step_task`` is the non-Optional handle used inside the
            # inner await loop; ``step`` is the Optional mirror consulted by
            # the ``finally`` so cancellation works even on early bail.
            step_task: asyncio.Future[_StepResult[T]] = asyncio.ensure_future(
                _safe_anext(agen)
            )
            step = step_task
            result: _StepResult[T]
            while True:
                try:
                    result = await asyncio.wait_for(
                        asyncio.shield(step_task), timeout=effective_tick
                    )
                    step = None  # completed; nothing to cancel later
                    break  # step completed within budget
                except TimeoutError:
                    if not _awaiting_human(execution_id):
                        elapsed += effective_tick
                        if elapsed >= timeout:
                            # Real stall: cancel the in-flight step so the
                            # generator can be closed cleanly, then surface
                            # a retryable timeout.
                            if not step_task.done():
                                step_task.cancel()
                            raise TimeoutError(
                                f"graph stream exceeded {timeout:.0f}s of active time"
                            ) from None
                    # else: ask_user pending -> pause (do not accrue),
                    # re-await the SAME step next iteration.
            if result.done:
                return
            # result.done is False -> value was set by _safe_anext.
            assert result.value is not None
            yield result.value
    finally:
        # Defensive: cancel any still-running in-flight step (e.g. on
        # caller cancellation) before closing the generator so the close
        # is clean.
        if step is not None and not step.done():
            step.cancel()
        # Close the generator if we bail for any reason while it's still
        # open (timeout, caller cancellation, exception).  ``aclose`` is
        # idempotent if the generator already finished.
        close = getattr(agen, "aclose", None)
        if close is not None:
            try:
                await close()
            except Exception:  # noqa: BLE001 - best-effort cleanup
                logger.debug(
                    "iter_with_pausable_deadline: aclose raised", exc_info=True
                )


# Sentinel: the result of a single ``__anext__`` step.  Using a tiny class
# (rather than letting ``StopAsyncIteration`` propagate through a task) keeps
# ``iter_with_pausable_deadline`` free of the StopAsyncIteration-inside-async-
# generator footgun.
class _StepResult[T]:
    """Outcome of one ``__anext__`` call: either ``done`` or carrying ``value``."""

    __slots__ = ("done", "value")

    def __init__(self, *, done: bool, value: T | None = None) -> None:
        self.done = done
        self.value = value


async def _safe_anext[T](agen: AsyncIterator[T]) -> _StepResult[T]:
    """Run one ``__anext__`` and convert ``StopAsyncIteration`` to a sentinel.

    Returning the sentinel (instead of letting ``StopAsyncIteration``
    propagate) avoids the Python restriction on ``StopAsyncIteration``
    inside an ``async def`` generator body.
    """
    try:
        value = await agen.__anext__()
    except StopAsyncIteration:
        return _StepResult(done=True)
    return _StepResult(done=False, value=value)


async def invoke_with_retry[T](
    invoke: Callable[[], Awaitable[T]],
    *,
    label: str,
    max_retries: int,
    timeout: float,
    execution_id: str | None = None,
) -> T:
    """Invoke *invoke()* under a pausable timeout and retry on transient
    errors.

    Wraps ``invoke()`` in :func:`await_with_pausable_deadline` so a
    provider stall (no exception, just a hang) is bounded by ``timeout``
    seconds of ACTIVE time, while PAUSING the deadline while the call is
    legitimately blocked on ``ask_user`` awaiting a human response.  On a
    retryable error (timeout or a transient stream error per
    :func:`is_transient_stream_error`), retries with exponential backoff
    plus jitter (``min(base * 2**attempt, cap) + uniform(0, jitter)``).

    On the final attempt or a non-retryable error the exception is
    re-raised so the caller's existing error-handling block can react.

    Args:
        invoke: Zero-arg async factory returning the call's result.
        label: Display name used in retry log lines (e.g. ``"planner"``,
            ``"WBSSpecialist"``).
        max_retries: Number of retries after the initial attempt.
        timeout: Active (non-paused) seconds for a single invocation.
        execution_id: Optional execution ID used to scope the
            awaiting-user pause check to this execution.

    Returns:
        The result on success.

    Raises:
        Exception: The last error when retries are exhausted, or the
            original error if it is not retryable.
    """
    for attempt in range(max_retries + 1):
        try:
            return await await_with_pausable_deadline(
                invoke(), timeout=timeout, execution_id=execution_id
            )
        except Exception as exc:
            retryable = isinstance(exc, (asyncio.TimeoutError, TimeoutError)) or (
                is_transient_stream_error(exc)
            )
            if retryable and attempt < max_retries:
                logger.warning(
                    "[%s_RETRY] retryable error (attempt %d/%d): %s",
                    label.upper(),
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )
                delay = min(RETRY_BASE_S * 2**attempt, RETRY_CAP_S) + random.uniform(
                    0, RETRY_JITTER_S
                )
                await asyncio.sleep(delay)
                continue
            raise
    # Unreachable when max_retries >= 0 (every non-raising path returns).
    raise RuntimeError(f"invoke_with_retry exited loop for {label}")

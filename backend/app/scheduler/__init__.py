"""Backcast agent scheduler — separate always-on process.

Owns *scheduling only*: a poll loop that reads due schedules from the shared
DB, advances ``next_run_at`` (skip-missed policy), and launches each run by
calling the backend trigger API over HTTP (authenticated as the schedule's
owner). It does NOT run agent executions itself — the in-memory
``ExecutionLifecycle``/``AgentEventBus`` singletons are process-local, so the
run must live in the backend process for the WS stream / Stop button /
notification delivery to work.

Entry point: ``python -m app.scheduler``.
"""

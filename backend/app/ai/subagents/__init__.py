"""Specialist agent configurations (DB-driven).

Specialist definitions are loaded from the ``ai_assistant_configs`` table
(rows where ``agent_type = 'specialist'``).  Use the CRUD UI or the seed
JSON in ``backend/seed/ai_specialist_configs.json`` to manage them.

This package re-exports the DB loader for convenient imports::

    from app.ai.subagents import load_specialists_from_db
"""

from app.ai.subagents.db_loader import (
    invalidate_cache,
    load_specialists_from_db,
)

__all__ = [
    "load_specialists_from_db",
    "invalidate_cache",
]

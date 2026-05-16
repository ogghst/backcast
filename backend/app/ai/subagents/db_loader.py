"""Load specialist agent configurations from the database.

Converts AIAssistantConfig rows with agent_type='specialist' into the dict
format expected by compile_subagents(). Cached with TTL to avoid repeated
DB queries during graph compilation.
"""

import importlib
import logging
import time
from typing import Any

from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.domain.ai import AIAssistantConfig

logger = logging.getLogger(__name__)

# Schema class registry: maps FQCN strings to Pydantic classes
_SCHEMA_REGISTRY: dict[str, type] = {}

# Cache: specialist dicts + timestamp
_cache: list[dict[str, Any]] | None = None
_cache_ts: float = 0.0
_CACHE_TTL = 300.0  # 5 minutes


def _resolve_schema(fqcn: str | None) -> type | None:
    """Resolve a fully qualified class name to a Python class."""
    if not fqcn:
        return None

    if fqcn in _SCHEMA_REGISTRY:
        return _SCHEMA_REGISTRY[fqcn]

    # e.g. "app.models.schemas.evm.EVMMetricsRead"
    module_path, _, class_name = fqcn.rpartition(".")
    try:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        _SCHEMA_REGISTRY[fqcn] = cls
        return cls
    except (ImportError, AttributeError) as e:
        logger.warning("Failed to resolve schema class %s: %s", fqcn, e)
        return None


def assistant_config_to_specialist_dict(
    config: AIAssistantConfig,
) -> dict[str, Any]:
    """Convert a specialist AIAssistantConfig row to the subagent dict schema."""
    return {
        "name": config.name,
        "description": config.description or "",
        "system_prompt": config.system_prompt or "",
        "allowed_tools": config.allowed_tools,
        "structured_output_schema": _resolve_schema(config.structured_output_schema),
    }


def invalidate_cache() -> None:
    """Clear the specialist config cache. Call after specialist CRUD."""
    global _cache, _cache_ts
    _cache = None
    _cache_ts = 0.0
    logger.info("[SPECIALIST_CACHE] Invalidated")


async def load_specialists_from_db() -> list[dict[str, Any]]:
    """Load active specialist configs from DB with TTL caching.

    Returns:
        List of specialist dicts compatible with compile_subagents().
    """
    global _cache, _cache_ts

    if _cache is not None and (time.monotonic() - _cache_ts) < _CACHE_TTL:
        return _cache

    async with async_session_maker() as session:
        stmt = (
            select(AIAssistantConfig)
            .where(
                AIAssistantConfig.agent_type == "specialist",
                AIAssistantConfig.is_active.is_(True),
            )
            .order_by(AIAssistantConfig.name)
        )
        result = await session.execute(stmt)
        configs = result.scalars().all()

    _cache = [assistant_config_to_specialist_dict(c) for c in configs]
    _cache_ts = time.monotonic()

    logger.info(
        "[SPECIALIST_CACHE] Loaded %d specialists from DB (TTL=%ds)",
        len(_cache),
        int(_CACHE_TTL),
    )
    return _cache

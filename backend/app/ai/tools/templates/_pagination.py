"""Shared pagination constants and helpers for AI tools."""

import math

import app.ai.config as _config

MAX_LIST_LIMIT = 200
BATCH_SIZE_LIMIT = 50


def get_page_limit(limit: int | None) -> int:
    """Return validated/clamped limit from page-based params."""
    if limit is None:
        limit = _config.AI_TOOLS_DEFAULT_PAGE_SIZE
    limit = min(limit, MAX_LIST_LIMIT)
    return limit


def calc_page_count(total: int, limit: int) -> int:
    """Return total page count."""
    return math.ceil(total / limit) if total > 0 else 0

"""Simple entity framework - commands and services for non-versioned entities."""

from app.core.simple.commands import (
    SimpleCommandABC,
    SimpleCreateCommand,
    SimpleDeleteCommand,
    SimpleUpdateCommand,
)
from app.core.simple.service import SimpleService

__all__ = [
    "SimpleCommandABC",
    "SimpleCreateCommand",
    "SimpleUpdateCommand",
    "SimpleDeleteCommand",
    "SimpleService",
]

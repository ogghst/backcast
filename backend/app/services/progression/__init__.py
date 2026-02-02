"""Progression strategies for schedule baseline calculations.

This module provides pure mathematical functions for calculating
progress over time for Earned Value Management (EVM) Planned Value (PV) calculations.
"""

from app.services.progression.base import ProgressionStrategy
from app.services.progression.gaussian import GaussianProgression
from app.services.progression.linear import LinearProgression
from app.services.progression.logarithmic import LogarithmicProgression

__all__ = [
    "ProgressionStrategy",
    "LinearProgression",
    "GaussianProgression",
    "LogarithmicProgression",
    "get_progression_strategy",
]


def get_progression_strategy(progression_type: str) -> ProgressionStrategy:
    """Get the appropriate progression strategy based on type string.

    Args:
        progression_type: The type of progression ("LINEAR", "GAUSSIAN", "LOGARITHMIC")

    Returns:
        ProgressionStrategy instance

    Raises:
        ValueError: If progression_type is unknown
    """
    strategies = {
        "LINEAR": LinearProgression(),
        "GAUSSIAN": GaussianProgression(),
        "LOGARITHMIC": LogarithmicProgression(),
    }

    strategy = strategies.get(progression_type.upper())
    if strategy is None:
        raise ValueError(
            f"Unknown progression type: {progression_type}. "
            f"Must be one of: {', '.join(strategies.keys())}"
        )

    return strategy

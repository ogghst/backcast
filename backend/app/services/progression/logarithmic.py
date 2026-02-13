"""Logarithmic (front-loaded) progression strategy.

Provides front-loaded progression where progress is rapid initially
and tapers off over time.
"""

import math
from datetime import datetime

from app.services.progression.base import ProgressionStrategy


class LogarithmicProgression(ProgressionStrategy):
    """Logarithmic front-loaded progression strategy.

    Models work that progresses quickly at the start and slows down
    toward completion. This is typical for tasks with upfront planning
    and design, or when early progress is easier than final polish.

    Uses natural logarithm to create the front-loaded curve.
    """

    # Add 1 to ln() to make the curve start at 0 and end at 1
    # ln(2) ≈ 0.693 is used as the normalization factor
    _LOG_NORMALIZATION: float = math.log(2.0)

    def calculate_progress(
        self, current_date: datetime, start_date: datetime, end_date: datetime
    ) -> float:
        """Calculate logarithmic front-loaded progress.

        Uses natural logarithm to create front-loaded curve:
            normalized_t = (current - start) / (end - start)  # [0, 1]
            progress = ln(1 + normalized_t) / ln(2)

        Args:
            current_date: The date for which to calculate progress
            start_date: The start date of the schedule baseline
            end_date: The end date of the schedule baseline

        Returns:
            A float between 0.0 and 1.0 representing progress
        """
        # Convert to timestamps for calculation
        current_ts = current_date.timestamp()
        start_ts = start_date.timestamp()
        end_ts = end_date.timestamp()

        duration = end_ts - start_ts

        if duration <= 0:
            raise ValueError("end_date must be after start_date")

        # Normalize to [0, 1] range
        elapsed = current_ts - start_ts
        normalized_t = elapsed / duration

        # Apply logarithmic transformation: ln(1 + t) / ln(2)
        # At t=0: ln(1)/ln(2) = 0
        # At t=1: ln(2)/ln(2) = 1
        # At t=0.25: ln(1.25)/ln(2) ≈ 0.32 (> 0.25, front-loaded!)
        progress = math.log(1.0 + normalized_t) / self._LOG_NORMALIZATION

        # Clamp to [0.0, 1.0] for edge cases
        return max(0.0, min(1.0, progress))

"""Gaussian (S-curve) progression strategy.

Provides S-curve progression modeling realistic project progress with
slow start, rapid middle phase, and tapering end.
"""

import math
from datetime import datetime

from app.services.progression.base import ProgressionStrategy


class GaussianProgression(ProgressionStrategy):
    """Gaussian S-curve progression strategy.

    Models realistic project progress where work ramps up slowly,
    accelerates in the middle, and tapers toward completion.
    This creates a characteristic S-curve shape.

    Uses the error function (erf) to generate a symmetric S-curve.
    """

    # Scale factor controls how "sharp" the S-curve is
    # Lower values = more gradual transition, higher = sharper
    _SCALE_FACTOR: float = 3.0

    def calculate_progress(
        self, current_date: datetime, start_date: datetime, end_date: datetime
    ) -> float:
        """Calculate Gaussian S-curve progress.

        Uses the error function to map linear time to an S-curve:
            normalized_t = (current - start) / (end - start)  # [0, 1]
            progress = 0.5 * (1 + erf(SCALE * (normalized_t - 0.5)))

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

        # Handle exact boundaries for semantic correctness
        # erf() asymptotically approaches 0 and 1 but never reaches them
        if current_ts <= start_ts:
            return 0.0
        if current_ts >= end_ts:
            return 1.0

        # Normalize to [0, 1] range
        elapsed = current_ts - start_ts
        normalized_t = elapsed / duration

        # Apply Gaussian error function with offset to map [0,1] -> [0,1]
        # erf(0) = 0, so at t=0.5 (midpoint), we get 0.5 * (1 + 0) = 0.5
        scaled_t = self._SCALE_FACTOR * (normalized_t - 0.5)
        progress = 0.5 * (1.0 + math.erf(scaled_t))

        # Clamp to [0.0, 1.0] for numerical safety
        return max(0.0, min(1.0, progress))

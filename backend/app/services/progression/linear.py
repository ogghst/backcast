"""Linear progression strategy.

Provides uniform progress over time - the simplest progression model.
"""

from datetime import datetime

from app.services.progression.base import ProgressionStrategy


class LinearProgression(ProgressionStrategy):
    """Linear progression strategy for uniform progress over time.

    At any point in time, progress is directly proportional to elapsed time.
    This is the simplest model and works well for steady, predictable work.
    """

    def calculate_progress(
        self, current_date: datetime, start_date: datetime, end_date: datetime
    ) -> float:
        """Calculate linear progress.

        Progress is calculated as:
            progress = (current_date - start_date) / (end_date - start_date)

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

        elapsed = current_ts - start_ts
        progress = elapsed / duration

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, progress))

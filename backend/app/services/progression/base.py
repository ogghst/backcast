"""Base progression strategy interface.

Provides the abstract interface for all progression strategies.
"""

from abc import ABC, abstractmethod
from datetime import datetime


class ProgressionStrategy(ABC):
    """Abstract base class for progression strategies.

    Each strategy defines how progress is calculated over time for
    schedule baseline Planned Value (PV) calculations in EVM.
    """

    @abstractmethod
    def calculate_progress(
        self, current_date: datetime, start_date: datetime, end_date: datetime
    ) -> float:
        """Calculate progress (0.0 to 1.0) at current_date.

        Args:
            current_date: The date for which to calculate progress
            start_date: The start date of the schedule baseline
            end_date: The end date of the schedule baseline

        Returns:
            A float between 0.0 and 1.0 representing progress

        Raises:
            ValueError: If start_date >= end_date
        """
        ...
